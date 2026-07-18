"""Optional cloud TTS backend: ElevenLabs. Requires ELEVENLABS_API_KEY.

Callers (voice_mcp/tools.py, hooks/speak_on_stop.py) are expected to catch
ElevenLabsError and silently fall back to the local Kokoro backend -- cloud
voice is a pure enhancement, never a hard dependency.
"""
from __future__ import annotations

import os

import numpy as np
import requests

API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # ElevenLabs' public "Rachel" voice
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
SAMPLE_RATE = 24000
TIMEOUT_SECONDS = 20


class ElevenLabsError(RuntimeError):
    pass


def synthesize(text: str, voice: str | None, speed: float, lang: str) -> tuple[np.ndarray, int]:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set")

    voice_id = voice or DEFAULT_VOICE_ID
    try:
        response = requests.post(
            API_URL.format(voice_id=voice_id),
            params={"output_format": f"pcm_{SAMPLE_RATE}"},
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={
                "text": text,
                "model_id": DEFAULT_MODEL_ID,
                "voice_settings": {"speed": max(0.7, min(1.2, speed))},
            },
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ElevenLabsError(f"ElevenLabs request failed: {exc}") from exc

    if response.status_code != 200:
        raise ElevenLabsError(f"ElevenLabs returned {response.status_code}: {response.text[:200]}")

    pcm = np.frombuffer(response.content, dtype=np.int16).astype(np.float32) / 32768.0
    return pcm, SAMPLE_RATE


def list_voices() -> list[dict]:
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise ElevenLabsError("ELEVENLABS_API_KEY is not set")
    try:
        response = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ElevenLabsError(f"ElevenLabs request failed: {exc}") from exc

    return [
        {"id": v["voice_id"], "name": v.get("name", ""), "language": "cloud"}
        for v in response.json().get("voices", [])
    ]
