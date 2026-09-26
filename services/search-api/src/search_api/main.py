"""Search API: query, suggest, and click-tracking endpoints."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from luna_shared.app import create_app
from luna_shared.cache import get_cache
from luna_shared.database import close_db, db, init_db
from luna_shared.errors import ValidationError
from luna_shared.ir.bm25 import BM25Config
from luna_shared.ir.scoring import ScoringConfig
from luna_shared.repositories import AnalyticsRepository
from pydantic import BaseModel, Field

from search_api.config import get_settings
from search_api.service import SearchService

settings = get_settings()
cache = get_cache()


class SearchResult(BaseModel):
    id: str
    url: str
    title: str | None
    snippet: str
    score: float
    pagerank: float
    crawled_at: str

class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    corrected_query: str | None = None
    results: list[SearchResult]
    total_results: int
    page: int
    per_page: int
    total_pages: int
    search_time_ms: float
    cache_hit: bool
    query_context: str | None = None
    answer: str | None = None

class Suggestion(BaseModel):
    text: str
    type: str

class SuggestResponse(BaseModel):
    query: str
    suggestions: list[Suggestion]

class ClickRequest(BaseModel):
    query_context: str
    document_id: str
    position: int = Field(ge=0)
    dwell_time_ms: int | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await init_db()
    await cache.connect()
    yield
    await cache.close()
    await close_db()

app, health = create_app(settings, title="Luna Search API", lifespan=lifespan)
health.register("postgres", db.ping)
health.register("redis", cache.ping)

def _service(session) -> SearchService:
    return SearchService(
        session,
        ranker_url=settings.ranker_url,
        bm25_config=BM25Config(k1=settings.bm25_k1, b=settings.bm25_b),
        scoring_config=ScoringConfig(),
        ai_api_key=settings.nemotron_api_key,
    )

@app.get("/api/v1/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    page: int = Query(1, ge=1),
    per_page: int = Query(default=settings.search_default_per_page, ge=1, le=settings.search_max_per_page),
    site: str | None = Query(None),
    language: str | None = Query(None),
    safe_search: bool = Query(True),
    date_range: str | None = Query(None),
) -> SearchResponse:
    start = time.perf_counter()
    cache_key = f"search:{q}:{page}:{per_page}:{site}:{language}:{safe_search}:{date_range}"

    cached = await cache.get_json(cache_key)
    if cached:
        cached["cache_hit"] = True
        cached["search_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
        return SearchResponse(**cached)

    async with db.session() as session:
        result = await _service(session).search(
            q, page, per_page, extra_filters={"site": site}
        )

    elapsed = round((time.perf_counter() - start) * 1000, 2)

    query_context = None
    async with db.session() as session:
        analytics = AnalyticsRepository(session)
        log = await analytics.log_query(
            query=q,
            normalized_query=result["normalized_query"],
            results_count=result["total_results"],
            page=page,
            per_page=per_page,
            search_time_ms=elapsed,
            cache_hit=False,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            filters={"site": site, "language": language} if site or language else {},
        )
        query_context = str(log.id)

    response = SearchResponse(
        **result, search_time_ms=elapsed, cache_hit=False, query_context=query_context
    )
    if result["total_results"] > 0:
        payload = response.model_dump()
        payload.pop("query_context", None)
        await cache.set_json(cache_key, payload, ttl=settings.search_cache_ttl)
    return response

@app.get("/api/v1/suggest", response_model=SuggestResponse)
async def suggest(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=settings.suggest_max_limit),
) -> SuggestResponse:
    if len(q.strip()) < settings.suggest_min_length:
        return SuggestResponse(query=q, suggestions=[])
    async with db.session() as session:
        raw = await _service(session).suggest(q.strip(), limit)
    return SuggestResponse(query=q, suggestions=[Suggestion(**s) for s in raw])

@app.post("/api/v1/clicks", status_code=202)
async def track_click(payload: ClickRequest) -> dict:
    try:
        query_log_id = uuid.UUID(payload.query_context)
        document_id = uuid.UUID(payload.document_id)
    except ValueError as exc:
        raise ValidationError("Invalid identifier", details={"field": "id"}) from exc

    async with db.session() as session:
        analytics = AnalyticsRepository(session)
        query_log = await analytics.get_query_log(query_log_id)
        if query_log is None:
            raise ValidationError("Unknown query context")
        await analytics.log_click(
            query_log_id=query_log_id,
            document_id=document_id,
            position=payload.position,
            dwell_time_ms=payload.dwell_time_ms,
        )
    return {"status": "accepted"}

@app.get("/api/v1/documents/{doc_id}")
async def get_document(doc_id: str) -> dict:
    from luna_shared.errors import NotFoundError
    from luna_shared.repositories import DocumentRepository

    async with db.session() as session:
        docs = DocumentRepository(session)
        try:
            doc = await docs.get(uuid.UUID(doc_id))
        except ValueError as exc:
            raise NotFoundError("Document not found") from exc
        if not doc:
            raise NotFoundError("Document not found")
        return {
            "id": str(doc.id),
            "url": doc.url,
            "title": doc.title,
            "meta_description": doc.meta_description,
            "language": doc.language,
            "pagerank": doc.pagerank,
            "crawled_at": doc.crawled_at.isoformat() if doc.crawled_at else None,
        }

def run() -> None:
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)

if __name__ == "__main__":
    run()
