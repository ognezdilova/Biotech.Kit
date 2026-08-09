"""Concrete Filter implementations built on scipy.signal.

All filters here are IIR (Butterworth bandpass / iirnotch), operate
sample-by-sample via scipy.signal.lfilter with persisted filter state
(`zi`), and warm-start that state from the first input value (via
lfilter_zi) to avoid a startup transient.
"""

import numpy as np
from scipy.signal import butter, iirnotch, lfilter, lfilter_zi

from core.digital_signal_processing.dsp_base import Filter


class BandpassFilter(Filter):
    """Butterworth bandpass filter.

    Typical use: isolate the EMG frequency band (commonly ~20-450 Hz)
    from a raw signal, rejecting DC offset/drift and high-frequency
    noise outside the band of interest.
    """

    def __init__(
        self,
        low_hz: float,
        high_hz: float,
        sample_rate_hz: float,
        order: int = 4,
    ) -> None:
        self._sample_rate_hz = sample_rate_hz
        nyquist = sample_rate_hz / 2.0
        self._b, self._a = butter(
            order, [low_hz / nyquist, high_hz / nyquist], btype="band"
        )
        self._zi_template = lfilter_zi(self._b, self._a)
        self._zi: np.ndarray | None = None

    def process(self, value: float) -> float:
        if self._zi is None:
            # Warm-start with the first sample so there's no ramp-up
            # transient from an assumed zero initial state.
            self._zi = self._zi_template * value
        out, self._zi = lfilter(self._b, self._a, [value], zi=self._zi)
        return float(out[0])

    def reset(self) -> None:
        self._zi = None


class NotchFilter(Filter):
    """IIR notch filter for rejecting a narrow frequency band.

    Typical use: reject powerline interference (50 Hz in most of the
    world, 60 Hz in North America) from a raw signal.
    """

    def __init__(
        self,
        notch_hz: float,
        sample_rate_hz: float,
        quality_factor: float = 30.0,
    ) -> None:
        self._sample_rate_hz = sample_rate_hz
        nyquist = sample_rate_hz / 2.0
        self._b, self._a = iirnotch(notch_hz / nyquist, quality_factor)
        self._zi_template = lfilter_zi(self._b, self._a)
        self._zi: np.ndarray | None = None

    def process(self, value: float) -> float:
        if self._zi is None:
            self._zi = self._zi_template * value
        out, self._zi = lfilter(self._b, self._a, [value], zi=self._zi)
        return float(out[0])

    def reset(self) -> None:
        self._zi = None