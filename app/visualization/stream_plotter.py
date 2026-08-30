"""
Live matplotlib visualization of raw + processed signal streams.

Must run in the main thread (matplotlib GUI event loop requirement).
Reads from RollingBufferConsumer instances fed by the acquisition
thread; does not touch acquisition/session logic directly.

"""

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from core.live_buffer import RollingBufferConsumer

class StreamPlotter:
    def __init__(
            self, 
            raw_buffer: RollingBufferConsumer,
            processed_buffer: RollingBufferConsumer,
            channels: list[int] | None = None,
            refresh_interval_ms: int = 50,
            ) -> None:
        self._raw_buffer = raw_buffer
        self._processed_buffer = processed_buffer
        self._channels = channels or [0]

        self._fig, (self._ax_raw, self._ax_proc) = plt.subplots(
            2, 1, figsize=(10, 6), sharex=False
        )
        self._fig.suptitle("Live Signal Streams")
        self._ax_raw.set_title("Raw Signal")
        self._ax_raw.set_ylabel("ADC value")
        self._ax_proc.set_title("Processed Signal")
        self._ax_proc.set_xlabel("Time (s)")
        self._ax_proc.set_ylabel("Amplitude")

        self._raw_lines = {ch: self._ax_raw.plot([], [], label=f"ch{ch}")[0] for ch in self._channels}
        self._proc_lines = {ch: self._ax_proc.plot([], [], label=f"ch{ch}")[0] for ch in self._channels}

        if len(self._channels) > 1:
            self._ax_raw.legend(loc="upper right")
            self._ax_proc.legend(loc="upper right")

        self._fig.tight_layout()
        self._anim: FuncAnimation | None = None

    def _update(self, _frame):
        artists = []
        artists += self._refresh(self._ax_raw, self._raw_buffer, self._raw_lines)
        artists += self._refresh(self._ax_proc, self._processed_buffer, self._proc_lines)
        return artists

    def _refresh(self, ax, buffer: RollingBufferConsumer, lines: dict):
        artists = []
        for ch, line in lines.items():
            snap = buffer.snapshot(ch)
            if snap is None:
                continue
            timestamps_us, values = snap
            t = (timestamps_us - timestamps_us[0]) / 1_000_000.0
            line.set_data(t, values)
            artists.append(line)
        ax.relim()
        ax.autoscale_view()
        return artists

    def start(self) -> None:
        "Blocking call from the main thread only"
        self._anim = FuncAnimation(
            self._fig,
            self._update,
            interval=self._refresh_interval_ms,
            cache_frame_data=False,
        )
        plt.show()


        