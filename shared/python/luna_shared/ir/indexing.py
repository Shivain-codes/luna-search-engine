"""Build positional postings for a document from its fields."""

from __future__ import annotations

from urllib.parse import urlparse

from luna_shared.ir.extraction import ExtractedPage
from luna_shared.utils.text_processing import analyze

#: Fields that are analyzed and indexed, in priority order.
INDEXED_FIELDS = ("title", "heading", "body", "meta_description", "url")


def _field_texts(page: ExtractedPage) -> dict[str, str]:
    headings = " ".join(v for values in page.headings.values() for v in values)
    parsed = urlparse(page.url)
    url_text = f"{parsed.netloc} {parsed.path}".replace("/", " ").replace("-", " ").replace("_", " ")
    return {
        "title": page.title or "",
        "heading": headings,
        "body": page.body_text,
        "meta_description": page.meta_description or "",
        "url": url_text,
    }


def build_postings(page: ExtractedPage) -> list[dict]:
    """Return postings ``[{term, field, frequency, positions}]`` for a page.

    Positions are token offsets within the field, enabling phrase and
    proximity matching later.
    """
    postings: list[dict] = []
    for field in INDEXED_FIELDS:
        text = _field_texts(page).get(field, "")
        if not text:
            continue
        positions: dict[str, list[int]] = {}
        for pos, term in enumerate(analyze(text)):
            positions.setdefault(term, []).append(pos)
        for term, term_positions in positions.items():
            postings.append(
                {
                    "term": term,
                    "field": field,
                    "frequency": len(term_positions),
                    "positions": term_positions,
                    "tf_idf": 0.0,
                }
            )
    return postings


def distinct_terms(postings: list[dict]) -> set[str]:
    return {p["term"] for p in postings}


__all__ = ["INDEXED_FIELDS", "build_postings", "distinct_terms"]
