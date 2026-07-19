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
            audio, _ = audio_io.record_until_silence(silence_ms=cfg["vad_silence_ms"], on_start=on_start)

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


def hands_free_listen(idle_seconds: float | None = None) -> dict:
    """Listen for one utterance during hands-free mode. Shared by the daemon
    (fast path, warm models) and the Stop hook's direct-import fallback."""
    cfg = config.load()
    max_seconds = idle_seconds if idle_seconds is not None else cfg["hands_free_idle_seconds"]

    def on_start():
        if cfg["audio_cues"]:
            audio_io.cue_listening_start()
        if cfg["notifications"]:
            audio_io.notify("Voice MCP", "Listening...")

    with config.ListenLock():
        audio, speech_detected = audio_io.record_until_silence(
            max_seconds=max_seconds, silence_ms=cfg["vad_silence_ms"], on_start=on_start
        )
    if cfg["audio_cues"]:
        audio_io.cue_listening_stop()

    if not speech_detected or audio.size == 0:
        return {"text": "", "speech_detected": speech_detected}

    text = stt.transcribe(audio, audio_io.SAMPLE_RATE, cfg["stt_backend"], cfg["language"])
    return {"text": text.strip(), "speech_detected": True}


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


def vocabulary(action: str, word: str | None = None, project_local: bool = False) -> dict:
    """Teach the STT model words it tends to mishear (app names, jargon,
    rare terms) -- fed to Whisper as a biasing prompt on every transcription."""
    if action == "list":
        return {"stt_vocabulary": config.load().get("stt_vocabulary", [])}
    if action == "add":
        if not word:
            raise ValueError("vocabulary(action='add') requires a word")
        return {"stt_vocabulary": config.add_vocabulary_word(word, project_local=project_local)}
    if action == "remove":
        if not word:
            raise ValueError("vocabulary(action='remove') requires a word")
        return {"stt_vocabulary": config.remove_vocabulary_word(word, project_local=project_local)}
    raise ValueError("action must be 'list', 'add', or 'remove'")
