"""Abstract base for DSP filter stages and the composable SignalProcessor."""

from abc import ABC, abstractmethod
from dataclasses import replace

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
        value: float = float(sample.value)
        for f in self._filters:
            value = f.process(value)
        return replace(sample, value=value)

    def reset(self) -> None:
        """Reset all filters in the chain (e.g. between sessions)."""
        for f in self._filters:
            f.reset()