"""Turn a raw assistant turn into something short worth speaking aloud.

No extra LLM call: Claude Code's own end-of-turn style is already supposed to
be a terse "what changed and what's next" (see the project's own guidance on
end-of-turn summaries), so for "brief" verbosity this is mostly cleanup +
truncation, not rewriting. "full" speaks the whole cleaned prose.
"""
from __future__ import annotations

from .sanitize import strip_for_speech

_SENTENCE_END = (". ", "! ", "? ")


def build_spoken_summary(raw_text: str, *, verbosity: str, max_chars: int) -> str:
    """Return the text to speak, or "" if there's nothing worth saying."""
    if verbosity == "off" or not raw_text or not raw_text.strip():
        return ""

    cleaned = strip_for_speech(raw_text)
    if not cleaned:
        return ""

    if verbosity == "full" or len(cleaned) <= max_chars:
        return cleaned

    # brief: keep whole sentences up to max_chars, don't cut mid-word
    truncated = cleaned[:max_chars]
    best_cut = max(
        (truncated.rfind(sep) + len(sep) for sep in _SENTENCE_END if sep in truncated),
        default=0,
    )
    if best_cut > 0:
        return truncated[:best_cut].strip()

    space_cut = truncated.rfind(" ")
    return (truncated[:space_cut] if space_cut > 0 else truncated).strip() + "..."
