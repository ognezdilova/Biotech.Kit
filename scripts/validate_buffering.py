"""Validation script for the windowing buffer layer.

Replays a previously recorded CSV file through the exact same
'AcquisitionSession' pipeline used for live acquisition (device ->
parser -> sinks), with a 'WindowBuffer' attached as an extra sink.
This proves the buffering layer works end-to-end with real Session
wiring, real recorded timing/jitter, and without touching 'app/main.py' or
requiring hardware.

No real DSP is performed here yet (no FFT/RMS/envelope). This is
just a sanity check that data flows correctly through Session -> WindowBuffer 
and that timestamps/windowing look right.
Once a real block-based processor exists, wire it in the same way
'_on_window' is wired below.

Usage:
    python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv                                   -- all channels, window-size 256 --hop-size 128 (default)
    python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --window-size 256 --hop-size 128  -- all channels, (specified window size/hop size)
    python -m scripts.validate_buffering data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --channel 0                       -- only channel 0, default window size/hop size

"""

import argparse
import sys
from pathlib import Path

import numpy as np

from core.replay_device import ReplayDevice
from app.parsers.esp32_emg_parser import ESP32EMGParser

from core.digital_signal_processing.buffering import Window, WindowBuffer
from core.session import AcquisitionSession


def _on_window(window: Window, stats: list[dict]) -> None:
    """Collect basic per-window sanity stats.

    No real signal processing here on purpose - min/max/mean just
    confirm the right values are landing in the right window in the
    right order, and sample_rate_hz() confirms timestamps survived
    the full pipeline intact.
    """
    values = window.values
    stats.append(
        {
            "channel": window.channel,
            "size": window.size,
            "duration_us": window.duration_us,
            "sample_rate_hz": window.sample_rate_hz(),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "mean": float(np.mean(values)),
        }
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a recorded CSV through WindowBuffer to sanity-check windowing."
    )
    parser.add_argument("csv_path", type=Path, help="Path to a recorded CSV file.")
    parser.add_argument(
        "--window-size", type=int, default=256, help="Samples per window (default: 256)."
    )
    parser.add_argument(
        "--hop-size",
        type=int,
        default=None,
        help="Samples between windows (default: same as --window-size, i.e. no overlap).",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=None,
        help="Only print stats for this channel (default: print all channels).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if not args.csv_path.exists():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1

    stats: list[dict] = []
    window_buffer = WindowBuffer(
        window_size=args.window_size,
        hop_size=args.hop_size,
        on_window=lambda window: _on_window(window, stats),
    )

    device = ReplayDevice(args.csv_path, speed=0)
    signal_parser = ESP32EMGParser()

    session = AcquisitionSession(
        device=device,
        parser=signal_parser,
        sinks=[window_buffer],
    )

    """Custom replay loop: ReplayDevice.read_line() returns None at EOF,
        but AcquisitionSession._loop() treats None as "skip and continue",
        which would loop forever. So the program runs the device/parsing manually."""

    with device:
        window_buffer.open()
        try:
            while True:
                raw_line = device.read_line()
                if raw_line is None:
                    # EOF reached
                    break
                
                sample = signal_parser.parse(raw_line)
                if sample is not None:
                    window_buffer.write(sample)
                    session._sample_count += 1
                    if session.sample_count % 1000 == 0:
                        print(f"Processed {session.sample_count} samples...")
        finally:
            window_buffer.close()

    if not stats:
        print(
            f"No windows emitted - recording too short for "
            f"window_size={args.window_size} "
            f"({session.sample_count} samples read total)."
        )
        return 0

    print(f"Read {session.sample_count} samples, emitted {len(stats)} window(s).\n")
    for i, s in enumerate(stats):
        if args.channel is not None and s["channel"] != args.channel:
            continue
        print(
            f"window {i:>4} | channel={s['channel']} | size={s['size']:>4} | "
            f"~{s['sample_rate_hz']:.1f} Hz | "
            f"min={s['min']:8.2f} max={s['max']:8.2f} mean={s['mean']:8.2f}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())