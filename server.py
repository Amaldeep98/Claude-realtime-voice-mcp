"""claude-voice-mcp: bidirectional local voice MCP server for Claude Code.

Registers listen/speak/stop_speaking/list_voices/voice_config as MCP tools.
Automatic "Claude speaks its responses" is handled separately by
hooks/speak_on_stop.py (a Claude Code Stop hook), not by this server --
see that file for why. This process also runs a background voice daemon
(voice_mcp/daemon.py) so the Stop hook can reuse already-warm models instead
of reloading them from scratch on every turn.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from voice_mcp import daemon, tools

mcp = FastMCP("claude-voice-mcp")
daemon.start_background()


@mcp.tool()
def listen(duration: float | None = None) -> str:
    """Record from the microphone and return the transcription.

    Without `duration`, records until the configured trailing silence is
    detected (voice-activity gated). With `duration` (seconds), records a
    fixed-length clip instead.
    """
    return tools.listen(duration)


@mcp.tool()
def speak(text: str, voice: str | None = None, speed: float | None = None, lang: str | None = None) -> str:
    """Speak `text` aloud through the local speakers.

    Uses the configured TTS backend (local Kokoro by default, or ElevenLabs
    if configured -- silently falls back to Kokoro if ElevenLabs is
    unavailable). `voice`/`speed`/`lang` override the persisted config for
    this call only.
    """
    return tools.speak(text, voice, speed, lang)


@mcp.tool()
def stop_speaking() -> str:
    """Interrupt any speech currently playing."""
    return tools.stop_speaking()


@mcp.tool()
def list_voices(language: str | None = None) -> list[dict]:
    """List available voices, optionally filtered by language code (a/b/e/f/h/i/j/p/z)."""
    return tools.list_voices(language)


@mcp.tool()
def voice_config(action: str, key: str | None = None, value: str | None = None, project_local: bool = False) -> dict:
    """Get or set voice-mcp settings (auto_speak, auto_speak_verbosity, tts_backend,
    voice, elevenlabs_voice_id, speed, stt_backend, language, vad_silence_ms,
    audio_cues, notifications, brief_max_chars).

    action="get" with no key returns the whole config. action="set" requires
    key and value. Pass project_local=true to persist to .voice-mcp.json in
    the current project instead of the user-level config.
    """
    return tools.voice_config(action, key, value, project_local)


@mcp.tool()
def vocabulary(action: str, word: str | None = None, project_local: bool = False) -> dict:
    """Teach the STT model words/names it tends to mishear (app names,
    jargon, rare terms), fed to Whisper as a biasing prompt on every
    transcription.

    action="add" (requires word), action="remove" (requires word), or
    action="list" to see the current vocabulary. Pass project_local=true to
    persist to .voice-mcp.json in the current project instead of the
    user-level config.
    """
    return tools.vocabulary(action, word, project_local)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
