"""Ranker service: BM25 candidate scoring and PageRank computation."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from luna_shared.app import create_app
from luna_shared.database import close_db, db, init_db
from luna_shared.ir.bm25 import BM25Scorer
from luna_shared.ir.pagerank import compute_pagerank
from luna_shared.ir.scoring import ScoringConfig, combine_score, freshness_score
from luna_shared.repositories import DocumentRepository, IndexRepository, TermStatsRepository
from pydantic import BaseModel, Field

from ranker.config import get_bm25_config, get_scoring_config, get_settings

settings = get_settings()


class RankCandidate(BaseModel):
    document_id: str
    postings: dict[str, dict[str, int]] = Field(default_factory=dict)
    field_lengths: dict[str, int] = Field(default_factory=dict)
    pagerank: float = 0.0
    crawled_at: str | None = None
    phrase_match: bool = False
    semantic_score: float = 0.0


class RankRequest(BaseModel):
    terms: list[str]
    doc_frequencies: dict[str, int]
    num_docs: int
    candidates: list[RankCandidate]


class RankedDocument(BaseModel):
    document_id: str
    score: float
    bm25: float
    semantic: float


class RankResponse(BaseModel):
    results: list[RankedDocument]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await init_db()
    yield
    await close_db()


app, health = create_app(settings, title="Luna Ranker", lifespan=lifespan)
health.register("postgres", db.ping)


@app.post("/api/v1/rank/score", response_model=RankResponse)
async def rank(request: RankRequest) -> RankResponse:
    """Score candidate documents with field-aware BM25 + PageRank + freshness."""
    from datetime import datetime

    bm25_config = get_bm25_config()
    scoring: ScoringConfig = get_scoring_config()
    scorer = BM25Scorer(bm25_config, num_docs=max(1, request.num_docs))

    results: list[RankedDocument] = []
    for cand in request.candidates:
        bm25 = scorer.score_document(
            request.terms,
            doc_frequencies=request.doc_frequencies,
            postings=cand.postings,
            field_lengths=cand.field_lengths,
        )
        crawled = None
        if cand.crawled_at:
            try:
                crawled = datetime.fromisoformat(cand.crawled_at)
            except ValueError:
                crawled = None
        fresh = freshness_score(crawled, scoring.freshness_half_life_days)
        final = combine_score(
            scoring,
            bm25=bm25,
            semantic=cand.semantic_score,
            pagerank=cand.pagerank,
            freshness=fresh,
            phrase_match=cand.phrase_match,
        )
        results.append(RankedDocument(document_id=cand.document_id, score=final, bm25=bm25, semantic=cand.semantic_score))

    results.sort(key=lambda r: r.score, reverse=True)
    return RankResponse(results=results)


@app.post("/api/v1/rank/pagerank")
async def recompute_pagerank() -> dict:
    """Recompute PageRank over the full document link graph and persist it."""
    async with db.session() as session:
        docs = DocumentRepository(session)
        links = await docs.all_links()
        nodes = [url for url, _ in links]
        edges = [(url, out) for url, outs in links for out in outs]
        scores = compute_pagerank(
            nodes,
            edges,
            damping=settings.pagerank_damping,
            max_iterations=settings.pagerank_iterations,
            tolerance=settings.pagerank_tolerance,
        )
        updated = await docs.set_pagerank(scores)
    return {"nodes": len(nodes), "edges": len(edges), "updated": updated}


@app.get("/api/v1/rank/stats")
async def stats() -> dict:
    async with db.session() as session:
        docs = DocumentRepository(session)
        idx = IndexRepository(session)
        terms = TermStatsRepository(session)
        return {
            "documents": await docs.count(),
            "postings": await idx.posting_count(),
            "terms": await terms.count(),
        }


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
