"""Default STT backend: Whisper large-v3-turbo via mlx-audio.

Free, local, well-tested, 99+ languages. Model weights are pulled once from
Hugging Face (mlx-community) and cached by mlx-audio/huggingface_hub.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

MODEL_ID = "mlx-community/whisper-large-v3-turbo-asr-fp16"

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
