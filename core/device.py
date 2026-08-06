"""Abstract interface for acquisition devices (raw data sources)."""

from abc import ABC, abstractmethod


class AcquisitionDevice(ABC):
    """Abstract source of raw data lines/bytes.

    Concrete implementations may use Serial (UART), BLE, USB HID,
    or a replay-from-file source. Upper layers depend only on this
    interface, never on a concrete transport.
    """

    @abstractmethod
    def open(self) -> None:
        """Open the connection to the device."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Close the connection to the device."""
        raise NotImplementedError

    @abstractmethod
    def read_line(self) -> str | None:
        """Read one raw line of data.

        Returns None if no data is available or the line could not
        be decoded — this is a normal condition, not an error.
        """
        raise NotImplementedError

    def __enter__(self) -> "AcquisitionDevice":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
