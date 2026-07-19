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

# Our config's `language` uses Kokoro's single-letter voice-language codes;
# Whisper expects its own ISO-ish codes. Translate between the two so STT is
# actually constrained to the expected language instead of auto-detecting
# per utterance (which is how ambient noise turned into stray Korean text).
_LANGUAGE_MAP = {
    "a": "en", "b": "en", "e": "es", "f": "fr", "h": "hi",
    "i": "it", "j": "ja", "p": "pt", "z": "zh",
}

_model = None


def _load():
    global _model
    if _model is None:
        from mlx_audio.stt.utils import load

        _model = load(MODEL_ID)
    return _model


def _build_initial_prompt() -> str | None:
    from .. import config

    words = config.load().get("stt_vocabulary") or []
    if not words:
        return None
    # Whisper doesn't take a vocabulary list directly -- the standard trick
    # is priming it with a short prompt that uses the words naturally, which
    # biases decoding toward them (see /vocab in README for how this is set).
    return "Vocabulary: " + ", ".join(words) + "."


def transcribe(audio: np.ndarray, sample_rate: int, language: str | None = None) -> str:
    model = _load()
    whisper_language = _LANGUAGE_MAP.get(language, language)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        sf.write(tmp.name, audio, sample_rate)
        result = model.generate(
            tmp.name,
            language=whisper_language,
            initial_prompt=_build_initial_prompt(),
            # Whisper's own defense against hallucinating text during
            # silence/noise segments -- off by default, worth having on here.
            hallucination_silence_threshold=2.0,
        )
    return getattr(result, "text", str(result)).strip()
