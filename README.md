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

## Two ways to use this

**Option 1: Claude Code's native `/voice` dictation + `/talkback` for replies.**
Claude Code has its own built-in push-to-talk dictation (tap `Space` in the
chat box) that types your speech into the input box for you -- that's a
separate system from this project, not something we built. Use it for input,
and run `/talkback on` so this MCP speaks Claude's replies back via Kokoro.
In this mode our mic/STT pipeline (`listen`, `/talk`) is never used at all --
only the TTS half. Simplest option if you're happy with Claude Code's own
dictation and just want spoken replies on top of it.

**Option 2: `/talk` for a fully local, hands-free real-time conversation.**
`/talk` (or `/talk on`) arms `hands_free` mode and starts recording through
our own local pipeline (Whisper STT in, Kokoro TTS out): it records until you
stop talking, transcribes it, Claude responds, the Stop hook speaks the reply,
then it automatically starts recording again -- a continuous back-and-forth
loop with no typing and no dictation button, until you say "stop listening",
go quiet past `hands_free_idle_seconds`, or run `/talk off`. This is the
"press play and just talk" option, entirely local end-to-end.

`/talk` only arms **listening** (`hands_free`) -- it does not turn spoken
replies on by itself. `auto_speak` (spoken replies) is on by default out of
the box, so a fresh install gets both automatically, but if you've ever
turned `auto_speak` off (via `/talkback off`), running `/talk` alone won't
bring it back -- run `/talkback on` too, or you'll hear yourself transcribed
and continued but never hear Claude's replies spoken.

You can also mix and match (e.g. native dictation most of the time, `/talk`
when you want your hands off the keyboard) -- `/talk` and `/talkback` are
independent toggles, covered in **Features** below.

## Features

- **Hands-free conversation** — `/talk on` (or just `/talk`) arms `hands_free`
  mode and starts listening; after Claude speaks, the Stop hook listens again
  automatically and feeds what you say back in as the next turn (via the
  hook's `decision: "block"` output), so you don't retype `/talk` every time.
  Say "stop listening", go quiet for `hands_free_idle_seconds` (default 90s),
  or run `/talk off` to end it explicitly -- handy after it's auto-disarmed
  and you want to re-arm it without checking current state. `/talk <seconds>`
  does a one-shot timed recording without touching hands-free at all.
- **`/talkback on` / `/talkback off`** (bare `/talkback` toggles) — controls
  spoken replies (`auto_speak`) independent of `/talk`'s listening toggle,
  e.g. for using native dictation as input with
  only our TTS for output.
- **`/talkback full` / `/talkback brief`** — how much of each reply gets
  spoken: `brief` (default) speaks a short summary truncated to
  `brief_max_chars` (320 by default); `full` speaks the whole reply. If
  replies are getting cut off mid-thought, switch to `full`.
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

## Setting up on a new machine, from scratch

1. **Clone this repo** somewhere permanent (its path gets baked into config
   below, so pick a final location, e.g. `~/tools/claude-voice-mcp`):

   ```bash
   git clone git@github.com:Amaldeep98/Claude-realtime-voice-mcp.git
   cd Claude-realtime-voice-mcp
   ```

2. **Run setup**:

   ```bash
   ./scripts/setup.sh
   ```

   This installs `uv` if missing (via `~/.local/bin`), pins Python 3.12 (spaCy,
   one of Kokoro's text-processing dependencies, doesn't yet have wheels for
   newer Pythons), syncs the environment, and pre-downloads the default models
   (~2-3GB): Kokoro-82M (TTS) and Whisper large-v3-turbo (STT).

3. **Register the Stop hook** (this is what makes auto-speak and hands-free
   work) by adding this to `.claude/settings.json` — replace both path
   occurrences with your absolute clone path and `uv`'s absolute path
   (`which uv`):

   ```json
   {
     "hooks": {
       "Stop": [
         {
           "hooks": [
             {
               "type": "command",
               "command": "/absolute/path/to/uv --project /absolute/path/to/claude-voice-mcp run python hooks/speak_on_stop.py",
               "timeout": 120
             }
           ]
         }
       ]
     }
   }
   ```

   Use the **absolute path to `uv`** (not just `uv`) since hooks don't
   necessarily inherit your shell's `PATH`. The 120s timeout matters: the hook
   speaks *and then listens* in hands-free mode, which can legitimately take
   over a minute — a shorter timeout will silently kill it mid-listen with no
   error shown (this bit us during development; see git history if curious).

4. If `.claude/settings.json` didn't already exist in that project when your
   Claude Code session started, run `/hooks` once (or restart) so the new
   file gets picked up.

5. Register the MCP server so Claude Code can see the `listen`/`speak`/etc.
   tools — see **Scope** below for project-only vs. everywhere.

## Scope: project-only vs. available everywhere

Three independent pieces, each defaulting to *this project only*, each with
an "everywhere" option:

| Piece | Default (project-only) | Make it global |
|---|---|---|
| **Voice settings** (voice, speed, auto_speak, hands_free, ...) | Already global: `~/.claude-voice-mcp/config.json` | N/A — already global. Add a `.voice-mcp.json` in a specific project's directory if you want *that project* to override something. |
| **MCP server** (the tools themselves) | This repo's `.mcp.json` — only auto-discovered when Claude Code's cwd is this directory | `claude mcp add voice --scope user -- /absolute/path/to/uv --directory /absolute/path/to/claude-voice-mcp run server.py` — registers it for every project for your user |
| **Slash commands** (`/talk`, `/voice`, `/talkback`) | This repo's `.claude/commands/*.md` — only available when working in this directory | Copy the three `.md` files into `~/.claude/commands/` instead (create the directory if it doesn't exist) |
| **Stop hook** (auto-speak / hands-free) | This repo's `.claude/settings.json` | Put the same `hooks.Stop` entry in `~/.claude/settings.json` instead |

If you want the whole thing available in every project without any
per-project setup, do the "global" option for all three of MCP server, slash
commands, and Stop hook. If you'd rather opt in per-project, keep the default
and just add `.mcp.json` + `.claude/commands/` + `.claude/settings.json`
entries (matching this repo's) to each project you want it in.

## Using it in another project (project-scoped, the default)

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

Then say "listen to me", or use `/talk` and `/voice` (copy those command
files in too, or use the global option above).

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
  stt_guard.py      # detect/trim Whisper hallucination (repeat loops) on noise/silence
  stt/              # whisper_backend.py (default), voxtral_backend.py (opt-in)
  tts/              # kokoro_backend.py (default), elevenlabs_backend.py (optional)
  tools.py          # tool implementations shared by server.py, the daemon, and the hook's fallback
  daemon.py         # background Unix-socket server (in server.py's process) keeping models warm
  ipc_client.py     # lightweight client the hook uses to reach the daemon, no heavy imports
server.py           # FastMCP entrypoint: listen, speak, stop_speaking, list_voices, voice_config;
                     # also starts the daemon in a background thread
hooks/speak_on_stop.py  # Stop hook: guaranteed auto-speak + hands-free, independent of the MCP server
                         # (talks to the daemon for speed, falls back to loading models directly)
```
