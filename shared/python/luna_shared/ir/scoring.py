"""Combined relevance scoring: BM25 + PageRank + freshness."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class ScoringConfig:
    bm25_weight: float = 0.6
    semantic_weight: float = 0.2
    pagerank_weight: float = 0.1
    freshness_weight: float = 0.1
    freshness_half_life_days: float = 365.0
    phrase_boost: float = 1.5
    prefix_boost: float = 1.2
    field_weights: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_ranking_yaml(cls, data: dict) -> ScoringConfig:
        ranking = data.get("ranking", data)
        scoring = ranking.get("scoring", {})
        return cls(
            bm25_weight=float(scoring.get("bm25_weight", 0.6)),
            semantic_weight=float(scoring.get("semantic_weight", 0.2)),
            pagerank_weight=float(scoring.get("pagerank_weight", 0.1)),
            freshness_weight=float(scoring.get("freshness_weight", 0.1)),
            freshness_half_life_days=float(scoring.get("freshness_half_life_days", 365.0)),
            phrase_boost=float(scoring.get("phrase_boost", 1.5)),
            prefix_boost=float(scoring.get("prefix_boost", 1.2)),
        )


def freshness_score(crawled_at: datetime | None, half_life_days: float) -> float:
    """Exponential decay in [0, 1] based on document age."""
    if crawled_at is None or half_life_days <= 0:
        return 0.0
    now = datetime.now(UTC)
    if crawled_at.tzinfo is None:
        crawled_at = crawled_at.replace(tzinfo=UTC)
    age_days = max(0.0, (now - crawled_at).total_seconds() / 86400.0)
    return math.pow(0.5, age_days / half_life_days)


def combine_score(
    config: ScoringConfig,
    *,
    bm25: float,
    semantic: float,
    pagerank: float,
    freshness: float,
    phrase_match: bool = False,
    prefix_match: bool = False,
) -> float:
    """Weighted combination of relevance signals.

    Implemented as a linear combination of scores, allowing
    weights to be tuned via ScoringConfig (from ranking.yaml).
    """
    score = (
        config.bm25_weight * bm25
        + config.semantic_weight * semantic
        + config.pagerank_weight * pagerank
        + config.freshness_weight * freshness
    )
    if phrase_match:
        score *= config.phrase_boost
    if prefix_match:
        score *= config.prefix_boost
    return score



def reciprocal_rank_fusion(
    rankings: list[list[str]], k: float = 60.0
) -> dict[str, float]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion (RRF).

    rankings: A list of ranked document IDs (one list per ranking method).
    """
    scores: dict[str, float] = {}
    for rank_list in rankings:
        for rank, doc_id in enumerate(rank_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))
    return scores

__all__ = ["ScoringConfig", "combine_score", "freshness_score", "reciprocal_rank_fusion"]
