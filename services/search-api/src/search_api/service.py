"""Search pipeline: retrieval, ranking, filtering, snippets, pagination."""

from __future__ import annotations

import uuid

import httpx
from luna_shared.ir.bm25 import BM25Config, BM25Scorer
from luna_shared.ir.query import ParsedQuery, parse_query
from luna_shared.ir.scoring import ScoringConfig, combine_score, freshness_score
from luna_shared.ir.embeddings import EmbeddingService
from luna_shared.ir.spellchecker import SpellChecker
from luna_shared.models import Document
from luna_shared.repositories import (
    DocumentRepository,
    IndexRepository,
    TermStatsRepository,
    SemanticSearchRepository,
)
from luna_shared.cache import get_cache


# ... existing imports ...

from luna_shared.utils.text_processing import build_snippet
from sqlalchemy.ext.asyncio import AsyncSession
from .ai_service import AIService

class SearchService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        ranker_url: str | None = None,
        bm25_config: BM25Config | None = None,
        scoring_config: ScoringConfig | None = None,
        ai_api_key: str | None = None,
    ) -> None:
        self.session = session
        self.ranker_url = ranker_url
        self.bm25_config = bm25_config or BM25Config()
        self.scoring_config = scoring_config or ScoringConfig()
        self.docs = DocumentRepository(session)
        self.index = IndexRepository(session)
        self.terms = TermStatsRepository(session)
        self.semantic = SemanticSearchRepository(session)
        self.embedder = EmbeddingService()
        self.ai = AIService(api_key=ai_api_key)
        self.spellchecker = SpellChecker(self.index)


    def _passes_filters(self, doc: Document, parsed: ParsedQuery) -> bool:
        filters = parsed.filters
        if "site" in filters and filters["site"].lower() not in doc.url.lower():
            return False
        if "inurl" in filters and filters["inurl"].lower() not in doc.url.lower():
            return False
        if "intitle" in filters and filters["intitle"].lower() not in (doc.title or "").lower():
            return False
        if parsed.excluded_terms:
            body = doc.body_text.lower()
            for term in parsed.excluded:
                if term.lower() in body:
                    return False
        return True

    async def _score_local(
        self,
        terms: list[str],
        doc_frequencies: dict[str, int],
        postings_by_doc: dict[uuid.UUID, dict[str, dict[str, int]]],
        field_lengths: dict[uuid.UUID, dict[str, int]],
        documents: dict[uuid.UUID, Document],
        num_docs: int,
    ) -> dict[uuid.UUID, float]:
        scorer = BM25Scorer(self.bm25_config, num_docs=max(1, num_docs))
        scores: dict[uuid.UUID, float] = {}
        for doc_id, postings in postings_by_doc.items():
            doc = documents.get(doc_id)
            if doc is None:
                continue
            bm25 = scorer.score_document(
                terms,
                doc_frequencies=doc_frequencies,
                postings=postings,
                field_lengths=field_lengths.get(doc_id, {}),
            )
            fresh = freshness_score(doc.crawled_at, self.scoring_config.freshness_half_life_days)
            scores[doc_id] = combine_score(
                self.scoring_config, bm25=bm25, semantic=0.0, pagerank=doc.pagerank, freshness=fresh
            )
        return scores

    async def _score_via_ranker(
        self,
        terms: list[str],
        doc_frequencies: dict[str, int],
        postings_by_doc: dict[uuid.UUID, dict[str, dict[str, int]]],
        field_lengths: dict[uuid.UUID, dict[str, int]],
        documents: dict[uuid.UUID, Document],
        num_docs: int,
        query: str,
    ) -> dict[uuid.UUID, float] | None:
        if not self.ranker_url:
            return None

        # Get semantic scores for all candidates
        query_vec = self.embedder.embed(query)
        semantic_scores = await self.semantic.search(query_vec, top_k=len(postings_by_doc))
        semantic_map = {uuid.UUID(doc_id): score for doc_id, score in semantic_scores}

        candidates = []
        for doc_id, postings in postings_by_doc.items():
            doc = documents.get(doc_id)
            if doc is None:
                continue
            candidates.append(
                {
                    "document_id": str(doc_id),
                    "postings": postings,
                    "field_lengths": field_lengths.get(doc_id, {}),
                    "pagerank": doc.pagerank,
                    "crawled_at": doc.crawled_at.isoformat() if doc.crawled_at else None,
                    "semantic_score": semantic_map.get(doc_id, 0.0),
                }
            )
        payload = {
            "terms": terms,
            "doc_frequencies": doc_frequencies,
            "num_docs": num_docs,
            "candidates": candidates,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{self.ranker_url}/api/v1/rank/score", json=payload)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None
        return {uuid.UUID(r["document_id"]): r["score"] for r in data.get("results", [])}

    async def search(
        self, query: str, page: int, per_page: int, extra_filters: dict | None = None
    ) -> dict:
        parsed = parse_query(query)
        if extra_filters:
            parsed.filters.update({k: v for k, v in extra_filters.items() if v})

        # Spell Correction
        corrected_query = None
        if not parsed.is_empty:
            # Try to correct the first term if it's likely misspelled
            first_term = parsed.terms[0] if parsed.terms else None
            if first_term:
                suggestion = await self.spellchecker.suggest(first_term)
                if suggestion:
                    corrected_query = suggestion
                    # Update parsed query with corrected term
                    parsed.terms[0] = suggestion
                    parsed.normalized = parsed.normalized.replace(first_term, suggestion, 1)

        num_docs = await self.docs.count()


        empty = {
            "query": query,
            "normalized_query": parsed.normalized,
            "corrected_query": None,
            "results": [],
            "total_results": 0,
            "page": page,
            "per_page": per_page,
            "total_pages": 0,
            "answer": None,
        }
        if parsed.is_empty or num_docs == 0:
            return empty

        terms = parsed.terms
        doc_frequencies = await self.terms.doc_frequencies(terms)
        postings_by_doc = await self.index.postings_for_terms(terms)
        if not postings_by_doc:
            return empty

        doc_ids = list(postings_by_doc.keys())
        documents = await self.docs.get_many(doc_ids)
        field_lengths = await self.index.document_field_lengths(doc_ids)

        # Filter first (cheaper than scoring everything we will drop)
        filtered = {
            did: p
            for did, p in postings_by_doc.items()
            if did in documents and self._passes_filters(documents[did], parsed)
        }
        if not filtered:
            return {**empty, "total_results": 0}

        scores = await self._score_via_ranker(
            terms, doc_frequencies, filtered, field_lengths, documents, num_docs, query=query
        )
        if scores is None:
            scores = await self._score_local(
                terms, doc_frequencies, filtered, field_lengths, documents, num_docs
            )

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        total = len(ranked)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        page_slice = ranked[start : start + per_page]

        results = []
        for doc_id, score in page_slice:
            doc = documents[doc_id]
            snippet = build_snippet(doc.body_text, [t for t in parsed.required] + parsed.phrases)
            results.append(
                {
                    "id": str(doc_id),
                    "url": doc.url,
                    "title": doc.title,
                    "snippet": snippet,
                    "score": round(score, 6),
                    "pagerank": round(doc.pagerank, 6),
                    "crawled_at": doc.crawled_at.isoformat() if doc.crawled_at else "",
                }
            )

        # RAG: Generate AI answer based on top results
        answer = await self.ai.generate_answer(query, results)

        # Real-time Analytics: Publish search event
        try:
            cache = get_cache()
            event = {
                "query": query,
                "results_count": total,
                "latency_ms": 0.0, # Simplified for now
            }
            import json
            await cache.publish("analytics:search_events", json.dumps(event))
        except Exception:
            pass # Analytics should never crash the search

        return {
            "query": query,
            "normalized_query": parsed.normalized,
            "corrected_query": corrected_query,
            "results": results,
            "total_results": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "answer": answer,
        }


    async def suggest(self, prefix: str, limit: int) -> list[dict]:
        """Suggestions from query logs and document titles."""
        from luna_shared.models import QueryLog
        from sqlalchemy import distinct, select

        prefix_lower = prefix.lower()
        suggestions: list[dict] = []
        seen: set[str] = set()

        result = await self.session.execute(
            select(distinct(QueryLog.normalized_query))
            .where(QueryLog.normalized_query.like(f"{prefix_lower}%"))
            .limit(limit)
        )
        for (text,) in result.all():
            if text and text not in seen:
                seen.add(text)
                suggestions.append({"text": text, "type": "query"})

        if len(suggestions) < limit:
            title_result = await self.session.execute(
                select(Document.title)
                .where(Document.title.isnot(None))
                .order_by(Document.pagerank.desc())
                .limit(limit * 3)
            )
            for (title,) in title_result.all():
                if not title:
                    continue
                if prefix_lower in title.lower() and title not in seen:
                    seen.add(title)
                    suggestions.append({"text": title, "type": "title"})
                if len(suggestions) >= limit:
                    break

        suggestions.sort(key=lambda s: (s["type"] != "query", s["text"]))
        return suggestions[:limit]

    __all__ = ["SearchService"]
