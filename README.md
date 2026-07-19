# claude-voice-mcp

Bidirectional local voice for Claude Code on Apple Silicon, built on
[mlx-audio](https://github.com/Blaizzy/mlx-audio). Talk to Claude, and Claude
talks back — **automatically**, guaranteed by a Claude Code Stop hook rather
than by Claude remembering to call a `speak()` tool. Runs 100% locally and
free by default (Whisper + Kokoro), with an optional ElevenLabs backend for
more realistic voices.

**Contents:** [Two ways to use this](#two-ways-to-use-this) ·
[Commands](#commands) · [Why a Stop hook](#why-a-stop-hook-instead-of-a-speak-tool) ·
[Setup](#setup-on-a-new-machine) · [Scope](#scope-project-only-vs-available-everywhere) ·
[Configuration](#configuration) · [Architecture](#architecture)

## Two ways to use this

**Option 1 — Claude Code's native dictation + `/talkback` for replies.**
Claude Code has its own built-in push-to-talk dictation (tap `Space` in the
chat box) that types your speech into the input box — that's a separate
system from this project, not something we built. Use it for input, and run
`/talkback on` so this MCP speaks Claude's replies back via Kokoro. Our own
mic/STT pipeline (`listen`, `/talk`) is never used in this mode — only the TTS
half. Simplest option if you're happy with Claude Code's own dictation and
just want spoken replies on top of it.

**Option 2 — `/talk` for a fully local, hands-free conversation.**
`/talk` arms `hands_free` mode and starts recording through our own local
pipeline (Whisper in, Kokoro out): it records until you stop talking,
transcribes it, Claude responds, the Stop hook speaks the reply, then it
automatically starts recording again — a continuous loop with no typing and
no dictation button, until you say "stop listening", go quiet past
`hands_free_idle_seconds`, or run `/talk off`. Entirely local end-to-end.

> `/talk` only arms **listening**. If you've ever turned spoken replies off
> with `/talkback off`, `/talk` alone won't bring them back — run
> `/talkback on` too, or you'll be transcribed and continued but never hear a
> reply. Both default to on, so a fresh install gets the full experience
> automatically.

The two options mix freely — e.g. native dictation most of the time, `/talk`
when you want your hands off the keyboard.

## Commands

| Command | Does |
|---|---|
| `/talk` | Toggles `hands_free` (arms it and starts listening if off; disarms if on) |
| `/talk on` | Arms `hands_free` and starts listening, regardless of current state |
| `/talk off` | Disarms `hands_free`, regardless of current state — the quick way back after it auto-disarms |
| `/talk <seconds>` | One-shot timed recording; doesn't touch `hands_free` either way |
| `/talkback` | Toggles `auto_speak` (spoken replies) on/off |
| `/talkback on` / `off` | Sets `auto_speak` explicitly |
| `/talkback full` | Speaks the entire reply, no truncation |
| `/talkback brief` | Speaks a short summary only, truncated to `brief_max_chars` (default, 320 chars) |
| `/voice` | Lists all 54 voices, grouped by language |
| `/voice <id>` | Switches to that voice (e.g. `/voice af_bella`) |

Say "stop listening" any time to end hands-free mode by voice instead of typing `/talk off`.

## Why a Stop hook instead of a `speak()` tool?

Tool-call-based auto-speak (the common approach) only works if the model
chooses to call the tool after every reply — it can forget, get distracted,
or skip it under load. This project instead wires a **Stop hook**
(`hooks/speak_on_stop.py`) that Claude Code invokes after *every* turn,
independent of the MCP server and independent of Claude's cooperation. It
reads Claude's own final message for the turn, strips code/markdown/paths,
and speaks it (a short summary by default, or the whole thing with
`/talkback full`). Everything about this is tunable live via the
`voice_config` MCP tool or a config file, no restart required.

The same hook is also what makes hands-free mode work: when armed, it listens
again after speaking and feeds what you say back in via its `decision:
"block"` output, so Claude Code continues the conversation without you
retyping anything.

## Other capabilities

- **`stop_speaking()`** — barge-in: interrupt playback mid-sentence.
- **`list_voices()`** — same as `/voice`, callable directly.
- **`voice_config()`** — get/set any setting live from Claude's console (see
  [Configuration](#configuration)), persisted to
  `~/.claude-voice-mcp/config.json` (or a project-local `.voice-mcp.json`).
- **Hallucination guard** (`stt_guard.py`) — Whisper occasionally hallucinates
  a repeating phrase from silence/noise (a known failure mode). Detected and
  trimmed automatically before it reaches the conversation.
- **Warm-model daemon** — the Stop hook is a fresh process every turn; without
  this it would reload Kokoro/Whisper from scratch each time (5+ seconds).
  `server.py` keeps a background daemon with both models warm so the hook
  stays fast.
- **Optional ElevenLabs backend** for more realistic voices: set
  `ELEVENLABS_API_KEY` and `voice_config set tts_backend elevenlabs`. If the
  key is missing or a call fails for any reason, it **silently falls back**
  to local Kokoro — voice never breaks because of the cloud.

## Requirements

- Apple Silicon Mac (M1 or later), macOS
- Python 3.11+, [uv](https://docs.astral.sh/uv/)
- Working microphone and speakers
- `ffmpeg` (optional, only needed for MP3/FLAC handling)

## Setup on a new machine

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

   Installs `uv` if missing (via `~/.local/bin`), pins Python 3.12 (spaCy, one
   of Kokoro's text-processing dependencies, doesn't yet have wheels for
   newer Pythons), syncs the environment, and pre-downloads the default
   models (~2-3GB): Kokoro-82M (TTS) and Whisper large-v3-turbo (STT).

3. **Register the Stop hook** — this is what makes auto-speak and hands-free
   work. Add to `.claude/settings.json`, replacing both paths with your
   absolute clone path and `uv`'s absolute path (`which uv`):

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

   Use the **absolute path to `uv`**, not just `uv` — hooks don't necessarily
   inherit your shell's `PATH`. The 120s timeout matters: the hook speaks
   *and then listens* in hands-free mode, which can legitimately take over a
   minute — a shorter timeout silently kills it mid-listen with no error
   shown.

4. If `.claude/settings.json` didn't already exist when your Claude Code
   session started, run `/hooks` once (or restart) so the new file gets
   picked up.

5. Register the MCP server so Claude Code can see the `listen`/`speak`/etc.
   tools — see [Scope](#scope-project-only-vs-available-everywhere) below for
   project-only vs. everywhere.

## Scope: project-only vs. available everywhere

Three independent pieces, each defaulting to *this project only*, each with
an "everywhere" option:

| Piece | Default (project-only) | Make it global |
|---|---|---|
| **Voice settings** (voice, speed, auto_speak, hands_free, ...) | Already global: `~/.claude-voice-mcp/config.json` | N/A — already global. Add a `.voice-mcp.json` in a specific project's directory if you want *that project* to override something. |
| **MCP server** (the tools themselves) | This repo's `.mcp.json` — only auto-discovered when Claude Code's cwd is this directory | `claude mcp add voice --scope user -- /absolute/path/to/uv --directory /absolute/path/to/claude-voice-mcp run server.py` |
| **Slash commands** (`/talk`, `/voice`, `/talkback`) | This repo's `.claude/commands/*.md` — only available when working in this directory | Copy the three `.md` files into `~/.claude/commands/` (create it if it doesn't exist) |
| **Stop hook** (auto-speak / hands-free) | This repo's `.claude/settings.json` | Put the same `hooks.Stop` entry in `~/.claude/settings.json` instead |

For everywhere-by-default, do the "global" option for all three of MCP
server, slash commands, and Stop hook. To opt in per-project instead, add
matching `.mcp.json` + `.claude/commands/` + `.claude/settings.json` entries
to each project you want it in — e.g. for another project's `.mcp.json`:

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

## Configuration

All settings live in `~/.claude-voice-mcp/config.json` and can be changed
live via the `voice_config` MCP tool (`voice_config(action="set", key="...",
value="...")`) — no restart required.

| Key | Default | Meaning |
|---|---|---|
| `auto_speak` | `true` | Speak replies automatically via the Stop hook |
| `auto_speak_verbosity` | `"brief"` | `off` / `brief` (short summary) / `full` (whole reply) — see `/talkback full`/`brief` |
| `brief_max_chars` | `320` | Character cap for `"brief"` verbosity |
| `hands_free` | `false` | Whether the Stop hook re-listens after speaking (armed by `/talk`) |
| `hands_free_idle_seconds` | `90` | How long hands-free waits for you to start talking before giving up |
| `vad_silence_ms` | `5000` | Trailing silence needed to end a recording once you've started talking |
| `tts_backend` | `"kokoro"` | `kokoro` (local) or `elevenlabs` (cloud, needs `ELEVENLABS_API_KEY`, silently falls back to kokoro) |
| `voice` | `"af_heart"` | Kokoro voice ID — see `/voice` for the full list |
| `elevenlabs_voice_id` | `null` | Voice ID to use when `tts_backend` is `elevenlabs` |
| `speed` | `1.0` | Playback speed multiplier |
| `stt_backend` | `"whisper"` | `whisper` (default) or `voxtral` (lower-latency streaming, heavier download) |
| `language` | `"a"` | Language code (`a`=American English, `b`=British, `e`=Spanish, `f`=French, `h`=Hindi, `i`=Italian, `j`=Japanese, `p`=Brazilian Portuguese, `z`=Mandarin) |
| `audio_cues` | `true` | Chime when listening starts/stops |
| `notifications` | `true` | macOS banner notifications for listening/speaking state |

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
