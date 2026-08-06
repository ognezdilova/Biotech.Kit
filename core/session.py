"""Orchestrates the acquisition flow: device -> parser -> sinks."""

from core.device import AcquisitionDevice
from core.parser import SignalParser
from core.sink import DataSink


class AcquisitionSession:
    """Ties together a device, a parser, and one or more sinks.

    The session depends only on the abstract interfaces, never on
    concrete implementations, so device/parser/sinks can be swapped
    independently of each other and of this class.
    """

    def __init__(
        self,
        device: AcquisitionDevice,
        parser: SignalParser,
        sinks: list[DataSink],
    ) -> None:
        self._device = device
        self._parser = parser
        self._sinks = sinks
        self._sample_count = 0

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def run(self) -> None:
        """Run the acquisition loop. Blocking call."""
        with self._device:
            for sink in self._sinks:
                sink.open()

            try:
                self._loop()
            finally:
                for sink in self._sinks:
                    sink.close()

    def _loop(self) -> None:
        while True:
            raw_line = self._device.read_line()
            if not raw_line:
                continue

            sample = self._parser.parse(raw_line)
            if sample is None:
                continue

            for sink in self._sinks:
                sink.write(sample)

            self._sample_count += 1
            if self._sample_count % 1000 == 0:
                print(f"Recorded {self._sample_count} samples...")
