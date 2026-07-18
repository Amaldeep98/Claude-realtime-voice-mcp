"""Persistent in-process voice daemon.

Runs as a background thread inside the long-lived MCP server process
(server.py) so the Kokoro/Whisper models loaded via voice_mcp.tools stay warm
across calls. Without this, the standalone Stop hook (hooks/speak_on_stop.py)
-- a brand new Python process spawned fresh on every single turn -- would pay
the full mlx/mlx_audio model-load cost (several seconds) every time it speaks.
Talking to this socket instead reuses whatever's already loaded here.
"""
from __future__ import annotations

import json
import socket
import threading

from . import tools
from .ipc_client import SOCKET_PATH, is_daemon_running


def _handle(conn: socket.socket) -> None:
    try:
        chunks = []
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            if chunk.endswith(b"\n"):
                break
        request = json.loads(b"".join(chunks).decode("utf-8"))
        action = request.get("action")
        if action == "speak":
            result = tools.speak(request["text"], request.get("voice"), request.get("speed"), request.get("lang"))
            response = {"ok": True, "result": result}
        elif action == "listen":
            result = tools.listen(request.get("duration"))
            response = {"ok": True, "result": result}
        elif action == "hands_free_listen":
            response = {"ok": True, **tools.hands_free_listen(request.get("idle_seconds"))}
        elif action == "stop_speaking":
            response = {"ok": True, "result": tools.stop_speaking()}
        else:
            response = {"ok": False, "error": f"unknown action {action!r}"}
    except Exception as exc:
        response = {"ok": False, "error": str(exc)}
    try:
        conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
    except OSError:
        pass
    finally:
        conn.close()


def _serve_forever() -> None:
    SOCKET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    server.listen(8)
    try:
        while True:
            conn, _ = server.accept()
            threading.Thread(target=_handle, args=(conn,), daemon=True).start()
    finally:
        server.close()
        SOCKET_PATH.unlink(missing_ok=True)


def _warm_default_tts() -> None:
    try:
        from .tts import kokoro_backend

        kokoro_backend._load()
    except Exception:
        pass


def start_background() -> None:
    """No-op if another process's daemon is already serving the socket --
    e.g. a second Claude Code session using the same MCP server config. It's
    fine for them to share one daemon; the audio device and config file are
    both process-independent shared local resources anyway."""
    if is_daemon_running():
        return
    threading.Thread(target=_serve_forever, daemon=True).start()
    threading.Thread(target=_warm_default_tts, daemon=True).start()
