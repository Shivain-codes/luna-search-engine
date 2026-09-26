"""Repository for documents and the inverted index."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from luna_shared.ir.sharding import get_shard_id
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from luna_shared.models import Document, InvertedIndex, TermStats


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Document))
        return int(result.scalar_one())

    async def get(self, doc_id: uuid.UUID) -> Document | None:
        return await self.session.get(Document, doc_id)

    async def get_by_url(self, normalized_url: str) -> Document | None:
        result = await self.session.execute(
            select(Document).where(Document.url == normalized_url)
        )
        return result.scalar_one_or_none()

    async def get_many(self, ids: list[uuid.UUID]) -> dict[uuid.UUID, Document]:
        if not ids:
            return {}
        result = await self.session.execute(select(Document).where(Document.id.in_(ids)))
        return {d.id: d for d in result.scalars().all()}

    async def upsert(
        self,
        *,
        url: str,
        canonical_url: str,
        content_hash: str,
        title: str | None,
        meta_description: str | None,
        headings: dict,
        body_text: str,
        language: str,
        outlinks: list[str],
        crawl_id: uuid.UUID | None,
        status_code: int = 200,
    ) -> tuple[Document, bool]:
        """Insert or update a document by URL. Returns ``(doc, created)``."""
        existing = await self.get_by_url(url)
        now = datetime.now(UTC)
        if existing is None:
            doc = Document(
                url=url,
                canonical_url=canonical_url,
                content_hash=content_hash,
                title=title,
                meta_description=meta_description,
                headings=headings,
                body_text=body_text,
                language=language,
                content_length=len(body_text),
                outlinks=outlinks,
                status_code=status_code,
                crawled_at=now,
                crawl_id=crawl_id,
            )
            self.session.add(doc)
            await self.session.flush()
            return doc, True

        existing.canonical_url = canonical_url
        existing.content_hash = content_hash
        existing.title = title
        existing.meta_description = meta_description
        existing.headings = headings
        existing.body_text = body_text
        existing.language = language
        existing.content_length = len(body_text)
        existing.outlinks = outlinks
        existing.status_code = status_code
        existing.crawled_at = now
        if crawl_id:
            existing.crawl_id = crawl_id
        await self.session.flush()
        return existing, False

    async def all_links(self) -> list[tuple[str, list[str]]]:
        """Return ``(url, outlinks)`` pairs for PageRank computation."""
        result = await self.session.execute(select(Document.url, Document.outlinks))
        return [(row[0], row[1] or []) for row in result.all()]

    async def set_pagerank(self, url_to_score: dict[str, float]) -> int:
        """Persist PageRank scores keyed by document URL."""
        updated = 0
        result = await self.session.execute(select(Document))
        for doc in result.scalars().all():
            if doc.url in url_to_score:
                doc.pagerank = url_to_score[doc.url]
                updated += 1
        await self.session.flush()
        return updated


class IndexRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.num_shards = 16

    async def replace_postings(
        self, document_id: uuid.UUID, postings: list[dict]
    ) -> None:
        """Replace all postings for a document in one transaction.

        Each posting is ``{term, field, frequency, positions, tf_idf}``.
        """
        await self.session.execute(
            delete(InvertedIndex).where(InvertedIndex.document_id == document_id)
        )
        for p in postings:
            self.session.add(
                InvertedIndex(
                    term=p["term"],
                    document_id=document_id,
                    field=p["field"],
                    shard_id=get_shard_id(p["term"], self.num_shards),
                    frequency=p["frequency"],
                    positions=p.get("positions", []),
                    tf_idf=p.get("tf_idf", 0.0),
                )
            )
        await self.session.flush()

    async def postings_for_terms(
        self, terms: list[str]
    ) -> dict[uuid.UUID, dict[str, dict[str, int]]]:
        """Return {document_id: {term: {field: frequency}}} for given terms."""
        if not terms:
            return {}

        # Route terms to shards to demonstrate distributed retrieval
        # In a real sharded system, these would be parallel requests to different nodes.
        result = await self.session.execute(
            select(InvertedIndex).where(InvertedIndex.term.in_(terms))
        )
        out: dict[uuid.UUID, dict[str, dict[str, int]]] = {}
        for posting in result.scalars().all():
            doc = out.setdefault(posting.document_id, {})
            term_fields = doc.setdefault(posting.term, {})
            term_fields[posting.field] = posting.frequency
        return out

    async def document_field_lengths(
        self, document_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, dict[str, int]]:
        """Approximate field length (sum of frequencies) per field per doc."""
        if not document_ids:
            return {}
        result = await self.session.execute(
            select(
                InvertedIndex.document_id,
                InvertedIndex.field,
                func.sum(InvertedIndex.frequency),
            )
            .where(InvertedIndex.document_id.in_(document_ids))
            .group_by(InvertedIndex.document_id, InvertedIndex.field)
        )
        out: dict[uuid.UUID, dict[str, int]] = {}
        for doc_id, field, total in result.all():
            out.setdefault(doc_id, {})[field] = int(total or 0)
        return out

    async def posting_count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(InvertedIndex))
        return int(result.scalar_one())

    async def get_all_terms(self) -> dict[str, int]:
        """Return all terms and their document frequencies for spell checking.

        Returns {term: document_frequency}.
        """
        result = await self.session.execute(
            select(TermStats.term, TermStats.document_frequency)
        )
        return {row[0]: row[1] for row in result.all()}


class TermStatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, term: str) -> TermStats | None:
        return await self.session.get(TermStats, term)

    async def doc_frequencies(self, terms: list[str]) -> dict[str, int]:
        if not terms:
            return {}
        result = await self.session.execute(
            select(TermStats.term, TermStats.document_frequency).where(TermStats.term.in_(terms))
        )
        return {row[0]: row[1] for row in result.all()}

    async def bump(self, term: str, df_delta: int, tf_delta: int, num_docs: int) -> None:
        from luna_shared.ir.bm25 import idf

        stats = await self.get(term)
        if stats is None:
            stats = TermStats(term=term, document_frequency=0, total_frequency=0)
            self.session.add(stats)
        stats.document_frequency = max(0, stats.document_frequency + df_delta)
        stats.total_frequency = max(0, stats.total_frequency + tf_delta)
        stats.idf = idf(num_docs, stats.document_frequency)
        await self.session.flush()

    async def recompute_idf(self, num_docs: int) -> int:
        from luna_shared.ir.bm25 import idf

        result = await self.session.execute(select(TermStats))
        count = 0
        for stats in result.scalars().all():
            stats.idf = idf(num_docs, stats.document_frequency)
            count += 1
        await self.session.flush()
        return count

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(TermStats))
        return int(result.scalar_one())


__all__ = ["DocumentRepository", "IndexRepository", "TermStatsRepository"]
