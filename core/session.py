"""Orchestrates the acquisition flow: device -> parser -> sinks."""

from core.device import AcquisitionDevice
from core.digital_signal_processing.dsp_base import SignalProcessor
from core.parser import SignalParser
from core.sink import DataSink


class AcquisitionSession:
    """Ties together a device, a parser, one or more sinks, and an optional signal processor.

    Raw samples always go to `sinks` unmodified. If a `processor` is
    provided, each raw sample is additionally run through it and the
    filtered result is sent to `processed_sinks`. This keeps recorded
    raw data untouched regardless of filter design, so DSP experiments
    can always be re-run against the same original recording.

    The session depends only on the abstract interfaces, never on
    concrete implementations, so device/parser/sinks/processor can be swapped
    independently of each other and of this class.
    """

    def __init__(
        self,
        device: AcquisitionDevice,
        parser: SignalParser,
        sinks: list[DataSink],
        processor: SignalProcessor | None = None,
        processed_sinks: list[DataSink] | None = None,
    ) -> None:
        self._device = device
        self._parser = parser
        self._sinks = sinks
        self._processor = processor
        self._processed_sinks = processed_sinks or []
        self._sample_count = 0

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def run(self) -> None:
        """Run the acquisition loop. Blocking call."""
        with self._device:
            for sink in self._sinks:
                sink.open()
            for sink in self._processed_sinks:
                sink.open()

            try:
                self._loop()
            finally:
                for sink in self._sinks:
                    sink.close()
                for sink in self._processed_sinks:
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

            if self._processor is not None:
                filtered_sample = self._processor.process(sample)
                for sink in self._processed_sinks:
                    sink.write(filtered_sample)

            self._sample_count += 1
            if self._sample_count % 1000 == 0:
                print(f"Recorded {self._sample_count} samples...")
