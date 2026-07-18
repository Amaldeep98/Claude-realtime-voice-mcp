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
    """Catches the case where the *whole* transcription is a repeat loop."""
    words = text.lower().split()
    if len(words) < min_words:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio <= max_unique_ratio


def strip_hallucinated_tail(text: str, *, min_repeats: int = 4, max_phrase_words: int = 4) -> str:
    """Catches the case where real speech is followed by a repeat-loop tail
    (e.g. a real question, then "...that's one that's one that's one...").
    Trims the repeating tail and returns the rest; returns the original text
    unchanged if no such tail is found.
    """
    words = text.split()
    n = len(words)
    cut = n
    for phrase_len in range(1, max_phrase_words + 1):
        if n < phrase_len * min_repeats:
            continue
        last_phrase = [w.lower() for w in words[n - phrase_len : n]]
        count = 1
        pos = n - phrase_len
        while pos - phrase_len >= 0 and [w.lower() for w in words[pos - phrase_len : pos]] == last_phrase:
            count += 1
            pos -= phrase_len
        if count >= min_repeats:
            cut = min(cut, pos)
    return " ".join(words[:cut]).strip()
