"""Parser for the text-based EMG protocol emitted by the ESP32 firmware.

Expected raw line format: "<timestamp_us>,<raw_value>"
Example: "123456,789"
"""

from app.core.models import Sample
from app.core.parser import SignalParser


class ESP32EMGParser(SignalParser):
    """Parses comma-separated 'timestamp_us,raw_value' lines into Sample."""

    def parse(self, raw_line: str) -> Sample | None:
        parts = raw_line.split(",")
        if len(parts) != 2:
            return None

        timestamp_str, value_str = parts

        try:
            timestamp_us = int(timestamp_str)
            value = int(value_str)
        except ValueError:
            return None

        return Sample(timestamp_us=timestamp_us, value=value)