from __future__ import annotations

from typing import Any

from . import audio_io, config, stt, tts


def listen(duration: float | None = None) -> str:
    cfg = config.load()

    def on_start():
        if cfg["audio_cues"]:
            audio_io.cue_listening_start()
        if cfg["notifications"]:
            audio_io.notify("Voice MCP", "Listening...")

    with config.ListenLock():
        if duration:
            audio = audio_io.record_fixed(duration, on_start=on_start)
        else:
            audio = audio_io.record_until_silence(silence_ms=cfg["vad_silence_ms"], on_start=on_start)

    if cfg["audio_cues"]:
        audio_io.cue_listening_stop()

    if audio.size == 0:
        return ""

    text = stt.transcribe(audio, audio_io.SAMPLE_RATE, cfg["stt_backend"], cfg["language"])
    return text


def speak(
    text: str,
    voice: str | None = None,
    speed: float | None = None,
    lang: str | None = None,
) -> str:
    if config.is_listen_locked():
        return "Skipped: a listen() recording is currently active."

    cfg = config.load()
    audio, sample_rate, backend_used = tts.synthesize(
        text,
        backend=cfg["tts_backend"],
        voice=voice or cfg["voice"],
        speed=speed if speed is not None else cfg["speed"],
        lang=lang or cfg["language"],
        elevenlabs_voice_id=cfg["elevenlabs_voice_id"],
    )
    if cfg["notifications"]:
        audio_io.notify("Voice MCP", "Speaking...")
    audio_io.play(audio, sample_rate)
    return f"Spoke {len(text)} characters via {backend_used}."


def stop_speaking() -> str:
    audio_io.stop_playback()
    return "Stopped."


def list_voices(language: str | None = None) -> list[dict]:
    return tts.list_voices(language)


def voice_config(action: str, key: str | None = None, value: Any = None, project_local: bool = False) -> dict:
    if action == "get":
        cfg = config.load()
        return {key: cfg[key]} if key else cfg
    if action == "set":
        if not key:
            raise ValueError("voice_config(action='set') requires a key")
        return config.set_value(key, value, project_local=project_local)
    raise ValueError("action must be 'get' or 'set'")
