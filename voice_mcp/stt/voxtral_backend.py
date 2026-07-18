"""Opt-in low-latency streaming STT backend: Voxtral Realtime (4B, int4) via mlx-audio.

Matches the original voice-mcp project's STT choice. Heavier download (~2.5GB)
and more memory than Whisper; enable via `voice_config set stt_backend voxtral`.
"""
from __future__ import annotations

import tempfile

import numpy as np
import soundfile as sf

MODEL_ID = "mlx-community/Voxtral-Mini-4B-Realtime-fp16"

_model = None


def _load():
    global _model
    if _model is None:
        from mlx_audio.stt.utils import load

        _model = load(MODEL_ID)
    return _model


def transcribe(audio: np.ndarray, sample_rate: int, language: str | None = None) -> str:
    model = _load()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        sf.write(tmp.name, audio, sample_rate)
        result = model.generate(tmp.name)
    return getattr(result, "text", str(result)).strip()
