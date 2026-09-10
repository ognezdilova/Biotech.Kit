"""Parser for the text-based EMG protocol emitted by the ESP32 firmware.

Supported raw line formats:
1) Single channel (legacy): "<timestamp_us>,<raw_value>"
2) Single sample with explicit channel: "<timestamp_us>,<raw_value>,ch<channel>"
3) Two channels in one line: "<timestamp_us>,<ch1_raw_value>,<ch2_raw_value>"
"""

from core.models import Sample
from core.parser import SignalParser


class ESP32EMGParser(SignalParser):
    """Parses one-line ESP32 EMG payloads into one or more Sample objects."""

    def parse(self, raw_line: str) -> Sample | None:
        samples = self.parse_many(raw_line)
        if not samples:
            return None
        return samples[0]

    def parse_many(self, raw_line: str) -> list[Sample]:
        parts = [p.strip() for p in raw_line.split(",")]

        if len(parts) == 2:
            timestamp_str, value_str = parts
            try:
                timestamp_us = int(timestamp_str)
                value = int(value_str)
            except ValueError:
                return []
            return [Sample(timestamp_us=timestamp_us, value=value, channel=0)]

        if len(parts) == 3:
            timestamp_str, second_str, third_str = parts
            try:
                timestamp_us = int(timestamp_str)
                second_value = int(second_str)
            except ValueError:
                return []

            # Explicit-channel rows from recordings/replay.
            if third_str.lower().startswith("ch"):
                try:
                    channel = int(third_str[2:])
                except ValueError:
                    return []
                return [
                    Sample(
                        timestamp_us=timestamp_us,
                        value=second_value,
                        channel=channel,
                    )
                ]

            # Otherwise treat as one timestamp carrying two BioAmp channels.
            try:
                third_value = int(third_str)
            except ValueError:
                return []
            return [
                Sample(timestamp_us=timestamp_us, value=second_value, channel=0),
                Sample(timestamp_us=timestamp_us, value=third_value, channel=1),
            ]

        return []