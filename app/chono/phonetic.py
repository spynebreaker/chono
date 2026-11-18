"""Spanish-aware text normalization for surname search.

Two keys are produced for every word:

* ``fold``: lowercase, accents removed (Núñez -> nunez, Güemes -> guemes).
* ``phon``: a phonetic key that merges spellings that sound alike in
  Latin American Spanish and the usual OCR/clerk variations found in old
  civil records (Villacrés / Billacres / Villacrez -> bilakres).

The rules are deliberately simple and documented so they can be tuned
against real records later.
"""

from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def fold(text: str) -> str:
    """Lowercase and strip diacritics (keeps ñ as n)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def words(text: str) -> list[str]:
    """Split text into words (letters only)."""
    return _WORD.findall(text)


def phon(word: str) -> str:
    """Phonetic key for one Spanish word."""
    w = fold(word)
    if not w:
        return ""
    # multi-letter groups first
    w = w.replace("qu", "k").replace("gue", "Ge").replace("gui", "Gi")  # hard g
    w = re.sub(r"c([ei])", r"s\1", w)  # ce, ci -> se, si
    w = re.sub(r"g([ei])", r"j\1", w)  # ge, gi -> je, ji
    w = w.replace("G", "g")
    w = re.sub(r"^y(?=[^aeiou])", "i", w)  # Yñiguez -> iñiguez
    w = re.sub(r"y$", "i", w)  # final y sounds like i
    w = w.replace("ch", "x")  # keep ch distinct from c/k
    w = w.replace("ll", "y")
    w = w.replace("ph", "f")
    w = w.replace("c", "k").replace("z", "s").replace("v", "b").replace("w", "b")
    w = w.replace("h", "")  # silent h (ch was already turned into x)
    w = re.sub(r"i(?=[aeiou])", "y", w)  # i before vowel sounds like y
    w = re.sub(r"(.)\1+", r"\1", w)  # collapse doubles (rr, ss, nn)
    return w


def keys(text: str) -> tuple[str, str]:
    """Return (folded text, phonetic text) for indexing a page."""
    ws = words(text)
    return " ".join(fold(w) for w in ws), " ".join(phon(w) for w in ws)


def edit_distance(a: str, b: str, limit: int = 2) -> int:
    """Levenshtein distance, stopping early once it exceeds ``limit``."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        best = i
        for j, cb in enumerate(b, 1):
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            cur.append(v)
            best = min(best, v)
        if best > limit:
            return limit + 1
        prev = cur
    return prev[-1]
