"""Abstract interface for sample consumers during acquisition.

Consumers receive samples as they arrive from the acquisition loop,
allowing for independent concerns like recording, visualization, and
real-time processing to operate in parallel without tight coupling.
"""

from abc import ABC, abstractmethod

from core.models import Sample


class SampleConsumer(ABC):
    """Abstract consumer of samples during acquisition.
    
    Unlike DataSink (which has explicit open/close lifecycle),
    a SampleConsumer is always ready to receive samples and handles
    its own internal state management.
    """

    @abstractmethod
    def consume(self, sample: Sample) -> None:
        """Process/handle one sample.
        
        Called by AcquisitionSession for each successfully parsed sample.
        The consumer decides internally whether to write, visualize,
        buffer, or otherwise process the sample.
        """
        raise NotImplementedError
