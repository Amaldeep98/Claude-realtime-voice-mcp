"""Shared config for claude-voice-mcp.

Loaded independently by the MCP server (voice_mcp/tools.py) and the standalone
Stop hook (hooks/speak_on_stop.py) so the hook can speak without the MCP
server needing to be mid-request. A project-local .voice-mcp.json (if present
in the current working directory) overrides the user-level config.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

USER_CONFIG_DIR = Path.home() / ".claude-voice-mcp"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.json"
PROJECT_CONFIG_NAME = ".voice-mcp.json"
LOCK_PATH = USER_CONFIG_DIR / "listen.lock"

DEFAULTS: dict[str, Any] = {
    "auto_speak": True,
    # off | brief | full
    "auto_speak_verbosity": "brief",
    # kokoro | elevenlabs
    "tts_backend": "kokoro",
    "voice": "af_heart",
    "elevenlabs_voice_id": None,
    "speed": 1.0,
    # whisper | voxtral
    "stt_backend": "whisper",
    "language": "a",
    # trailing silence needed to end a recording, once you've started
    # talking -- generous by default so a mid-sentence pause doesn't cut
    # you off early
    "vad_silence_ms": 5000,
    "audio_cues": True,
    "notifications": True,
    # spoken-summary length cap for "brief" verbosity
    "brief_max_chars": 320,
    # when true, the Stop hook listens again after speaking so a voice
    # conversation continues without retyping /talk each turn
    "hands_free": False,
    # how long the hands-free re-listen waits for you to start talking
    # before it gives up and turns itself off
    "hands_free_idle_seconds": 90,
}

VALID_KEYS = set(DEFAULTS.keys())


def _project_config_path() -> Path:
    return Path.cwd() / PROJECT_CONFIG_NAME


def load() -> dict[str, Any]:
    cfg = dict(DEFAULTS)

    if USER_CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(USER_CONFIG_PATH.read_text()))
        except (json.JSONDecodeError, OSError):
            pass

    project_path = _project_config_path()
    if project_path.exists():
        try:
            cfg.update(json.loads(project_path.read_text()))
        except (json.JSONDecodeError, OSError):
            pass

    return cfg


def save(cfg: dict[str, Any], *, project_local: bool = False) -> Path:
    target = _project_config_path() if project_local else USER_CONFIG_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    return target


def set_value(key: str, value: Any, *, project_local: bool = False) -> dict[str, Any]:
    if key not in VALID_KEYS:
        raise KeyError(f"Unknown config key '{key}'. Valid keys: {sorted(VALID_KEYS)}")
    cfg = load()
    cfg[key] = _coerce(key, value)
    save(cfg, project_local=project_local)
    return cfg


def _coerce(key: str, value: Any) -> Any:
    """Coerce string values (as would arrive from an MCP tool call) to the right type."""
    if not isinstance(value, str):
        return value
    default = DEFAULTS[key]
    if isinstance(default, bool):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(default, float):
        return float(value)
    if isinstance(default, int):
        return int(value)
    if value.lower() == "null" and default is None:
        return None
    return value


def is_listen_locked() -> bool:
    return LOCK_PATH.exists()


class ListenLock:
    """Held while listen() is recording so the Stop hook / speak() never talks over the mic."""

    def __enter__(self) -> "ListenLock":
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCK_PATH.write_text(str(os.getpid()))
        return self

    def __exit__(self, *exc: Any) -> None:
        LOCK_PATH.unlink(missing_ok=True)
