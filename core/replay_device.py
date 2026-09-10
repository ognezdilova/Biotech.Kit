"""Replay device that reads CSV recordings and mimics a live AcquisitionDevice."""

from __future__ import annotations
from typing import Iterator
import csv
import time
from pathlib import Path
from typing import TextIO

from core.device import AcquisitionDevice


class ReplayDevice(AcquisitionDevice):
    """Replays a CSV recording through the same interface as a live device.

    Reads CSV files produced by CSVSink and returns raw lines in the same
    format that a live device would emit, preserving original timing or
    allowing configurable playback speed.

    Expected CSV format:
        Header: timestamp,raw_value[,channel]
        Data rows: <timestamp_us>,<value>[,<channel>]
    """

    def __init__(
        self,
        filepath: str,
        speed: float = 1.0,
        sample_rate: float | None = None,
    ) -> None:
        """Initialize a replay device.

        Args:
            filepath: Path to the CSV file to replay.
            speed: Playback speed multiplier (1.0 = real-time, 2.0 = 2x faster,
                   0 or None = as fast as possible with no delays).
            sample_rate: Fallback sample rate (Hz) for synthetic timing if the
                         CSV contains no usable timestamps. If None and timestamps
                         are missing, playback will be as fast as possible.
        """
        self._filepath = Path(filepath)
        self._speed = speed if speed is not None and speed > 0 else 0
        self._sample_rate = sample_rate
        self._file: TextIO | None = None
        self._reader: Iterator[list[str]] | None = None
        self._prev_timestamp_us: int | None = None
        self._prev_real_time: float | None = None
        self._use_synthetic_timing = False
        self._synthetic_interval_s: float | None = None
        self._row_count = 0
        self._has_channel_column = False

    def open(self) -> None:
        """Open the CSV file and prepare for replay."""
        if not self._filepath.exists():
            raise FileNotFoundError(f"Replay file not found: {self._filepath}")

        self._file = open(self._filepath, "r", newline="")
        self._reader = csv.reader(self._file)

        # Read and validate header
        try:
            header = next(self._reader)
        except StopIteration:
            self._file.close()
            raise ValueError(f"CSV file is empty: {self._filepath}")

        if len(header) < 2 or header[0] != "timestamp" or header[1] != "raw_value":
            self._file.close()
            raise ValueError(
                f"CSV file has invalid header. Expected ['timestamp', 'raw_value'], "
                f"got {header}"
            )

        self._has_channel_column = len(header) >= 3 and header[2] == "channel"

        # Peek at first data row to check if timestamps are usable
        try:
            first_row = next(self._reader)
            # Try to parse timestamp
            try:
                int(first_row[0])
                self._use_synthetic_timing = False
            except (ValueError, IndexError):
                # Timestamps are not usable, fall back to sample_rate
                if self._sample_rate is not None and self._sample_rate > 0:
                    self._use_synthetic_timing = True
                    self._synthetic_interval_s = 1.0 / self._sample_rate
                # else: no timing at all, play as fast as possible

            # Close and reopen to reset to start
            self._file.seek(0)
            self._reader = csv.reader(self._file)
            next(self._reader)  # Skip header again
        except StopIteration:
            # File has header but no data
            pass

        self._prev_timestamp_us = None
        self._prev_real_time = None
        self._row_count = 0

    def close(self) -> None:
        """Close the CSV file."""
        if self._file is not None:
            self._file.close()
            self._file = None
        self._reader = None
        self._prev_timestamp_us = None
        self._prev_real_time = None

    def read_line(self) -> str | None:
        """Read one line from the CSV and return it in raw device format.

        Returns raw line in the format "<timestamp_us>,<raw_value>" to match
        the format expected by ESP32EMGParser.

        Returns None when the end of the recording is reached.
        """
        if self._reader is None:
            raise RuntimeError("Device is not open. Call open() first.")

        try:
            row = next(self._reader)
        except StopIteration:
            # End of file reached
            return None

        if len(row) < 2:
            # Malformed row, skip it by returning None (consistent with
            # how live devices handle bad data)
            return None

        timestamp_str, value_str = row[0], row[1]
        channel_str = row[2] if self._has_channel_column and len(row) >= 3 else None

        # Validate that we can parse the values
        try:
            timestamp_us = int(timestamp_str)
            int(value_str)  # Validate value is an integer
            if channel_str is not None:
                int(channel_str)
        except ValueError:
            # Malformed data, skip it
            return None

        # Handle timing/delay before returning the line
        self._handle_timing(timestamp_us)

        self._row_count += 1
        if channel_str is None:
            return f"{timestamp_str},{value_str}"
        return f"{timestamp_str},{value_str},ch{channel_str}"

    def _handle_timing(self, timestamp_us: int) -> None:
        """Apply appropriate delay to respect original timing or playback speed."""
        if self._speed == 0:
            # No delay mode: return as fast as possible
            return

        current_real_time = time.time()

        if self._use_synthetic_timing:
            # Use constant interval based on sample_rate
            if self._prev_real_time is not None and self._synthetic_interval_s is not None:
                elapsed = current_real_time - self._prev_real_time
                target_interval = self._synthetic_interval_s / self._speed
                sleep_time = target_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
            self._prev_real_time = time.time()
        else:
            # Use actual timestamps from CSV
            if self._prev_timestamp_us is not None:
                delta_us = timestamp_us - self._prev_timestamp_us
                if delta_us > 0:
                    # Scale by speed (higher speed = shorter delay)
                    delay_s = (delta_us / 1_000_000) / self._speed
                    # Adjust for time already elapsed since last sample
                    elapsed = current_real_time - self._prev_real_time
                    sleep_time = delay_s - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)

            self._prev_timestamp_us = timestamp_us
            self._prev_real_time = time.time()
