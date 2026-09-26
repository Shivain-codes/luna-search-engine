"""Field-aware BM25 scoring.

The score for a document is the sum over query terms of the per-field
BM25 contribution weighted by the configured field weight:

    score = Σ_field weight_field · Σ_term IDF(term) · tf'·(k1+1) / (tf' + k1·(1 - b + b·|D_field|/avgdl_field))

where ``tf'`` is the term frequency of the term in that field of the
document. IDF uses the standard BM25 formulation with +0.5 smoothing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def idf(num_docs: int, doc_frequency: int) -> float:
    """BM25 inverse document frequency (never negative)."""
    if num_docs <= 0:
        return 0.0
    return max(0.0, math.log((num_docs - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1.0))


DEFAULT_FIELD_WEIGHTS = {
    "title": 3.0,
    "heading": 2.0,
    "body": 1.0,
    "anchor": 1.5,
    "meta_description": 1.2,
    "url": 0.8,
}

DEFAULT_AVG_FIELD_LENGTH = {
    "title": 8.0,
    "heading": 12.0,
    "body": 500.0,
    "anchor": 6.0,
    "meta_description": 25.0,
    "url": 4.0,
}


@dataclass
class BM25Config:
    k1: float = 1.5
    b: float = 0.75
    field_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_FIELD_WEIGHTS))
    avg_field_length: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_AVG_FIELD_LENGTH)
    )

    @classmethod
    def from_ranking_yaml(cls, data: dict) -> BM25Config:
        ranking = data.get("ranking", data)
        bm25 = ranking.get("bm25", {})
        weights = ranking.get("field_weights", {})
        avg = ranking.get("field_length_norm", {}).get("avg_field_length", {})
        return cls(
            k1=float(bm25.get("k1", 1.5)),
            b=float(bm25.get("b", 0.75)),
            field_weights={**DEFAULT_FIELD_WEIGHTS, **{k: float(v) for k, v in weights.items()}},
            avg_field_length={
                **DEFAULT_AVG_FIELD_LENGTH,
                **{k: float(v) for k, v in avg.items()},
            },
        )


class BM25Scorer:
    """Computes field-aware BM25 given precomputed term statistics."""

    def __init__(self, config: BM25Config, num_docs: int) -> None:
        self.config = config
        self.num_docs = num_docs

    def term_score(
        self,
        *,
        doc_frequency: int,
        term_frequency: int,
        field: str,
        field_length: int,
    ) -> float:
        """BM25 contribution of one term occurring in one field."""
        if term_frequency <= 0:
            return 0.0
        weight = self.config.field_weights.get(field, 1.0)
        avgdl = self.config.avg_field_length.get(field, 500.0) or 1.0
        k1, b = self.config.k1, self.config.b
        term_idf = idf(self.num_docs, doc_frequency)
        norm = 1.0 - b + b * (field_length / avgdl)
        tf_component = (term_frequency * (k1 + 1.0)) / (term_frequency + k1 * norm)
        return weight * term_idf * tf_component

    def score_document(
        self,
        query_terms: list[str],
        *,
        doc_frequencies: dict[str, int],
        postings: dict[str, dict[str, int]],
        field_lengths: dict[str, int],
    ) -> float:
        """Score a single document.

        ``postings`` maps term -> {field: term_frequency}.
        ``field_lengths`` maps field -> length in tokens.
        """
        total = 0.0
        for term in set(query_terms):
            fields = postings.get(term)
            if not fields:
                continue
            df = doc_frequencies.get(term, 0)
            for field_name, tf in fields.items():
                total += self.term_score(
                    doc_frequency=df,
                    term_frequency=tf,
                    field=field_name,
                    field_length=field_lengths.get(field_name, 0),
                )
        return total


__all__ = [
    "BM25Config",
    "BM25Scorer",
    "DEFAULT_AVG_FIELD_LENGTH",
    "DEFAULT_FIELD_WEIGHTS",
    "idf",
]
