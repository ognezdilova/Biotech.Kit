"""
Offline visualizer for biosignal CSV recordings (EMG) produced by CSVSink in BiotechKit.

Usage:
    python view_csv.py data/recordings/emg_data_YYYYMMDD_HHMMSS.csv
    python view_csv.py data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --time-col timestamp --channels ch0 ch1
    python view_csv.py data/recordings/emg_data_YYYYMMDD_HHMMSS.csv --sample-rate 500

This script is NOT part of BK's core architecture — it's a temporary
diagnostic tool. Its only job is to let you quickly eyeball what was
recorded, before a proper real-time UI exists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def load_csv(path: Path) -> pd.DataFrame:
    """Load a recording CSV file into a DataFrame."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError(f"File {path} is empty or contains no data.")

    return df


def resolve_time_axis(
    df: pd.DataFrame,
    time_col: str | None,
    sample_rate: float | None,
) -> tuple[pd.Series, str]:
    """
    Decide what to use as the X axis:
    1. Explicitly provided time column (--time-col)
    2. Auto-detected timestamp/time column
    3. Synthetic time reconstructed from sample_rate
    4. Plain sample index (fallback)
    """
    if time_col is not None:
        if time_col not in df.columns:
            raise ValueError(f"Time column '{time_col}' not found in file.")
        return df[time_col], time_col

    for candidate in ("timestamp", "time", "t"):
        if candidate in df.columns:
            return df[candidate], candidate

    if sample_rate is not None and sample_rate > 0:
        synthetic_time = df.index / sample_rate
        return synthetic_time, "time (s), reconstructed from sample_rate"

    return df.index.to_series(), "sample index"


def resolve_channels(df: pd.DataFrame, channels: list[str] | None, time_col_name: str) -> list[str]:
    """
    Decide which columns should be treated as signal channels.
    If the user did not pass --channels explicitly, take all numeric
    columns except the one already used as the time axis.
    """
    if channels is not None:
        missing = [c for c in channels if c not in df.columns]
        if missing:
            raise ValueError(f"Channels not found in file: {missing}")
        return channels

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    return [c for c in numeric_cols if c != time_col_name]


def plot_signals(df: pd.DataFrame, x: pd.Series, x_label: str, channels: list[str], title: str) -> None:
    """Draw one subplot per channel, sharing a common X axis."""
    if not channels:
        raise ValueError("No numeric channels found to display.")

    fig, axes = plt.subplots(
        nrows=len(channels),
        ncols=1,
        sharex=True,
        figsize=(12, 3 * len(channels)),
        squeeze=False,
    )

    for ax, channel in zip(axes[:, 0], channels):
        ax.plot(x, df[channel], linewidth=0.8)
        ax.set_ylabel(channel)
        ax.grid(True, alpha=0.3)

    axes[-1, 0].set_xlabel(x_label)
    fig.suptitle(title)
    fig.tight_layout()
    plt.show()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline visualizer for BiotechKit CSV recordings")
    parser.add_argument("csv_path", type=Path, help="Path to the recording CSV file")
    parser.add_argument(
        "--time-col",
        type=str,
        default=None,
        help="Name of the time column (auto-detected by default)",
    )
    parser.add_argument(
        "--channels",
        type=str,
        nargs="+",
        default=None,
        help="List of channel columns to display (defaults to all numeric columns)",
    )
    parser.add_argument(
        "--sample-rate",
        type=float,
        default=None,
        help="Sampling rate in Hz, used if the file has no time column",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    try:
        df = load_csv(args.csv_path)
        x, x_label = resolve_time_axis(df, args.time_col, args.sample_rate)
        channels = resolve_channels(df, args.channels, x_label)
        plot_signals(df, x, x_label, channels, title=args.csv_path.name)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())