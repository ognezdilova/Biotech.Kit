"""Orchestrates the acquisition flow: device -> parser -> consumers.

Acquisition runs continuously, emitting samples to registered consumers.
Consumers handle their own lifecycle (e.g., recording start/stop, visualization).
"""

import threading

from core.consumer import SampleConsumer
from core.device import AcquisitionDevice
from core.digital_signal_processing.dsp_base import SignalProcessor
from core.parser import SignalParser


class AcquisitionSession:
    """Ties together a device, a parser, and sample consumers.

    Raw samples are emitted to all `consumers`. If a `processor` is
    provided, each raw sample is additionally run through it and the
    filtered result is sent to `processed_consumers`. This keeps raw
    and processed data flows independent.

    Acquisition runs continuously regardless of consumer state (e.g.,
    recording may be stopped while acquisition continues). Consumers
    manage their own lifecycle independently.

    The session depends only on abstract interfaces, so device/parser/
    consumers/processor can be swapped independently.
    """

    def __init__(
        self,
        device: AcquisitionDevice,
        parser: SignalParser,
        consumers: list[SampleConsumer] | None = None,
        processor: SignalProcessor | None = None,
        processed_consumers: list[SampleConsumer] | None = None,
    ) -> None:
        self._device = device
        self._parser = parser
        self._consumers = consumers or []
        self._processor = processor
        self._processed_consumers = processed_consumers or []
        self._sample_count = 0
        self._stop_event = threading.Event()

    @property
    def sample_count(self) -> int:
        return self._sample_count

    def stop(self) -> None:
        """Signal the acquisition loop to stop gracefully."""
        self._stop_event.set()

    def run(self) -> None:
        """Run the acquisition loop. Blocking call.
        
        Continuously reads from device, parses samples, and emits to
        all registered consumers. Consumers manage their own lifecycle
        (the session does not open/close them).
        """
        with self._device:
            self._loop()

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            raw_line = self._device.read_line()
            if not raw_line:
                continue

            sample = self._parser.parse(raw_line)
            if sample is None:
                continue

            # Emit raw sample to all consumers
            for consumer in self._consumers:
                consumer.consume(sample)

            # If processor exists, emit filtered sample to processed consumers
            filtered_sample = None
            if self._processor is not None:
                filtered_sample = self._processor.process(sample)
                for consumer in self._processed_consumers:
                    consumer.consume(filtered_sample)

            self._sample_count += 1
            if self._sample_count % 1000 == 0:
                print(f"Processed {self._sample_count} samples...")
                # Debug: show sample values to verify data flow
                if self._sample_count == 1000:
                    filt_val = f"{filtered_sample.value:.2f}" if filtered_sample else "N/A"
                    print(f"  Sample check - Raw: {sample.value:.2f}, Filtered: {filt_val}")
