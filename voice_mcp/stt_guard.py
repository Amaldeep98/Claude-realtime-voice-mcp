"""Guards against STT hallucination on ambient noise/silence.

Whisper (and similar models) has a well-known failure mode: fed audio that's
mostly silence or noise, it can produce a long looping repeat of a short
phrase instead of an empty/low-confidence result. This matters here because
our VAD's energy-based fallback can flag a noise burst as "speech", which
then goes to STT and comes back as this kind of garbage -- which we do NOT
want to treat as a real utterance and feed back into the conversation.
"""
from __future__ import annotations


def looks_like_hallucinated_repeat(text: str, *, min_words: int = 12, max_unique_ratio: float = 0.2) -> bool:
    words = text.lower().split()
    if len(words) < min_words:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio <= max_unique_ratio
