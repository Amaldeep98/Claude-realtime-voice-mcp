"""Strip markdown/code/paths/urls from text so TTS reads it naturally."""
from __future__ import annotations

import re

_FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]*)`")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_BARE_URL = re.compile(r"https?://\S+")
_FILE_REF = re.compile(r"\b[\w./-]+\.\w{1,5}:\d+(-\d+)?\b")  # path/to/file.py:12-34
_BOLD_ITALIC = re.compile(r"[*_]{1,3}([^*_]+)[*_]{1,3}")
_HEADING = re.compile(r"^#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^\s*[-*]\s+", re.MULTILINE)
_MULTI_WS = re.compile(r"\s+")


def strip_for_speech(text: str) -> str:
    text = _FENCED_CODE_BLOCK.sub(" ", text)
    text = _FILE_REF.sub("", text)
    text = _MARKDOWN_LINK.sub(r"\1", text)
    text = _BARE_URL.sub("", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _BOLD_ITALIC.sub(r"\1", text)
    text = _HEADING.sub("", text)
    text = _BULLET.sub("", text)
    text = _MULTI_WS.sub(" ", text)
    return text.strip()
