#!/usr/bin/env python3
"""Claude Code Stop hook: speaks a brief summary of every assistant turn.

This is what makes auto-speak *guaranteed* rather than dependent on Claude
remembering to call a speak() tool: Claude Code invokes this on every Stop
event and it runs independently of the MCP server. It uses the
`last_assistant_message` field the Stop hook input already provides (per
Claude Code's hook docs) rather than parsing the transcript file, since the
transcript is written asynchronously and can lag.

Never blocks the turn: always exits 0. Any failure here should be invisible
to the user, not a stuck conversation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice_mcp import audio_io, config, summarizer, tts  # noqa: E402


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    cfg = config.load()
    if not cfg["auto_speak"] or cfg["auto_speak_verbosity"] == "off":
        return
    if config.is_listen_locked():
        return  # never talk over an active listen() recording

    raw_text = payload.get("last_assistant_message") or ""
    text = summarizer.build_spoken_summary(
        raw_text, verbosity=cfg["auto_speak_verbosity"], max_chars=cfg["brief_max_chars"]
    )
    if not text:
        return

    try:
        audio, sample_rate, _ = tts.synthesize(
            text,
            backend=cfg["tts_backend"],
            voice=cfg["voice"],
            speed=cfg["speed"],
            lang=cfg["language"],
            elevenlabs_voice_id=cfg["elevenlabs_voice_id"],
        )
        if cfg["notifications"]:
            audio_io.notify("Voice MCP", "Speaking...")
        audio_io.play(audio, sample_rate)
    except Exception:
        return  # auto-speak failures must never surface as a broken turn


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
