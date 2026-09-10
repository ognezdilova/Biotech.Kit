"""
Live matplotlib visualization of raw + processed signal streams.

Must run in the main thread (matplotlib GUI event loop requirement).
Reads from RollingBufferConsumer instances fed by the acquisition
thread; does not touch acquisition/session logic directly.

"""

import threading

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

from core.live_buffer import RollingBufferConsumer

class StreamPlotter:
    def __init__(
            self, 
            raw_buffer: RollingBufferConsumer,
            processed_buffer: RollingBufferConsumer,
            channels: list[int] | None = None,
            refresh_interval_ms: int = 50,
            watch_thread: "threading.Thread | None" = None,
            raw_ylim: tuple[float, float] | None = None,
            processed_ylim: tuple[float, float] | None = None,
            ) -> None:
        self._raw_buffer = raw_buffer
        self._processed_buffer = processed_buffer
        self._channels = channels or [0]
        self._refresh_interval_ms = refresh_interval_ms
        self._watch_thread = watch_thread
        self._frame_count = 0
        self._rescale_interval = 20  # Rescale every N frames instead of every frame
        self._processed_ymax: float | None = None

        self._fig, (self._ax_raw, self._ax_proc) = plt.subplots(
            2, 1, figsize=(10, 6), sharex=False
        )
        self._fig.suptitle("Live Signal Streams (Press Ctrl+C in terminal or close window to stop)")
        self._ax_raw.set_title("Raw Signal")
        self._ax_raw.set_ylabel("ADC value")
        self._ax_proc.set_title("Processed Signal")
        self._ax_proc.set_xlabel("Time (s)")
        self._ax_proc.set_ylabel("Amplitude")

        # Set initial axis limits to avoid autoscaling every frame
        if raw_ylim:
            self._ax_raw.set_ylim(raw_ylim)
        else:
            self._ax_raw.set_ylim(0, 4095)  # Typical 12-bit ADC range
        
        # For processed data, use provided limits or enable auto Y-scaling
        self._auto_scale_processed_y = processed_ylim is None
        if processed_ylim:
            self._ax_proc.set_ylim(processed_ylim)
            self._processed_ymax = processed_ylim[1]
        else:
            # Keep baseline anchored at 0 so relaxed muscle activity sits near zero.
            self._ax_proc.set_ylim(0.0, 1.0)
            self._processed_ymax = 1.0

        # Set initial xlim (will auto-adjust with data)
        self._ax_raw.set_xlim(0, 2)  # 2 seconds window initially
        self._ax_proc.set_xlim(0, 2)

        self._raw_lines = {ch: self._ax_raw.plot([], [], label=f"ch{ch}")[0] for ch in self._channels}
        self._proc_lines = {ch: self._ax_proc.plot([], [], label=f"ch{ch}")[0] for ch in self._channels}

        if len(self._channels) > 1:
            self._ax_raw.legend(loc="upper right")
            self._ax_proc.legend(loc="upper right")

        self._fig.tight_layout()
        self._anim: FuncAnimation | None = None

    def _update(self, _frame):
        if self._watch_thread is not None and not self._watch_thread.is_alive():
            plt.close(self._fig)
            return []
        
        self._frame_count += 1
        should_rescale = (self._frame_count % self._rescale_interval == 0)
        
        artists = []
        artists += self._refresh(self._ax_raw, self._raw_buffer, self._raw_lines, should_rescale)
        artists += self._refresh(self._ax_proc, self._processed_buffer, self._proc_lines, should_rescale)
        return artists

    def _refresh(self, ax, buffer: RollingBufferConsumer, lines: dict, rescale: bool):
        artists = []
        channel_values = []
        for ch, line in lines.items():
            snap = buffer.snapshot(ch)
            if snap is None:
                continue
            timestamps_us, values = snap
            if len(timestamps_us) == 0:
                continue
            t = (timestamps_us - timestamps_us[0]) / 1_000_000.0
            line.set_data(t, values)
            artists.append(line)
            channel_values.append(values)
        
        # Only rescale axes periodically, not every frame (major performance improvement)
        if rescale:
            ax.relim()
            # Auto-scale Y for processed plot if no limits were provided
            scale_y = (ax == self._ax_proc and self._auto_scale_processed_y)
            ax.autoscale_view(scalex=True, scaley=False)

            if scale_y and channel_values:
                all_values = np.concatenate(channel_values)
                # Robust peak estimate: ignore rare spikes to keep the plot stable.
                target_max = max(1.0, float(np.percentile(all_values, 99)) * 1.2)
                if self._processed_ymax is None:
                    self._processed_ymax = target_max
                elif target_max > self._processed_ymax:
                    # Expand quickly when contractions increase.
                    self._processed_ymax = 0.8 * self._processed_ymax + 0.2 * target_max
                else:
                    # Shrink slowly to avoid jitter when relaxing.
                    self._processed_ymax = 0.95 * self._processed_ymax + 0.05 * target_max

                ax.set_ylim(0.0, max(1.0, self._processed_ymax))
        
        return artists

    def start(self) -> None:
        "Blocking call from the main thread only"
        self._anim = FuncAnimation(
            self._fig,
            self._update,
            interval=self._refresh_interval_ms,
            blit=True,  # Only redraw changed artists (huge performance boost)
            cache_frame_data=False,
        )
        plt.show(block=True)


class DualChannelRawPlotter:
    """Minimal live plotter with exactly two raw channel subplots."""

    def __init__(
        self,
        raw_buffer: RollingBufferConsumer,
        channels: tuple[int, int] = (0, 1),
        refresh_interval_ms: int = 50,
        watch_thread: "threading.Thread | None" = None,
        raw_ylim: tuple[float, float] | None = None,
    ) -> None:
        self._raw_buffer = raw_buffer
        self._ch1, self._ch2 = channels
        self._refresh_interval_ms = refresh_interval_ms
        self._watch_thread = watch_thread

        self._fig, (self._ax1, self._ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=False)
        self._fig.suptitle("Live Raw EMG (Press Ctrl+C in terminal or close window to stop)")

        self._ax1.set_title(f"Channel {self._ch1 + 1} Raw")
        self._ax1.set_ylabel("ADC value")
        self._ax2.set_title(f"Channel {self._ch2 + 1} Raw")
        self._ax2.set_xlabel("Time (s)")
        self._ax2.set_ylabel("ADC value")

        if raw_ylim is not None:
            self._ax1.set_ylim(raw_ylim)
            self._ax2.set_ylim(raw_ylim)
        else:
            self._ax1.set_ylim(0, 4095)
            self._ax2.set_ylim(0, 4095)

        self._ax1.set_xlim(0, 2)
        self._ax2.set_xlim(0, 2)

        self._line1 = self._ax1.plot([], [])[0]
        self._line2 = self._ax2.plot([], [])[0]
        self._fig.tight_layout()
        self._anim: FuncAnimation | None = None

    def _update(self, _frame):
        if self._watch_thread is not None and not self._watch_thread.is_alive():
            plt.close(self._fig)
            return []

        artists = []
        for channel, ax, line in (
            (self._ch1, self._ax1, self._line1),
            (self._ch2, self._ax2, self._line2),
        ):
            snap = self._raw_buffer.snapshot(channel)
            if snap is None:
                continue
            timestamps_us, values = snap
            if len(timestamps_us) == 0:
                continue
            t = (timestamps_us - timestamps_us[0]) / 1_000_000.0
            line.set_data(t, values)
            ax.relim()
            ax.autoscale_view(scalex=True, scaley=False)
            artists.append(line)

        return artists

    def start(self) -> None:
        self._anim = FuncAnimation(
            self._fig,
            self._update,
            interval=self._refresh_interval_ms,
            blit=True,
            cache_frame_data=False,
        )
        plt.show(block=True)


        