"""Pre-download the default local models so first real use isn't slow.

Run via `uv run scripts/warmup.py`. Safe to re-run.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice_mcp.stt import whisper_backend
from voice_mcp.tts import kokoro_backend


def main() -> None:
    print(f"Downloading/loading TTS model: {kokoro_backend.MODEL_ID}")
    kokoro_backend._load()
    print("Kokoro ready.")

    print(f"Downloading/loading STT model: {whisper_backend.MODEL_ID}")
    whisper_backend._load()
    print("Whisper ready.")

    print("Warmup complete.")


if __name__ == "__main__":
    main()
