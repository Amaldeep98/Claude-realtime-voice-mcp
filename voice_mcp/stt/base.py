from __future__ import annotations

from typing import Protocol

import numpy as np


class SttBackend(Protocol):
    def transcribe(self, audio: np.ndarray, sample_rate: int, language: str | None = None) -> str:
        """Return the transcribed text for the given mono int16/float audio."""
        ...
