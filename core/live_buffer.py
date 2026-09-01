"""Thread-safe rolling buffer consumer for live data streams.

"""

import threading

from core.consumer import SampleConsumer
from core.digital_signal_processing.buffering import RingBuffer
from core.models import Sample

class RollingBufferConsumer(SampleConsumer):
    """
    Thread-safe rolling buffer for live data streams.
    Safe to write from one thread (acquisition)
    and read from another (e.g. a plotting thread) concurrently.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be a positive integer.")
        self._capacity = capacity
        self._lock = threading.Lock()
        self._values: dict[int, RingBuffer] = {}
        self._timestamps: dict[int, RingBuffer] = {}

    def consume(self, sample: Sample) -> None:
        with self._lock:
            ch = sample.channel
            values = self._values.get(ch)
            if values is None:
                values = RingBuffer(self._capacity)
                timestamps = RingBuffer(self._capacity, dtype=int)
                self._values[ch] = values
                self._timestamps[ch] = timestamps
            else:
                timestamps = self._timestamps[ch]
            values.push(float(sample.value))
            timestamps.push(sample.timestamp_us)

    def snapshot(self, channel: int = 0):
        """Return (timestamps_us, values) oldest->newest, or None if empty."""
        with self._lock:
            values = self._values.get(channel)
            if values is None or values.count == 0:
                return None
            timestamps = self._timestamps[channel]
            return timestamps.snapshot(), values.snapshot()

    def channels(self) -> list[int]:
        with self._lock:
            return list(self._values.keys())