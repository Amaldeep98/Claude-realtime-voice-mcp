#!/usr/bin/env python3
"""Claude Code Stop hook: speaks a brief summary of every assistant turn, and
(when hands-free mode is armed) keeps a voice conversation going.

This is what makes auto-speak *guaranteed* rather than dependent on Claude
remembering to call a speak() tool: Claude Code invokes this on every Stop
event and it runs independently of the MCP server. It uses the
`last_assistant_message` field the Stop hook input already provides (per
Claude Code's hook docs) rather than parsing the transcript file, since the
transcript is written asynchronously and can lag.

Hands-free mode (armed by /talk, toggled via voice_config key="hands_free"):
after speaking, this listens again. If it hears something, it emits
`{"decision": "block", "reason": <what you said>}` so Claude Code continues
the conversation with that as the next input -- no retyping /talk needed. If
you say a stop phrase, or stay quiet past `hands_free_idle_seconds`, hands-free
turns itself off and the turn ends normally.

Performance note: this script is spawned fresh by Claude Code on every single
turn. Talking to the voice daemon (voice_mcp/daemon.py, a background thread in
the long-lived MCP server process) means we reuse already-warm Kokoro/Whisper
models instead of reloading them from scratch every time -- that reload was
taking 5+ seconds on its own. voice_mcp.audio_io/stt/tts (which pull in
mlx/mlx_audio/transformers) are only imported here as a fallback if the
daemon isn't reachable, so the common case stays fast.

Never blocks the turn on its own account: speaking/listening failures are
swallowed so a broken mic or model never surfaces as a stuck conversation.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voice_mcp import config, ipc_client, summarizer  # noqa: E402
from voice_mcp.stt_guard import is_echo_of, looks_like_hallucinated_repeat, strip_hallucinated_tail  # noqa: E402

DEBUG_LOG_PATH = config.USER_CONFIG_DIR / "hook_debug.log"
# Claiming a prompt_id atomically means only one hook invocation for a given
# turn ever proceeds, even if this script is registered in multiple scopes
# at once (e.g. both a project's .claude/settings.json and the global
# ~/.claude/settings.json fire for the same Stop event when working inside
# that project) -- otherwise Claude audibly speaks the same reply twice.
CLAIMS_DIR = config.USER_CONFIG_DIR / "prompt_claims"


def _log(msg: str) -> None:
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG_PATH.open("a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def _claim_prompt(prompt_id: str | None) -> bool:
    """True if this invocation is the first (and only) one to claim
    `prompt_id` -- callers should no-op entirely if this returns False."""
    if not prompt_id:
        return True  # older Claude Code without prompt_id -- can't dedup, proceed as before
    try:
        CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(CLAIMS_DIR / f"{prompt_id}.claim"), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        return False
    except OSError:
        return True  # claim-tracking itself failed -- don't let that block real work
    _cleanup_old_claims()
    return True


def _cleanup_old_claims(max_age_seconds: float = 3600) -> None:
    try:
        cutoff = time.time() - max_age_seconds
        for path in CLAIMS_DIR.glob("*.claim"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
    except OSError:
        pass


STOP_PHRASES = {
    "stop listening",
    "stop listening please",
    "that's all",
    "that's all for now",
    "that will be all",
    "end voice mode",
    "turn off voice mode",
    "cancel voice mode",
    "stop voice mode",
    "exit voice mode",
}


def _speak(cfg: dict, text: str) -> None:
    response = ipc_client.call("speak", text=text, voice=cfg["voice"], speed=cfg["speed"], lang=cfg["language"])
    if response is not None and response.get("ok"):
        return

    from voice_mcp import audio_io, tts  # heavy fallback: daemon unreachable

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


def _listen_once(cfg: dict) -> tuple[str, bool]:
    """Returns (transcribed_text, speech_detected)."""
    response = ipc_client.call("hands_free_listen", idle_seconds=cfg["hands_free_idle_seconds"])
    _log(f"hands_free_listen daemon response: {response!r}")
    if response is not None and response.get("ok"):
        return response.get("text", ""), response.get("speech_detected", False)
    if response is not None and not response.get("ok"):
        _log(f"daemon returned an error, falling back to direct recording: {response.get('error')!r}")

    from voice_mcp import audio_io, stt  # heavy fallback: daemon unreachable

    def on_start():
        if cfg["audio_cues"]:
            audio_io.cue_listening_start()
        if cfg["notifications"]:
            audio_io.notify("Voice MCP", "Listening...")

    with config.ListenLock():
        audio, speech_detected = audio_io.record_until_silence(
            max_seconds=cfg["hands_free_idle_seconds"],
            silence_ms=cfg["vad_silence_ms"],
            on_start=on_start,
        )
    if cfg["audio_cues"]:
        audio_io.cue_listening_stop()
    _log(f"fallback recording: speech_detected={speech_detected} audio_samples={audio.size}")

    if not speech_detected or audio.size == 0:
        return "", speech_detected

    text = stt.transcribe(audio, audio_io.SAMPLE_RATE, cfg["stt_backend"], cfg["language"])
    _log(f"fallback transcription: {text!r}")
    return text.strip(), speech_detected


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        _log(f"failed to parse stdin JSON: {exc}")
        return

    prompt_id = payload.get("prompt_id")
    if not _claim_prompt(prompt_id):
        _log(f"duplicate hook invocation for prompt_id={prompt_id!r} (multiple hook scopes registered), skipping")
        return

    cfg = config.load()
    _log(f"--- stop hook fired: auto_speak={cfg['auto_speak']} hands_free={cfg['hands_free']} ---")

    spoken_text = None
    if cfg["auto_speak"] and cfg["auto_speak_verbosity"] != "off" and not config.is_listen_locked():
        raw_text = payload.get("last_assistant_message") or ""
        text = summarizer.build_spoken_summary(
            raw_text, verbosity=cfg["auto_speak_verbosity"], max_chars=cfg["brief_max_chars"]
        )
        if text:
            try:
                _speak(cfg, text)
                _log(f"spoke: {text!r}")
                spoken_text = text
            except Exception as exc:
                _log(f"speak failed: {exc}")

    if not cfg["hands_free"] or config.is_listen_locked():
        _log("hands_free off or listen-locked, done")
        return

    if spoken_text:
        # let any room echo/reverb from our own speaker output decay before
        # opening the mic again -- reduces (but doesn't replace) the need for
        # the is_echo_of() check above
        time.sleep(0.6)

    try:
        heard, speech_detected = _listen_once(cfg)
    except Exception as exc:
        _log(f"listen failed: {exc}, disarming hands_free")
        config.set_value("hands_free", False)
        return

    _log(f"listen result: heard={heard!r} speech_detected={speech_detected}")

    if not speech_detected:
        config.set_value("hands_free", False)  # went quiet -- end hands-free gracefully
        _log("no speech detected within idle window, disarmed hands_free")
        return

    if not heard:
        _log("speech detected but transcription was empty, leaving hands_free on")
        return  # speech detected but nothing transcribed; don't tear down the session for a blip

    if spoken_text and is_echo_of(heard, spoken_text):
        _log(f"discarding acoustic echo of our own TTS output, leaving hands_free on: {heard!r}")
        return  # the mic picked up our own speaker output, not new user speech

    trimmed = strip_hallucinated_tail(heard)
    if trimmed != heard:
        _log(f"trimmed a hallucinated repeat tail: {heard!r} -> {trimmed!r}")
        heard = trimmed

    if not heard or looks_like_hallucinated_repeat(heard):
        _log(f"discarding likely STT hallucination (repetitive garbage), leaving hands_free on: {heard!r}")
        return  # ambient noise mis-flagged as speech; don't feed garbage into the conversation

    if heard.lower().strip(" .!?") in STOP_PHRASES:
        config.set_value("hands_free", False)
        _log("stop phrase matched, disarmed hands_free")
        try:
            _speak(cfg, "Voice mode off.")
        except Exception:
            pass
        return

    _log(f"emitting decision:block with reason={heard!r}")
    print(json.dumps({"decision": "block", "reason": heard}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
