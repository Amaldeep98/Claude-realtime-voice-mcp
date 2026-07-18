from __future__ import annotations

import numpy as np

from . import elevenlabs_backend, kokoro_backend
from .elevenlabs_backend import ElevenLabsError


def synthesize(
    text: str, *, backend: str, voice: str, speed: float, lang: str, elevenlabs_voice_id: str | None
) -> tuple[np.ndarray, int, str]:
    """Return (audio, sample_rate, backend_used). Falls back to kokoro on any ElevenLabs failure."""
    if backend == "elevenlabs":
        try:
            audio, sr = elevenlabs_backend.synthesize(text, elevenlabs_voice_id, speed, lang)
            return audio, sr, "elevenlabs"
        except ElevenLabsError:
            pass  # silent fallback, per design: voice always works regardless of cloud status
    audio, sr = kokoro_backend.synthesize(text, voice, speed, lang)
    return audio, sr, "kokoro"


def list_voices(language: str | None = None) -> list[dict]:
    voices = kokoro_backend.list_voices(language)
    try:
        voices = voices + elevenlabs_backend.list_voices()
    except ElevenLabsError:
        pass
    return voices
