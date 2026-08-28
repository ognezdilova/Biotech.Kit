"""Validation script: compute and plot RMS envelope of recorded EMG.

Compares two envelope extraction approaches:
1. Low-pass envelope (continuous, sample-by-sample, low latency)
2. RMS envelope (windowed, block-based, standard for research)

Both approaches use the same preprocessing:
- Notch filter (powerline rejection)
- Bandpass filter (EMG band isolation)
- Full-wave rectification (envelope preparation)

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
from core.digital_signal_processing.filters import (
    BandpassFilter,
    LowpassFilter,
    NotchFilter,
    RectificationFilter,
)
from core.replay_device import ReplayDevice


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare low-pass and RMS envelope extraction from recorded EMG")
    parser.add_argument("csv_path", type=Path, help="Path to recorded CSV file")
    parser.add_argument("--window-size", type=int, default=256, help="RMS window size in samples")
    parser.add_argument("--hop-size", type=int, default=None, help="Hop size (default: window-size/2)")
    parser.add_argument("--lowpass-cutoff", type=float, default=8.0, help="Low-pass filter cutoff in Hz (default: 8)")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"File not found: {args.csv_path}", file=sys.stderr)
        return 1

    hop_size = args.hop_size or (args.window_size // 2)
    sample_rate_hz = 1000.0  # matches firmware SAMPLE_RATE
    
    # Processor with low-pass: produces continuous envelope
    lowpass_processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=60.0, sample_rate_hz=sample_rate_hz),
            BandpassFilter(low_hz=20.0, high_hz=400.0, sample_rate_hz=sample_rate_hz),
            RectificationFilter(),
            LowpassFilter(cutoff_hz=args.lowpass_cutoff, sample_rate_hz=sample_rate_hz),
        ]
    )
    
    # Processor without low-pass: produces rectified signal for RMS
    rectified_processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=60.0, sample_rate_hz=sample_rate_hz),
            BandpassFilter(low_hz=20.0, high_hz=400.0, sample_rate_hz=sample_rate_hz),
            RectificationFilter(),
        ]
    )
    
    rms_processor = RMSProcessor()
    
    # Collect envelope values
    rms_values: list[float] = []
    rms_times: list[float] = []
    raw_values: list[float] = []
    lowpass_envelope: list[float] = []
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
                    
                    # Get continuous low-pass envelope
                    lowpass_value = lowpass_processor.process_value(float(sample.value))
                    lowpass_envelope.append(lowpass_value)
                    
                    # Get rectified signal for RMS windowing
                    rectified_value = rectified_processor.process_value(float(sample.value))
                    
                    # Update sample value for windowing (use rectified)
                    from dataclasses import replace
                    rectified_sample = replace(sample, value=rectified_value)
                    window_buffer.write(rectified_sample)
        finally:
            window_buffer.close()

    if not rms_values:
        print("No RMS values computed - recording too short", file=sys.stderr)
        return 1

    # Plot: Raw signal + Low-pass envelope + RMS envelope comparison
    fig, axes = plt.subplots(3, 1, sharex=True, figsize=(14, 10))

    # Plot 1: Raw EMG
    axes[0].plot(raw_times, raw_values, linewidth=0.5, alpha=0.7, color='steelblue')
    axes[0].set_ylabel("ADC Value")
    axes[0].set_title(f"1. Raw EMG Signal ({args.csv_path.name})")
    axes[0].grid(True, alpha=0.3)
    axes[0].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)

    # Plot 2: Low-pass envelope (continuous)
    axes[1].plot(raw_times, lowpass_envelope, linewidth=1.0, color='darkorange', label=f"Low-pass envelope ({args.lowpass_cutoff} Hz)")
    axes[1].set_ylabel("Amplitude")
    axes[1].set_title("2. Continuous Envelope (Low-pass)")
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    # Plot 3: RMS envelope (windowed) overlaid on low-pass for comparison
    axes[2].plot(raw_times, lowpass_envelope, linewidth=0.8, alpha=0.5, color='lightcoral', label=f"Low-pass ({args.lowpass_cutoff} Hz)")
    axes[2].plot(rms_times, rms_values, linewidth=1.5, color='purple', marker='o', markersize=3, label=f"RMS (window={args.window_size}, hop={hop_size})")
    axes[2].set_ylabel("Amplitude")
    axes[2].set_xlabel("Time (s)")
    axes[2].set_title("3. Envelope Comparison: Low-pass (continuous) vs RMS (windowed)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    fig.tight_layout()
    plt.show()

    print(f"\nProcessed {len(raw_values)} samples ({len(raw_values)/sample_rate_hz:.2f} seconds)")
    print(f"\nLow-pass envelope:")
    print(f"  Samples: {len(lowpass_envelope)} (one per input sample)")
    print(f"  Mean: {np.mean(lowpass_envelope):.2f}")
    print(f"  Max: {np.max(lowpass_envelope):.2f}")
    print(f"\nRMS envelope:")
    print(f"  Values: {len(rms_values)} (one per {hop_size} samples)")
    print(f"  Mean: {np.mean(rms_values):.2f}")
    print(f"  Max: {np.max(rms_values):.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())