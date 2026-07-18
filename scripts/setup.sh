#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -m)" != "arm64" || "$(uname -s)" != "Darwin" ]]; then
  echo "claude-voice-mcp requires Apple Silicon macOS (mlx-audio needs MLX)." >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Warning: ffmpeg not found. Install it (e.g. 'brew install ffmpeg') for MP3/FLAC support." >&2
fi

cd "$(dirname "$0")/.."
echo "Syncing Python environment..."
uv sync

echo "Pre-downloading local models (Kokoro TTS + Whisper STT, ~2-3GB)..."
uv run scripts/warmup.py

echo
echo "Setup complete. Add this to a project's .mcp.json to use it there:"
echo '  "voice": {"type": "stdio", "command": "uv", "args": ["--directory", "'"$(pwd)"'", "run", "server.py"]}'
