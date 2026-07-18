from __future__ import annotations

from typing import Protocol

import numpy as np


class TtsBackend(Protocol):
    def synthesize(self, text: str, voice: str, speed: float, lang: str) -> tuple[np.ndarray, int]:
        """Return (audio, sample_rate)."""
        ...

    def list_voices(self, language: str | None = None) -> list[dict]:
        ...
