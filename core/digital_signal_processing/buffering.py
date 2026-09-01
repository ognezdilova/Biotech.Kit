"""Buffering layer for block-based (windowed) DSP.

WindowBuffer implements the same
(open/close/write) shape as DataSink, so it plugs directly into an
AcquisitionSession's sinks / processed_sinks list next to
CsvSink - no changes to AcquisitionSession are required. Every
hop_size samples, once enough data has accumulated, it emits a
Window: a fixed-size, time-stamped slice of the signal that
downstream block-based processors can consume.

Buffering is per-channel (keyed by `Sample.channel`), so multi-channel
acquisition works without special-casing: each channel gets its own
independent ring buffer and windowing cadence.
"""

from collections.abc import Callable
from dataclasses import dataclass
import threading

import numpy as np

from core.models import Sample


class RingBuffer:
    """Fixed-capacity circular buffer of numeric values.

    Pushing is O(1) with no per-sample allocation (a pre-allocated
    numpy array is reused). snapshot() returns the last `capacity`
    values (or fewer, if not yet full) in chronological order
    (oldest -> newest) as a *copy*, so callers can safely hand it off
    to another thread/consumer without the buffer mutating under them.
    """

    def __init__(self, capacity: int, dtype: type = np.float64) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._data = np.zeros(capacity, dtype=dtype)
        self._write_index = 0
        self._count = 0
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def is_full(self) -> bool:
        with self._lock:
            return self._count >= self._capacity

    def push(self, value) -> None:
        with self._lock:
            # pushes new value, overwriting oldest if full
            self._data[self._write_index] = value
            self._write_index = (self._write_index + 1) % self._capacity
            self._count = min(self._count + 1, self._capacity)

    def snapshot(self) -> np.ndarray:
        """Return buffered values in chronological order (oldest -> newest)."""
        with self._lock:
            if self._count < self._capacity:
                return self._data[: self._count].copy()
            # Full and circular: the oldest sample sits at _write_index
            # (the slot about to be overwritten next).
            return np.concatenate(
                (self._data[self._write_index :], self._data[: self._write_index])
            )

    def clear(self) -> None:
        with self._lock:
            self._data.fill(0)
            self._write_index = 0
            self._count = 0


@dataclass(frozen=True, slots=True)
class Window:
    """A fixed-size, time-stamped slice of a single channel's signal.

    `values` and `timestamps_us` are aligned index-for-index and both
    run oldest -> newest. Carrying real timestamps (rather than just
    assuming a nominal sample rate) lets consumers (FFT, etc.) derive
    the effective sample rate from actual acquisition timing, which
    matters for jittery serial/BLE links.
    """

    channel: int
    values: np.ndarray
    timestamps_us: np.ndarray

    @property
    def size(self) -> int:
        return len(self.values)

    @property
    def duration_us(self) -> int:
        return int(self.timestamps_us[-1] - self.timestamps_us[0])

    def sample_rate_hz(self) -> float:
        """Effective sample rate estimated from real timestamps.

        Returns 0.0 if it can't be estimated (degenerate window).
        """
        duration_s = self.duration_us / 1000000
        if duration_s <= 0:
            return 0.0
        return (self.size - 1) / duration_s


WindowCallback = Callable[[Window], None]


class WindowBuffer:
    """Turns a stream of `Sample`s into fixed-size, optionally overlapping
    `Window`s, per channel.

    Implements the `DataSink` shape (`open`/`close`/`write`) so it can
    be dropped into `AcquisitionSession(sinks=[...])` or
    `processed_sinks=[...]` exactly like any other sink - it can watch
    raw samples, filtered samples, or both (via two separate
    `WindowBuffer` instances), without the session needing to know
    anything about windowing.

    A window is emitted every `hop_size` new samples on a given
    channel, once at least `window_size` samples have been collected
    for that channel:
      - `hop_size == window_size` -> back-to-back, non-overlapping windows.
      - `hop_size < window_size`  -> overlapping (sliding) windows.
      - `hop_size > window_size`  -> windows with gaps skipped between them.
    """

    def __init__(
        self,
        window_size: int,
        hop_size: int | None = None,
        on_window: WindowCallback | None = None,
    ) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self._window_size = window_size
        self._hop_size = window_size if hop_size is None else hop_size
        if self._hop_size <= 0:
            raise ValueError("hop_size must be positive")

        self._on_window = on_window
        self._value_buffers: dict[int, RingBuffer] = {}
        self._timestamp_buffers: dict[int, RingBuffer] = {}
        self._since_last_window: dict[int, int] = {}
        self._lock = threading.Lock()

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def hop_size(self) -> int:
        return self._hop_size

    def channels(self) -> list[int]:
        with self._lock:
            return list(self._value_buffers.keys())

    # DataSink interface 

    def open(self) -> None:
        """Nothing to open; per-channel buffers are created lazily on first write."""

    def close(self) -> None:
        """Nothing to close; buffers simply stop receiving new data."""

    def write(self, sample: Sample) -> None:
        window: Window | None = None
        with self._lock:
            channel = sample.channel
            values = self._value_buffers.get(channel)
            if values is None:
                values = RingBuffer(self._window_size, dtype=np.float64)
                timestamps = RingBuffer(self._window_size, dtype=np.int64)
                self._value_buffers[channel] = values
                self._timestamp_buffers[channel] = timestamps
                self._since_last_window[channel] = 0
            timestamps = self._timestamp_buffers[channel]

            values.push(float(sample.value))
            timestamps.push(sample.timestamp_us)
            self._since_last_window[channel] += 1

            if values.is_full() and self._since_last_window[channel] >= self._hop_size:
                self._since_last_window[channel] = 0
                window = Window(
                    channel=channel,
                    values=values.snapshot(),
                    timestamps_us=timestamps.snapshot(),
                )

        if window is not None and self._on_window is not None:
            self._on_window(window)

    # pull-based access 

    def get_window(self, channel: int = 0) -> Window | None:
        """Return the most recent full window for a channel, or None
        if that channel hasn't accumulated `window_size` samples yet.
        """
        with self._lock:
            values = self._value_buffers.get(channel)
            if values is None or not values.is_full():
                return None
            timestamps = self._timestamp_buffers[channel]
            return Window(
                channel=channel,
                values=values.snapshot(),
                timestamps_us=timestamps.snapshot(),
            )