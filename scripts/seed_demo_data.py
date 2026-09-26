"""Deterministic, offline, idempotent demo-data loader.

Populates a migrated database with:
  - admin users (admin / operator / viewer) with development credentials
  - a completed crawl job and its documents (from the bundled corpus)
  - a full inverted index + term statistics
  - PageRank scores computed over the document link graph
  - query logs (including a zero-result example) and click logs

Running it repeatedly does not create duplicates: documents are upserted by
URL, users by email, and logs are only seeded when empty.

Usage:
    uv run python scripts/seed_demo_data.py
    DATABASE_URL=postgresql://... uv run python scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime, timedelta

from luna_shared.database import Database
from luna_shared.ir.extraction import extract_page
from luna_shared.ir.indexing import build_postings, distinct_terms
from luna_shared.ir.pagerank import compute_pagerank
from luna_shared.models import CrawlStatus
from luna_shared.repositories import (
    AdminRepository,
    AnalyticsRepository,
    CrawlRepository,
    DocumentRepository,
    IndexRepository,
    TermStatsRepository,
)
from luna_shared.security import hash_password

sys.path.insert(0, "scripts")
from demo_corpus import DEMO_PAGES, DEMO_QUERIES  # noqa: E402

DEMO_USERS = [
    ("admin@luna.dev", "admin", "admin123"),
    ("operator@luna.dev", "operator", "operator123"),
    ("viewer@luna.dev", "viewer", "viewer123"),
]


async def seed_users(db: Database) -> dict[str, int]:
    counts = {"inserted": 0, "skipped": 0}
    async with db.session() as session:
        repo = AdminRepository(session)
        for email, role, password in DEMO_USERS:
            if await repo.get_user_by_email(email):
                counts["skipped"] += 1
                continue
            await repo.create_user(
                email=email, hashed_password=hash_password(password), role=role
            )
            counts["inserted"] += 1
    return counts


async def seed_documents(db: Database) -> dict[str, int]:
    counts = {"inserted": 0, "updated": 0}
    # One crawl job to own the documents.
    async with db.session() as session:
        crawl = CrawlRepository(session)
        jobs = await crawl.list_jobs()
        job = next((j for j in jobs if j.name == "Demo Corpus"), None)
        if job is None:
            job = await crawl.create_job(
                name="Demo Corpus",
                seed_urls=list(DEMO_PAGES.keys())[:1],
                allowed_domains=["luna.dev"],
            )
            await crawl.set_status(job, CrawlStatus.COMPLETED)
        job_id = job.id

    async with db.session() as session:
        docs = DocumentRepository(session)
        index = IndexRepository(session)
        for url, html in DEMO_PAGES.items():
            page = extract_page(html, url)
            _doc, created = await docs.upsert(
                url=page.url,
                canonical_url=page.canonical_url,
                content_hash=page.content_hash,
                title=page.title,
                meta_description=page.meta_description,
                headings=page.headings,
                body_text=page.body_text,
                language=page.language,
                outlinks=page.outlinks,
                crawl_id=job_id,
            )
            counts["inserted" if created else "updated"] += 1

        # Rebuild the index deterministically from all documents.
        num_docs = await docs.count()
        all_docs = await docs.get_many(
            [d for d in (await _all_ids(session))]
        )
        # Reset term stats by recomputing from scratch.
        df_counter: dict[str, int] = {}
        tf_counter: dict[str, int] = {}
        for doc in all_docs.values():
            page = extract_page_from_doc(doc)
            postings = build_postings(page)
            await index.replace_postings(doc.id, postings)
            for term in distinct_terms(postings):
                df_counter[term] = df_counter.get(term, 0) + 1
                tf_counter[term] = tf_counter.get(term, 0) + sum(
                    p["frequency"] for p in postings if p["term"] == term
                )
        # Persist term stats.
        from luna_shared.ir.bm25 import idf
        from luna_shared.models import TermStats
        from sqlalchemy import delete

        await session.execute(delete(TermStats))
        for term, df in df_counter.items():
            session.add(
                TermStats(
                    term=term,
                    document_frequency=df,
                    total_frequency=tf_counter[term],
                    idf=idf(num_docs, df),
                )
            )
        await session.flush()

    return counts


def extract_page_from_doc(doc):
    from luna_shared.ir.extraction import ExtractedPage

    return ExtractedPage(
        url=doc.url,
        canonical_url=doc.canonical_url,
        title=doc.title,
        meta_description=doc.meta_description,
        headings=doc.headings or {},
        body_text=doc.body_text,
        outlinks=doc.outlinks or [],
        language=doc.language,
    )


async def _all_ids(session):
    from luna_shared.models import Document
    from sqlalchemy import select

    result = await session.execute(select(Document.id))
    return [row[0] for row in result.all()]


async def seed_pagerank(db: Database) -> float:
    async with db.session() as session:
        docs = DocumentRepository(session)
        links = await docs.all_links()
        nodes = [url for url, _ in links]
        edges = [(url, out) for url, outs in links for out in outs]
        scores = compute_pagerank(nodes, edges)
        await docs.set_pagerank(scores)
        return max(scores.values()) if scores else 0.0


async def seed_logs(db: Database) -> dict[str, int]:
    counts = {"queries": 0, "clicks": 0, "skipped": 0}
    async with db.session() as session:
        analytics = AnalyticsRepository(session)
        if await analytics.query_volume(None, None) > 0:
            counts["skipped"] = 1
            return counts

        doc_ids = await _all_ids(session)
        base = datetime.now(UTC) - timedelta(days=1)
        offset = 0
        for query, result_count in DEMO_QUERIES:
            for _ in range(max(1, result_count)):
                log = await analytics.log_query(
                    query=query,
                    normalized_query=query,
                    results_count=result_count,
                    page=1,
                    per_page=10,
                    search_time_ms=12.0 + offset % 30,
                    filters={},
                    created_at=base + timedelta(minutes=offset),
                )
                counts["queries"] += 1
                offset += 1
                # Seed a click for the first result of non-zero queries.
                if result_count > 0 and doc_ids:
                    await analytics.log_click(
                        query_log_id=log.id,
                        document_id=doc_ids[offset % len(doc_ids)],
                        position=1,
                        dwell_time_ms=1500,
                    )
                    counts["clicks"] += 1
    return counts


async def main() -> int:
    db = Database()
    db.connect()
    if db.is_sqlite:
        await db.create_all()
    # Point the shared global db at the same engine for repositories.
    import luna_shared.database as dbmod

    dbmod.db = db

    users = await seed_users(db)
    documents = await seed_documents(db)
    top_pr = await seed_pagerank(db)
    logs = await seed_logs(db)

    async with db.session() as session:
        doc_count = await DocumentRepository(session).count()
        posting_count = await IndexRepository(session).posting_count()
        term_count = await TermStatsRepository(session).count()

    await db.disconnect()

    print("Demo data loaded:")
    print(f"  users:      +{users['inserted']} (skipped {users['skipped']})")
    print(f"  documents:  +{documents['inserted']} (updated {documents['updated']}) total {doc_count}")
    print(f"  postings:   {posting_count}")
    print(f"  terms:      {term_count}")
    print(f"  pagerank:   top score {top_pr:.4f}")
    print(f"  query logs: +{logs['queries']} clicks +{logs['clicks']} (skipped {logs['skipped']})")
    print("\nDefault admin login: admin@luna.dev / admin123")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
