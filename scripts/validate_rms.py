"""Validation script: compute and plot RMS envelope of recorded EMG.

Usage:
    python -m scripts.validate_rms data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
    python -m scripts.validate_rms data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --window-size 128 --hop-size 64
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from app.parsers.esp32_emg_parser import ESP32EMGParser
from core.digital_signal_processing.block_processors import RMSProcessor
from core.digital_signal_processing.buffering import Window, WindowBuffer
from core.replay_device import ReplayDevice


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute RMS envelope from recorded EMG")
    parser.add_argument("csv_path", type=Path, help="Path to recorded CSV file")
    parser.add_argument("--window-size", type=int, default=256, help="RMS window size in samples")
    parser.add_argument("--hop-size", type=int, default=None, help="Hop size (default: window-size/2)")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1

    hop_size = args.hop_size or (args.window_size // 2)
    rms_processor = RMSProcessor()
    
    # Collect RMS values and their timestamps
    rms_values: list[float] = []
    rms_times: list[float] = []
    raw_values: list[float] = []
    raw_times: list[float] = []
    start_time_us: int | None = None

    def on_window(window: Window) -> None:
        nonlocal start_time_us
        if start_time_us is None:
            start_time_us = window.timestamps_us[0]
        
        # Compute RMS for this window
        result = rms_processor.process(window)
        
        # Use the center timestamp of the window
        window_center_us = (window.timestamps_us[0] + window.timestamps_us[-1]) / 2
        window_center_s = (window_center_us - start_time_us) / 1_000_000
        
        rms_values.append(float(result.values[0]))
        rms_times.append(window_center_s)

    window_buffer = WindowBuffer(
        window_size=args.window_size,
        hop_size=hop_size,
        on_window=on_window,
    )

    device = ReplayDevice(args.csv_path, speed=0)
    signal_parser = ESP32EMGParser()

    # Process the recording
    with device:
        window_buffer.open()
        try:
            while True:
                raw_line = device.read_line()
                if raw_line is None:
                    break
                
                sample = signal_parser.parse(raw_line)
                if sample is not None:
                    if start_time_us is not None:
                        raw_times.append((sample.timestamp_us - start_time_us) / 1_000_000)
                        raw_values.append(float(sample.value))
                    window_buffer.write(sample)
        finally:
            window_buffer.close()

    if not rms_values:
        print("No RMS values computed - recording too short", file=sys.stderr)
        return 1

    # Plot raw signal and RMS envelope
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(14, 8))

    ax1.plot(raw_times, raw_values, linewidth=0.5, alpha=0.7, label="Raw EMG")
    ax1.set_ylabel("ADC Value")
    ax1.set_title(f"Raw EMG Signal ({args.csv_path.name})")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.plot(rms_times, rms_values, linewidth=1.5, color='darkorange', label=f"RMS (window={args.window_size}, hop={hop_size})")
    ax2.set_ylabel("RMS Amplitude")
    ax2.set_xlabel("Time (s)")
    ax2.set_title("RMS Envelope (Muscle Activation Level)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.tight_layout()
    plt.show()

    print(f"\nProcessed {len(raw_values)} samples")
    print(f"Computed {len(rms_values)} RMS values")
    print(f"Mean RMS: {np.mean(rms_values):.2f}")
    print(f"Max RMS: {np.max(rms_values):.2f}")
    print(f"Min RMS: {np.min(rms_values):.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())