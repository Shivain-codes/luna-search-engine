"""Query parser: normalization, boolean/phrase operators, and field filters.

Supported syntax:
- ``+term``        required term
- ``-term``        excluded term
- ``"a b c"``      exact phrase
- ``site:x.com``   restrict to a domain substring
- ``intitle:x``    term must appear in the title
- ``inurl:x``      term must appear in the URL
- ``filetype:pdf`` content-type/extension filter
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from luna_shared.utils.text_processing import analyze

_PHRASE_RE = re.compile(r'"([^"]+)"')
_FIELD_OPS = ("site:", "intitle:", "inurl:", "filetype:")


def normalize_query(query: str) -> str:
    """Unicode-normalize, collapse whitespace, and lowercase."""
    query = unicodedata.normalize("NFKC", query)
    query = re.sub(r"\s+", " ", query).strip()
    return query.lower()


@dataclass
class ParsedQuery:
    original: str
    normalized: str
    required: list[str] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)

    @property
    def terms(self) -> list[str]:
        """Analyzed (stemmed) required terms plus phrase terms."""
        out: list[str] = []
        for token in self.required:
            out.extend(analyze(token))
        for phrase in self.phrases:
            out.extend(analyze(phrase))
        return out

    @property
    def excluded_terms(self) -> list[str]:
        out: list[str] = []
        for token in self.excluded:
            out.extend(analyze(token))
        return out

    @property
    def is_empty(self) -> bool:
        return not self.terms and not self.phrases


def parse_query(query: str) -> ParsedQuery:
    normalized = normalize_query(query)
    working = normalized
    phrases: list[str] = []
    for match in _PHRASE_RE.findall(working):
        phrases.append(match.strip())
    working = _PHRASE_RE.sub(" ", working)

    required: list[str] = []
    excluded: list[str] = []
    filters: dict[str, str] = {}

    for token in working.split():
        matched_field = next((op for op in _FIELD_OPS if token.startswith(op)), None)
        if matched_field:
            value = token[len(matched_field):].strip()
            if value:
                filters[matched_field.rstrip(":")] = value
        elif token.startswith("+") and len(token) > 1:
            required.append(token[1:])
        elif token.startswith("-") and len(token) > 1:
            excluded.append(token[1:])
        elif token:
            required.append(token)

    return ParsedQuery(
        original=query,
        normalized=normalized,
        required=required,
        excluded=excluded,
        phrases=phrases,
        filters=filters,
    )


__all__ = ["ParsedQuery", "normalize_query", "parse_query"]
