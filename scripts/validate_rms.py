"""Validation script: compute and plot RMS envelope of recorded EMG.

Demonstrates the full EMG processing pipeline:
- Notch filter (powerline rejection)
- Bandpass filter (EMG band isolation)
- Full-wave rectification (envelope preparation)
- RMS envelope (muscle activation level)

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
from core.digital_signal_processing.dsp_base import SignalProcessor
from core.digital_signal_processing.filters import BandpassFilter, NotchFilter, RectificationFilter
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
    sample_rate_hz = 1000.0  # matches firmware SAMPLE_RATE
    
    # Set up the signal processing chain (same as main.py)
    processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=60.0, sample_rate_hz=sample_rate_hz),
            BandpassFilter(low_hz=20.0, high_hz=400.0, sample_rate_hz=sample_rate_hz),
            RectificationFilter(),
        ]
    )
    
    rms_processor = RMSProcessor()
    
    # Collect RMS values and their timestamps
    rms_values: list[float] = []
    rms_times: list[float] = []
    raw_values: list[float] = []
    filtered_values: list[float] = []
    rectified_values: list[float] = []
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
                    if start_time_us is None:
                        start_time_us = sample.timestamp_us
                    
                    # Track raw signal
                    time_s = (sample.timestamp_us - start_time_us) / 1_000_000
                    raw_times.append(time_s)
                    raw_values.append(float(sample.value))
                    
                    # Apply filter chain step-by-step to track intermediate values
                    # Step 1: Notch + Bandpass (without rectification)
                    filtered_value = processor._filters[0].process(float(sample.value))  # Notch
                    filtered_value = processor._filters[1].process(filtered_value)       # Bandpass
                    filtered_values.append(filtered_value)
                    
                    # Step 2: Rectification
                    rectified_value = processor._filters[2].process(filtered_value)     # Rectification
                    rectified_values.append(rectified_value)
                    
                    # Update sample value for windowing (use rectified)
                    from dataclasses import replace
                    rectified_sample = replace(sample, value=rectified_value)
                    window_buffer.write(rectified_sample)
        finally:
            window_buffer.close()

    if not rms_values:
        print("No RMS values computed - recording too short", file=sys.stderr)
        return 1

    # Plot: Raw -> Filtered -> Rectified -> RMS Envelope
    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(14, 10))

    # Plot 1: Raw EMG
    axes[0].plot(raw_times, raw_values, linewidth=0.5, alpha=0.7, color='steelblue')
    axes[0].set_ylabel("ADC Value")
    axes[0].set_title(f"1. Raw EMG Signal ({args.csv_path.name})")
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)

    # Plot 2: Filtered (Notch + Bandpass, before rectification)
    axes[1].plot(raw_times, filtered_values, linewidth=0.5, alpha=0.7, color='green')
    axes[1].set_ylabel("Filtered Value")
    axes[1].set_title("2. Filtered Signal (Notch 60Hz + Bandpass 20-400Hz)")
    axes[1].grid(True, alpha=0.3)
    axes[1].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)

    # Plot 3: Rectified (after full-wave rectification)
    axes[2].plot(raw_times, rectified_values, linewidth=0.5, alpha=0.7, color='purple')
    axes[2].set_ylabel("Rectified Value")
    axes[2].set_title("3. Rectified Signal (Full-wave: abs(x))")
    axes[2].grid(True, alpha=0.3)
    axes[2].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)

    # Plot 4: RMS Envelope
    axes[3].plot(rms_times, rms_values, linewidth=1.5, color='darkorange', label=f"RMS (window={args.window_size}, hop={hop_size})")
    axes[3].set_ylabel("RMS Amplitude")
    axes[3].set_xlabel("Time (s)")
    axes[3].set_title("4. RMS Envelope (Muscle Activation Level)")
    axes[3].grid(True, alpha=0.3)
    axes[3].legend()

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