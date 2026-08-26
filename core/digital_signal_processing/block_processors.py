"""Concrete BlockProcessor implementations.

Mirrors the split already used for the sample-by-sample side of the
DSP layer ('dsp_base.py' = abstractions, 'filters.py' = concrete
Filters): this module holds concrete 'BlockProcessor's, while
'dsp_base.py' defines the 'BlockProcessor' contract itself.
"""

import numpy as np

from core.digital_signal_processing.buffering import Window
from core.digital_signal_processing.dsp_base import BlockProcessor, BlockResult


class RMSProcessor(BlockProcessor):
    """Computes the root-mean-square amplitude of a Window.

    RMS is a standard EMG amplitude / muscle-activation-level measure:
    it collapses a whole window down to a single scalar, so
    'BlockResult.values' here always has shape (1,).
    """

    @property
    def label(self) -> str:
        return "rms"

    def process(self, window: Window) -> BlockResult:
        rms_value = float(np.sqrt(np.mean(np.square(window.values))))
        return BlockResult(
            label=self.label,
            values=np.array([rms_value]),
            source_window=window,
        )