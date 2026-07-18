"""Lightweight client for the in-process voice daemon (see daemon.py).

Deliberately has zero heavy imports (no mlx/mlx_audio/transformers/numpy) so
callers like the Stop hook can try the fast path without paying any import
cost, even in the fallback case where the daemon isn't reachable.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

SOCKET_PATH = Path.home() / ".claude-voice-mcp" / "daemon.sock"


def call(action: str, timeout: float = 90.0, **kwargs: Any) -> dict | None:
    """Returns the daemon's response dict, or None if it's unreachable."""
    if not SOCKET_PATH.exists():
        return None
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect(str(SOCKET_PATH))
        sock.sendall((json.dumps({"action": action, **kwargs}) + "\n").encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
        return json.loads(b"".join(chunks).decode("utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    finally:
        sock.close()


def is_daemon_running() -> bool:
    if not SOCKET_PATH.exists():
        return False
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(1.0)
        sock.connect(str(SOCKET_PATH))
        return True
    except OSError:
        return False
    finally:
        sock.close()
