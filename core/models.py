"""Shared data structures used across all layers of BK."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Sample:
    """A single parsed signal sample."""
    timestamp_us: int
    value: int | float
    channel: int = 0  # placeholder for future multi-channel support
