"""Default local TTS backend: Kokoro-82M via mlx-audio. 54 voices / 9 languages."""
from __future__ import annotations

import numpy as np

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
DEFAULT_SAMPLE_RATE = 24000

# Ground truth from hexgrad/Kokoro-82M VOICES.md, used as a fallback if the
# loaded model doesn't expose its own voice list at runtime.
VOICES: dict[str, list[str]] = {
    "a": [  # American English
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
        "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael",
        "am_onyx", "am_puck", "am_santa",
    ],
    "b": ["bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable", "bm_george", "bm_lewis"],  # British English
    "e": ["ef_dora", "em_alex", "em_santa"],  # Spanish
    "f": ["ff_siwis"],  # French
    "h": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"],  # Hindi
    "i": ["if_sara", "im_nicola"],  # Italian
    "j": ["jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"],  # Japanese
    "p": ["pf_dora", "pm_alex", "pm_santa"],  # Brazilian Portuguese
    "z": ["zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi", "zm_yunjian", "zm_yunxi", "zm_yunxia", "zm_yunyang"],  # Mandarin
}

LANGUAGE_NAMES = {
    "a": "American English", "b": "British English", "e": "Spanish", "f": "French",
    "h": "Hindi", "i": "Italian", "j": "Japanese", "p": "Brazilian Portuguese", "z": "Mandarin Chinese",
}

_model = None


def _load():
    global _model
    if _model is None:
        from mlx_audio.tts.utils import load_model

        _model = load_model(MODEL_ID)
    return _model


def list_voices(language: str | None = None) -> list[dict]:
    voices = VOICES
    if language:
        voices = {language: VOICES.get(language, [])}
    return [
        {"id": voice_id, "language": lang, "language_name": LANGUAGE_NAMES[lang]}
        for lang, ids in voices.items()
        for voice_id in ids
    ]


def synthesize(text: str, voice: str, speed: float, lang: str) -> tuple[np.ndarray, int]:
    model = _load()
    chunks = []
    sample_rate = DEFAULT_SAMPLE_RATE
    for result in model.generate(text=text, voice=voice, speed=speed, lang_code=lang):
        audio = np.asarray(result.audio, dtype=np.float32)
        chunks.append(audio)
        sample_rate = getattr(result, "sample_rate", sample_rate)
    if not chunks:
        return np.zeros(0, dtype=np.float32), sample_rate
    return np.concatenate(chunks), sample_rate
