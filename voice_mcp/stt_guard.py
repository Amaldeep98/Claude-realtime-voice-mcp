"""Guards against STT hallucination on ambient noise/silence.

Whisper (and similar models) has a well-known failure mode: fed audio that's
mostly silence or noise, it can produce a long looping repeat of a short
phrase instead of an empty/low-confidence result. This matters here because
our VAD's energy-based fallback can flag a noise burst as "speech", which
then goes to STT and comes back as this kind of garbage -- which we do NOT
want to treat as a real utterance and feed back into the conversation.
"""
import re

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def looks_like_hallucinated_repeat(text: str, *, min_words: int = 12, max_unique_ratio: float = 0.2) -> bool:
    """Catches the case where the *whole* transcription is a repeat loop."""
    words = text.lower().split()
    if len(words) < min_words:
        return False
    unique_ratio = len(set(words)) / len(words)
    return unique_ratio <= max_unique_ratio


def _word_overlap(a: str, b: str) -> float:
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


def _strip_exact_repeat_tail(text: str, *, min_repeats: int, max_phrase_words: int) -> str:
    """Catches identical phrases repeating with no sentence punctuation
    (e.g. "...that's one that's one that's one...")."""
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


def _strip_similar_sentence_tail(text: str, *, min_repeats: int, max_sentence_words: int) -> str:
    """Catches near-duplicate short sentences repeating with minor wording
    drift (e.g. "And it stopped. And it stopped. And stopped. And stopped.")
    -- a real Whisper hallucination pattern that isn't an exact repeat."""
    sentences = [s for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    if len(sentences) < min_repeats:
        return text

    ref = sentences[-1]
    if len(ref.split()) > max_sentence_words:
        return text

    idx = len(sentences) - 1
    while idx - 1 >= 0:
        candidate = sentences[idx - 1]
        if len(candidate.split()) <= max_sentence_words and _word_overlap(candidate, ref) >= 0.5:
            idx -= 1
        else:
            break

    if len(sentences) - idx >= min_repeats:
        return " ".join(sentences[:idx]).strip()
    return text


def strip_hallucinated_tail(
    text: str, *, min_repeats: int = 4, max_phrase_words: int = 4, max_sentence_words: int = 6
) -> str:
    """Trims a hallucinated repeat-loop tail off real speech, whichever form
    it takes; returns the original text unchanged if no such tail is found.
    """
    trimmed = _strip_exact_repeat_tail(text, min_repeats=min_repeats, max_phrase_words=max_phrase_words)
    trimmed = _strip_similar_sentence_tail(trimmed, min_repeats=min_repeats, max_sentence_words=max_sentence_words)
    return trimmed
