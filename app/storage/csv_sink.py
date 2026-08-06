"""CSV file implementation of DataSink."""

import csv
import os
from datetime import datetime
from typing import TextIO

from core.models import Sample
from core.sink import DataSink


class CSVSink(DataSink):
    """Writes samples to a timestamped CSV file."""

    def __init__(self, output_dir: str = "data/recordings", flush_every: int = 1000) -> None:
        self._output_dir = output_dir
        self._flush_every = flush_every
        self._file: TextIO | None = None
        self._writer: "csv._writer | None" = None
        self._written = 0
        self.filepath: str | None = None

    def open(self) -> None:
        os.makedirs(self._output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(self._output_dir, f"emg_data_{timestamp}.csv")

        self._file = open(self.filepath, "w", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["timestamp", "raw_value"])

        print(f"Saving data to {self.filepath}")

    def write(self, sample: Sample) -> None:
        if self._writer is None:
            raise RuntimeError("Sink is not open. Call open() first.")

        self._writer.writerow([sample.timestamp_us, sample.value])

        self._written += 1
        if self._written % self._flush_every == 0:
            self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            print(f"Data saved to: {self.filepath}  ({self._written} samples)")
        self._file = None
        self._writer = None