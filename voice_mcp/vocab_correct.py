"""Post-processing fuzzy correction for taught vocabulary words.

Whisper's initial_prompt (see stt/whisper_backend.py) biases recognition
toward taught words but doesn't guarantee exact matches, especially for
made-up or unusual compound names -- e.g. "bedouapp" coming back as "bido
app". This catches near-misses by comparing normalized text similarity
between sliding windows of the transcript and each taught word, and swaps in
the exact taught spelling when they're a close enough match.
"""
from __future__ import annotations

import difflib
import re

_WORD = re.compile(r"\S+")


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def correct_vocabulary(text: str, vocabulary: list[str], *, min_ratio: float = 0.72) -> str:
    if not vocabulary or not text:
        return text

    words = list(_WORD.finditer(text))
    if not words:
        return text

    used = set()
    replacements = []  # (start_char, end_char, replacement)

    for term in vocabulary:
        target_norm = _normalize(term)
        if not target_norm:
            continue
        term_word_count = max(1, len(term.split()))
        best = None  # (ratio, start_idx, end_idx)
        for span in {term_word_count, term_word_count + 1, max(1, term_word_count - 1)}:
            for start in range(0, len(words) - span + 1):
                idx_range = range(start, start + span)
                if used & set(idx_range):
                    continue
                window_norm = _normalize(" ".join(words[i].group() for i in idx_range))
                if not window_norm:
                    continue
                ratio = difflib.SequenceMatcher(None, window_norm, target_norm).ratio()
                if ratio >= min_ratio and (best is None or ratio > best[0]):
                    best = (ratio, start, start + span)
        if best:
            _, start, end = best
            replacements.append((words[start].start(), words[end - 1].end(), term))
            used.update(range(start, end))

    if not replacements:
        return text

    replacements.sort(key=lambda r: r[0], reverse=True)
    result = text
    for start_char, end_char, term in replacements:
        result = result[:start_char] + term + result[end_char:]
    return result
