"""Validation script: run a recorded CSV through SignalProcessor and
visually compare raw vs. filtered signal, without touching live hardware.

Demonstrates the complete sample-by-sample filter chain with envelope extraction:
- Notch filter (powerline rejection)
- Bandpass filter (EMG band isolation)
- Full-wave rectification (envelope preparation)
- Low-pass filter (continuous envelope smoothing)

Usage:
    python -m scripts.validate_dsp data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
"""

import sys

import matplotlib.pyplot as plt

from core.digital_signal_processing.dsp_base import SignalProcessor
from core.digital_signal_processing.filters import (
    BandpassFilter,
    LowpassFilter,
    NotchFilter,
    RectificationFilter,
)
from core.replay_device import ReplayDevice


def main(csv_path: str) -> None:
    sample_rate_hz = 1000.0  # matches firmware SAMPLE_RATE

    # Match the complete pipeline from main.py
    processor = SignalProcessor(
        filters=[
            NotchFilter(notch_hz=60.0, sample_rate_hz=sample_rate_hz),
            BandpassFilter(low_hz=20.0, high_hz=400.0, sample_rate_hz=sample_rate_hz),
            RectificationFilter(),
            LowpassFilter(cutoff_hz=8.0, sample_rate_hz=sample_rate_hz),
        ]
    )

    timestamps: list[int] = []
    raw_values: list[float] = []
    envelope_values: list[float] = []

    # speed=0 -> read as fast as possible, no real-time delay, since
    # we only care about the data here, not real-time playback.
    with ReplayDevice(csv_path, sample_rate=sample_rate_hz, speed=0) as device:
        while True:
            line = device.read_line()
            if line is None:
                break  # ReplayDevice signals end of file this way

            ts_str, raw_str = line.strip().split(",")
            timestamp_us = int(ts_str)
            raw_value = float(raw_str)

            envelope_value = processor.process_value(raw_value)

            timestamps.append(timestamp_us)
            raw_values.append(raw_value)
            envelope_values.append(envelope_value)

    time_s = [(t - timestamps[0]) / 1_000_000 for t in timestamps]

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(12, 6))

    axes[0].plot(time_s, raw_values, linewidth=0.7, color='steelblue')
    axes[0].set_title("Raw EMG Signal")
    axes[0].set_ylabel("ADC value")
    axes[0].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(time_s, envelope_values, linewidth=1.0, color='darkorange')
    axes[1].set_title("Continuous Envelope (Notch + Bandpass + Rectification + Lowpass 8Hz)")
    axes[1].set_ylabel("Envelope amplitude")
    axes[1].set_xlabel("Time (s)")
    axes[1].axhline(y=0, color='k', linestyle='--', linewidth=0.5, alpha=0.5)
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.validate_dsp <path_to_csv>")
        sys.exit(1)
    main(sys.argv[1])