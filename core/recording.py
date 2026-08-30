"""Recording lifecycle management, decoupled from acquisition.

Provides explicit start/stop control over when data is written to sinks,
allowing acquisition to run continuously while recording is paused or inactive.
Also provides adapters for using DataSink instances as SampleConsumers.
"""

from core.consumer import SampleConsumer
from core.models import Sample
from core.sink import DataSink


class RecordingController:
    """Manages recording lifecycle independently of acquisition.
    
    Wraps one or more DataSinks and provides explicit start/stop control.
    Samples are only written to sinks while recording is active.
    
    Usage:
        controller = RecordingController(sinks=[CSVSink(...)])
        controller.start_recording()  # Opens sinks
        # ... samples are written via write() ...
        controller.stop_recording()   # Closes sinks
    """

    def __init__(self, sinks: list[DataSink]) -> None:
        """Initialize a recording controller.
        
        Args:
            sinks: List of DataSink instances to manage. All sinks will
                   open/close together and receive the same samples.
        """
        self._sinks = sinks
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Check if recording is currently active."""
        return self._is_recording

    def start_recording(self) -> None:
        """Start recording -> opens all sinks.
        
        If already recording, this is a no-op.
        """
        if not self._is_recording:
            for sink in self._sinks:
                sink.open()
            self._is_recording = True

    def stop_recording(self) -> None:
        """Stop recording - closes all sinks.
        
        If not currently recording, this is a no-op.
        """
        if self._is_recording:
            for sink in self._sinks:
                sink.close()
            self._is_recording = False

    def write(self, sample: Sample) -> None:
        """Write sample to all sinks if recording is active.
        
        If recording is not active, the sample is silently ignored.
        
        Args:
            sample: Sample to write to sinks.
        """
        if self._is_recording:
            for sink in self._sinks:
                sink.write(sample)


class RecordingSampleConsumer(SampleConsumer):
    """Adapts RecordingController to the SampleConsumer interface.
    
    Allows a RecordingController to be used as a consumer in the
    acquisition pipeline, receiving samples and forwarding them to
    the controller's write() method.
    """

    def __init__(self, controller: RecordingController) -> None:
        """Initialize consumer with a recording controller.
        
        Args:
            controller: RecordingController to delegate samples to.
        """
        self._controller = controller

    @property
    def controller(self) -> RecordingController:
        """Access the underlying recording controller."""
        return self._controller

    def consume(self, sample: Sample) -> None:
        """Forward sample to the recording controller.
        
        The controller decides whether to write based on its internal
        recording state.
        
        Args:
            sample: Sample to forward to controller.
        """
        self._controller.write(sample)


class SinkConsumer(SampleConsumer):
    """Adapts a DataSink to the SampleConsumer interface.
    
    Manages the sink's lifecycle automatically: opens when created,
    writes on every consume(), and provides a close() method for cleanup.
    
    This allows legacy DataSink implementations (like WindowBuffer) to
    work with the new consumer-based architecture without modification.
    
    Usage:
        sink = WindowBuffer(window_size=256)
        consumer = SinkConsumer(sink)
        # sink.open() is called immediately
        
        session = AcquisitionSession(consumers=[consumer], ...)
        session.run()
        
        consumer.close()  # closes the sink when done
    """

    def __init__(self, sink: DataSink, auto_open: bool = True) -> None:
        """Initialize consumer with a data sink.
        
        Args:
            sink: DataSink to wrap.
            auto_open: If True, calls sink.open() immediately. If False,
                       caller must call open() manually before consuming.
        """
        self._sink = sink
        if auto_open:
            self._sink.open()

    @property
    def sink(self) -> DataSink:
        """Access the underlying sink."""
        return self._sink

    def consume(self, sample: Sample) -> None:
        """Forward sample to the sink's write() method.
        
        Args:
            sample: Sample to write to sink.
        """
        self._sink.write(sample)

    def open(self) -> None:
        """Explicitly open the sink if not auto-opened."""
        self._sink.open()

    def close(self) -> None:
        """Close the underlying sink."""
        self._sink.close()

    def __enter__(self) -> "SinkConsumer":
        """Support context manager protocol."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close sink on context exit."""
        self.close()
