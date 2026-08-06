"""Abstract interface for parsing raw data into Sample objects."""

from abc import ABC, abstractmethod

from core.models import Sample


class SignalParser(ABC):
    """Abstract parser that converts a raw data line into a Sample.

    Concrete implementations depend on the firmware/board data format
    (e.g. CSV-style text line, binary packet, etc).
    """

    @abstractmethod
    def parse(self, raw_line: str) -> Sample | None:
        """Parse one raw line.

        Returns None if the line does not match the expected format —
        malformed lines are expected occasionally on real hardware links
        and must not raise an exception.
        """
        raise NotImplementedError
