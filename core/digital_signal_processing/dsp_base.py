"""Abstract base for DSP filter stages and the composable SignalProcessor."""

from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass, replace

import numpy as np

from core.digital_signal_processing.buffering import Window
from core.models import Sample


class Filter(ABC):
    """A single, stateful, causal signal-processing stage.

    Operates on one scalar value at a time so the exact same code path
    is used for live acquisition (called once per incoming sample) and
    offline validation (called in a loop fed by ReplayDevice) - no
    separate "batch mode" is required.

    Concrete filters are expected to be causal (IIR/FIR) and to carry
    their own internal state (e.g. scipy `zi` coefficients) between
    calls to `process()`.
    """

    @abstractmethod
    def process(self, value: float) -> float:
        """Process a single input value and return the filtered output."""
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Clear internal filter state (e.g. at the start of a new session)."""
        raise NotImplementedError


class SignalProcessor:
    """An ordered, composable chain of Filter stages.

    Applies each filter in sequence to a Sample's value and returns a
    new Sample with the filtered value. The input Sample is never
    mutated (Sample is frozen).

    Filter order matters and is not validated - it is the caller's
    responsibility to order filters sensibly (e.g. notch -> bandpass
    -> smoothing for a typical EMG chain).
    """

    def __init__(self, filters: list[Filter]) -> None:
        self._filters = filters
        self._filters_by_channel: dict[int, list[Filter]] = {}

    def process_value(self, value: float) -> float:
        """Run a raw numeric value through the full filter chain.

        Useful for validation/tooling that works with plain numbers
        rather than full Sample objects (e.g. scripts reading raw CSV
        rows directly, without going through a SignalParser).
        """
        for f in self._filters:
            value = f.process(value)
        return value


    def process(self, sample: Sample) -> Sample:
        """Run a Sample's value through the full filter chain.
        Returns a new Sample with the filtered value; the input
        Sample is never mutated (Sample is frozen).
        """
        filters = self._filters_by_channel.get(sample.channel)
        if filters is None:
            # Keep channel states fully independent for interleaved streams.
            filters = copy.deepcopy(self._filters)
            self._filters_by_channel[sample.channel] = filters

        value: float = float(sample.value)
        for f in filters:
            value = f.process(value)
        return replace(sample, value=value)

    def reset(self) -> None:
        """Reset all filters in the chain (e.g. between sessions)."""
        for f in self._filters:
            f.reset()
        for channel_filters in self._filters_by_channel.values():
            for f in channel_filters:
                f.reset()
        self._filters_by_channel.clear()

class BlockProcessor(ABC):
    """A single, stateless-by-default, block-based signal-processing stage.

    Complements 'Filter': 'Filter' is causal and operates one scalar
    value at a time (correct for real-time IIR filtering like notch/
    bandpass). 'BlockProcessor' instead consumes a whole pre-assembled
    'Window' produced by 'WindowBuffer' (see buffering.py), and derives a result from it as
    a unit. This is the right shape for algorithms that are only
    meaningful over a block of samples: FFT, RMS, spectral analysis,
    envelope detection, and future ML feature extraction.

    Implementations should default to being stateless across calls
    (each 'process()' call depends only on the 'Window' it's given,
    not on previous windows), so windows can be replayed, reordered,
    or processed out of sequence. A concrete
    implementation that does need cross-window state (e.g. a running
    average) should document that explicitly, since it changes how the
    processor behaves under replay/reordering.
    """

    @property
    @abstractmethod
    def label(self) -> str:
        """Short, stable name identifying this processor's output
        (e.g. "rms", "fft_magnitude", "envelope"). Lets downstream
        consumers (sinks, plots, a future ML feature store) know what
        a 'BlockResult.values' array actually represents, without
        having to know which concrete class produced it.
        """
        raise NotImplementedError

    @abstractmethod
    def process(self, window: Window) -> "BlockResult":
        """Compute this processor's result for a single Window."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class BlockResult:
    """Output of one `BlockProcessor` applied to one `Window`.

    'values' has no fixed shape relationship to the
    source window's size: RMS collapses a window down to a single
    number ('values' of length 1), an FFT magnitude spectrum produces
    'window.size // 2 + 1' bins, envelope detection may return an
    array the same length as the window. 'label' disambiguates what
    'values' holds, and 'source_window' is kept (by reference, not
    copied) so consumers can still read channel/timing/sample-rate
    context ('source_window.sample_rate_hz()', etc.) without having to
    recompute or re-pass it separately.
    """

    label: str
    values: np.ndarray
    source_window: Window

    @property
    def channel(self) -> int:
        return self.source_window.channel


class BlockProcessorGroup:
    """Runs one Window through several independent BlockProcessors.

    Unlike 'SignalProcessor' (which threads a single value through
    filters sequentially, each stage's output feeding the next),
    'BlockProcessorGroup' runs every processor against the same
    input Window independently e.g. computing RMS and an FFT
    magnitude spectrum from the same window are two unrelated
    analyses, not two stages of one transform, so there is no
    meaningful "order" between them the way there is for notch ->
    bandpass filtering.
    """

    def __init__(self, processors: list[BlockProcessor]) -> None:
        self._processors = processors

    def process(self, window: Window) -> list[BlockResult]:
        return [processor.process(window) for processor in self._processors]      