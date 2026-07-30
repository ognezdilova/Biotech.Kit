"""Abstract interface for data sinks (consumers of parsed samples)."""

from abc import ABC, abstractmethod

from app.core.models import Sample


class DataSink(ABC):
    """Abstract consumer of parsed Sample objects."""

    @abstractmethod
    def open(self) -> None:
        """Prepare the sink to receive data (e.g. open a file)."""
        raise NotImplementedError

    @abstractmethod
    def write(self, sample: Sample) -> None:
        """Write/handle one sample."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        """Finalize the sink (e.g. close a file)."""
        raise NotImplementedError

    def __enter__(self) -> "DataSink":
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
