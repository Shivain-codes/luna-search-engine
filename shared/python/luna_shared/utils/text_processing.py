"""Text analysis: tokenization, stopwords, Porter stemming, snippets.

Implemented without heavy NLP dependencies so it runs anywhere. The Porter
stemmer is a compact, well-known algorithm implementation.
"""

from __future__ import annotations

import html as html_lib
import re

STOPWORDS: frozenset[str] = frozenset(
    """
    a an and are as at be by for from has he in is it its of on that the to was were will with
    this these those i you your they them we our us or but not no so if then than too very can
    just about into over under again more most such only own same s t don
    """.split()
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase word tokenization."""
    return _TOKEN_RE.findall(text.lower())


class PorterStemmer:
    """Porter stemming algorithm (Martin Porter, 1980)."""

    def _cons(self, word: str, i: int) -> bool:
        ch = word[i]
        if ch in "aeiou":
            return False
        if ch == "y":
            return i == 0 or not self._cons(word, i - 1)
        return True

    def _m(self, word: str) -> int:
        n = 0
        i = 0
        length = len(word)
        while i < length and self._cons(word, i):
            i += 1
        while i < length:
            while i < length and not self._cons(word, i):
                i += 1
            if i >= length:
                break
            n += 1
            while i < length and self._cons(word, i):
                i += 1
        return n

    def _has_vowel(self, word: str) -> bool:
        return any(not self._cons(word, i) for i in range(len(word)))

    def _double_cons(self, word: str) -> bool:
        return len(word) >= 2 and word[-1] == word[-2] and self._cons(word, len(word) - 1)

    def _cvc(self, word: str) -> bool:
        if len(word) < 3:
            return False
        if self._cons(word, len(word) - 1) and not self._cons(word, len(word) - 2) and self._cons(word, len(word) - 3):
            return word[-1] not in "wxy"
        return False

    def stem(self, word: str) -> str:
        if len(word) <= 2:
            return word
        w = word
        # Step 1a
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-2]
        elif w.endswith("ss"):
            pass
        elif w.endswith("s"):
            w = w[:-1]
        # Step 1b
        if w.endswith("eed"):
            if self._m(w[:-3]) > 0:
                w = w[:-1]
        elif w.endswith("ed") and self._has_vowel(w[:-2]):
            w = w[:-2]
            w = self._post_1b(w)
        elif w.endswith("ing") and self._has_vowel(w[:-3]):
            w = w[:-3]
            w = self._post_1b(w)
        # Step 1c
        if w.endswith("y") and self._has_vowel(w[:-1]):
            w = w[:-1] + "i"
        w = self._step2(w)
        w = self._step3(w)
        w = self._step4(w)
        w = self._step5(w)
        return w

    def _post_1b(self, w: str) -> str:
        if w.endswith(("at", "bl", "iz")):
            return w + "e"
        if self._double_cons(w) and not w.endswith(("l", "s", "z")):
            return w[:-1]
        if self._m(w) == 1 and self._cvc(w):
            return w + "e"
        return w

    def _replace_suffix(self, w: str, mapping: dict[str, str], min_m: int = 0) -> str:
        for suffix, repl in mapping.items():
            if w.endswith(suffix):
                stem = w[: -len(suffix)]
                if self._m(stem) > min_m:
                    return stem + repl
                return w
        return w

    def _step2(self, w: str) -> str:
        mapping = {
            "ational": "ate", "tional": "tion", "enci": "ence", "anci": "ance",
            "izer": "ize", "abli": "able", "alli": "al", "entli": "ent",
            "eli": "e", "ousli": "ous", "ization": "ize", "ation": "ate",
            "ator": "ate", "alism": "al", "iveness": "ive", "fulness": "ful",
            "ousness": "ous", "aliti": "al", "iviti": "ive", "biliti": "ble",
        }
        return self._replace_suffix(w, mapping)

    def _step3(self, w: str) -> str:
        mapping = {
            "icate": "ic", "ative": "", "alize": "al", "iciti": "ic",
            "ical": "ic", "ful": "", "ness": "",
        }
        return self._replace_suffix(w, mapping)

    def _step4(self, w: str) -> str:
        suffixes = [
            "al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement",
            "ment", "ent", "ou", "ism", "ate", "iti", "ous", "ive", "ize",
        ]
        for suffix in suffixes:
            if w.endswith(suffix):
                stem = w[: -len(suffix)]
                if suffix == "ion":
                    if self._m(stem) > 1 and stem.endswith(("s", "t")):
                        return stem
                elif self._m(stem) > 1:
                    return stem
                return w
        if w.endswith("ion") and self._m(w[:-3]) > 1 and w[:-3].endswith(("s", "t")):
            return w[:-3]
        return w

    def _step5(self, w: str) -> str:
        if w.endswith("e"):
            stem = w[:-1]
            if self._m(stem) > 1 or (self._m(stem) == 1 and not self._cvc(stem)):
                w = stem
        if w.endswith("ll") and self._m(w) > 1:
            w = w[:-1]
        return w


_stemmer = PorterStemmer()


def stem(word: str) -> str:
    return _stemmer.stem(word)


def analyze(text: str, *, remove_stopwords: bool = True, do_stem: bool = True) -> list[str]:
    """Full analysis pipeline returning processed tokens in order."""
    tokens = tokenize(text)
    result: list[str] = []
    for token in tokens:
        if remove_stopwords and token in STOPWORDS:
            continue
        result.append(stem(token) if do_stem else token)
    return result


def analyze_positions(text: str, **kwargs) -> dict[str, list[int]]:
    """Return term -> sorted positions map for a field."""
    positions: dict[str, list[int]] = {}
    for pos, term in enumerate(analyze(text, **kwargs)):
        positions.setdefault(term, []).append(pos)
    return positions


class TextProcessor:
    """Convenience object used by services."""

    def analyze(self, text: str, **kwargs) -> list[str]:
        return analyze(text, **kwargs)

    def stem(self, word: str) -> str:
        return stem(word)

    def tokenize(self, text: str) -> list[str]:
        return tokenize(text)


_processor = TextProcessor()


def get_text_processor() -> TextProcessor:
    return _processor


def build_snippet(text: str, query_terms: list[str], max_length: int = 200) -> str:
    """Return a snippet centered on the densest match window."""
    if not text:
        return ""
    lowered = text.lower()
    terms = [t.lower() for t in query_terms if t]
    if not terms:
        return text[:max_length].strip() + ("..." if len(text) > max_length else "")
    best_pos, best_score = 0, -1
    step = max(1, max_length // 4)
    for i in range(0, max(1, len(text) - max_length + 1), step):
        window = lowered[i : i + max_length]
        score = sum(window.count(t) for t in terms)
        if score > best_score:
            best_score, best_pos = score, i
    start = max(0, best_pos)
    end = min(len(text), start + max_length)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def clean_html(raw: str) -> str:
    raw = re.sub(r"<(script|style|noscript|iframe|svg|canvas)[^>]*>.*?</\1>", " ", raw,
                 flags=re.IGNORECASE | re.DOTALL)
    raw = re.sub(r"<!--.*?-->", " ", raw, flags=re.DOTALL)
    return raw


def extract_text_from_html(raw: str) -> str:
    raw = clean_html(raw)
    raw = re.sub(r"</(div|p|h[1-6]|li|tr|br|section|article|header|footer|nav|aside)>", "\n", raw,
                 flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html_lib.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()


__all__ = [
    "PorterStemmer",
    "STOPWORDS",
    "TextProcessor",
    "analyze",
    "analyze_positions",
    "build_snippet",
    "clean_html",
    "extract_text_from_html",
    "get_text_processor",
    "stem",
    "tokenize",
]
