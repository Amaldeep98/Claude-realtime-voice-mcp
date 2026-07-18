from __future__ import annotations

import numpy as np

from . import voxtral_backend, whisper_backend

_BACKENDS = {
    "whisper": whisper_backend,
    "voxtral": voxtral_backend,
}


def transcribe(audio: np.ndarray, sample_rate: int, backend: str, language: str | None = None) -> str:
    module = _BACKENDS.get(backend, whisper_backend)
    return module.transcribe(audio, sample_rate, language)
