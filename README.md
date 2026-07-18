# claude-voice-mcp

Bidirectional local voice for Claude Code on Apple Silicon, built on
[mlx-audio](https://github.com/Blaizzy/mlx-audio). Say **"listen to me"** or
run `/talk` and Claude hears you; Claude speaks its responses back
**automatically**, guaranteed by a Claude Code Stop hook rather than by
Claude remembering to call a tool.

## Why this instead of just calling a `speak()` tool?

Tool-call-based auto-speak (the common approach) only works if the model
chooses to call the tool after every reply — it can forget, get distracted,
or skip it under load. This project instead wires a **Stop hook**
(`hooks/speak_on_stop.py`) that Claude Code invokes after *every* turn,
independent of the MCP server and independent of Claude's cooperation. It
reads Claude's own final message for the turn, strips code/markdown/paths,
and speaks a short summary of what happened. Everything about this — on/off,
verbosity, voice, backend — is tunable live via the `voice_config` MCP tool
or a config file, no restart required.

## Features

- **Hands-free conversation** — `/talk on` (or just `/talk`) arms `hands_free`
  mode and starts listening; after Claude speaks, the Stop hook listens again
  automatically and feeds what you say back in as the next turn (via the
  hook's `decision: "block"` output), so you don't retype `/talk` every time.
  Say "stop listening", go quiet for `hands_free_idle_seconds` (default 90s),
  or run `/talk off` to end it explicitly -- handy after it's auto-disarmed
  and you want to re-arm it without checking current state. `/talk <seconds>`
  does a one-shot timed recording without touching hands-free at all.
- **`/talkback`** — toggles spoken replies (`auto_speak`) on/off independent of
  `/talk`'s listening toggle, e.g. for using native dictation as input with
  only our TTS for output.
- **`listen()`** — mic capture, gated by voice-activity detection (webrtcvad
  + energy fallback), stops after a configurable trailing-silence window
  (`vad_silence_ms`, default 5s, generous so mid-sentence pauses don't cut
  you off).
- **`speak()`** — local TTS via Kokoro-82M: 54 voices across 9 languages
  (American & British English, Spanish, French, Hindi, Italian, Japanese,
  Brazilian Portuguese, Mandarin).
- **`stop_speaking()`** — barge-in: interrupt playback mid-sentence.
- **`list_voices()`** / **`/voice`** — browse or switch voices.
- **`voice_config()`** — get/set every setting live from Claude's console,
  persisted to `~/.claude-voice-mcp/config.json` (or a project-local
  `.voice-mcp.json`).
- **Automatic spoken summaries** after every turn via the Stop hook (see above).
- **100% local and free by default** — Whisper large-v3-turbo for STT,
  Kokoro-82M for TTS, both open-weight models pulled once from Hugging Face.
- **Optional ElevenLabs backend** for more realistic voices: set
  `ELEVENLABS_API_KEY` and `voice_config set tts_backend elevenlabs`. If the
  key is missing or a call fails for any reason, it **silently falls back**
  to local Kokoro — voice never breaks because of the cloud.

## Requirements

- Apple Silicon Mac (M1 or later), macOS
- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Working microphone and speakers
- `ffmpeg` (optional, only needed for MP3/FLAC handling)

## Setup

```bash
./scripts/setup.sh
```

This installs `uv` if missing, syncs the environment, and pre-downloads the
default models (~2-3GB): Kokoro-82M (TTS) and Whisper large-v3-turbo (STT).

The Stop hook needs to be registered once in `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      { "type": "command", "command": "uv --project /path/to/claude-voice-mcp run python hooks/speak_on_stop.py", "timeout": 30 }
    ]
  }
}
```

## Using it in another project

Add to that project's `.mcp.json`:

```json
{
  "mcpServers": {
    "voice": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/claude-voice-mcp", "run", "server.py"]
    }
  }
}
```

Then say "listen to me", or use `/talk` and `/voice`.

## Configuration

All settings live in `~/.claude-voice-mcp/config.json` (see
`voice_mcp/config.py` for the full schema/defaults) and can be changed live
via the `voice_config` MCP tool, e.g.:

- `voice_config(action="set", key="auto_speak", value="false")` — disable auto-speak entirely
- `voice_config(action="set", key="auto_speak_verbosity", value="full")` — speak the whole reply, not just a brief summary
- `voice_config(action="set", key="tts_backend", value="elevenlabs")` — use ElevenLabs when `ELEVENLABS_API_KEY` is set
- `voice_config(action="set", key="stt_backend", value="voxtral")` — switch to Voxtral Realtime for lower-latency streaming STT

## Swapping models

- STT: `whisper` (default) or `voxtral` (Voxtral Realtime, matches the lower-latency streaming feel of similar projects, heavier download).
- TTS: `kokoro` (default, local) or `elevenlabs` (cloud, optional, silent fallback to kokoro).

## Architecture

```
voice_mcp/
  config.py        # shared config, read by both the MCP server and the standalone hook
  audio_io.py       # mic capture + VAD, playback, cue tones, macOS notifications
  sanitize.py       # strip markdown/code/urls/paths before any TTS call
  summarizer.py     # turn a raw assistant turn into a short spoken summary
  stt/              # whisper_backend.py (default), voxtral_backend.py (opt-in)
  tts/              # kokoro_backend.py (default), elevenlabs_backend.py (optional)
  tools.py          # tool implementations shared by server.py and the hook
server.py           # FastMCP entrypoint: listen, speak, stop_speaking, list_voices, voice_config
hooks/speak_on_stop.py  # Stop hook: guaranteed auto-speak, independent of the MCP server
```
