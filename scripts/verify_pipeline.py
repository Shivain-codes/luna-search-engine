"""End-to-end pipeline verification without external infrastructure.

Runs crawl -> index -> rank -> search entirely in-process against SQLite and
an in-memory broker, using an offline fixture fetcher. Exits non-zero on any
failed assertion.
"""

from __future__ import annotations

import asyncio
import sys

from luna_shared.database import Database
from luna_shared.messaging import Broker, QueueNames
from luna_shared.repositories import CrawlRepository, DocumentRepository, IndexRepository

FIXTURES = {
    "https://example.test/python": """
        <html lang="en"><head><title>Python Programming Language</title>
        <meta name="description" content="Learn Python programming"></head>
        <body><h1>Python</h1><p>Python is a popular programming language for
        web development, data science, and automation. Learn python today.</p>
        <a href="https://example.test/data">Data science</a></body></html>
    """,
    "https://example.test/data": """
        <html lang="en"><head><title>Data Science with Python</title></head>
        <body><h1>Data Science</h1><p>Data science uses python and statistics
        to analyze data and build models.</p>
        <a href="https://example.test/python">Python</a></body></html>
    """,
    "https://example.test/java": """
        <html lang="en"><head><title>Java Programming</title></head>
        <body><h1>Java</h1><p>Java is a programming language for enterprise
        applications and android development.</p></body></html>
    """,
}


class FixtureFetcher:
    user_agent = "TestBot/1.0"

    async def fetch(self, url: str):
        from crawler.fetcher import FetchResult

        html = FIXTURES.get(url)
        if html is None:
            return FetchResult(url, 404, None, "text/html", error="not found")
        return FetchResult(url, 200, html, "text/html")

    async def get_text(self, url: str):
        return None  # no robots.txt in fixtures

    async def close(self):
        pass


async def main() -> int:
    import os
    import tempfile

    tmp = os.path.join(tempfile.gettempdir(), "nexus_verify.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    db = Database(f"sqlite+aiosqlite:///{tmp}")
    db.connect()
    await db.create_all()

    # Patch the shared global db so services/repositories share this engine.
    import luna_shared.database as dbmod

    dbmod.db = db

    broker = Broker("memory://")
    await broker.connect()

    from crawler.fetcher import PolitenessManager
    from crawler.service import CrawlService
    from indexer.service import index_document
    from search_api.service import SearchService

    # 1) Crawl
    async with db.session() as session:
        crawl_repo = CrawlRepository(session)
        job = await crawl_repo.create_job(
            name="demo",
            seed_urls=list(FIXTURES.keys()),
            allowed_domains=["example.test"],
            max_depth=2,
            max_pages=50,
        )
        job_id = job.id

    async with db.session() as session:
        service = CrawlService(
            session, FixtureFetcher(), broker, politeness=PolitenessManager(delay=0.0)
        )
        job = await CrawlRepository(session).get_job(job_id)
        outcome = await service.run_job(job, max_pages=50)
    print(f"crawl: {outcome}")

    # Process index tasks emitted during the crawl (indexer role).
    indexed: list[str] = []

    async def on_index(envelope):
        import uuid

        async with db.session() as s:
            result = await index_document(s, uuid.UUID(envelope.payload["document_id"]))
            indexed.append(result["document_id"])

    await broker.process_pending(QueueNames.INDEX_REQUESTED, on_index)

    async with db.session() as session:
        doc_count = await DocumentRepository(session).count()
        posting_count = await IndexRepository(session).posting_count()
    print(f"documents={doc_count} postings={posting_count} indexed_events={len(indexed)}")
    assert doc_count == 3, f"expected 3 docs, got {doc_count}"
    assert posting_count > 0, "no postings created"
    assert len(indexed) >= 3, f"expected >=3 index events, got {len(indexed)}"

    # 2) Search
    async with db.session() as session:
        search = SearchService(session, ranker_url=None)
        result = await search.search("python programming", page=1, per_page=10)
    print(f"search 'python programming': {result['total_results']} results")
    for r in result["results"]:
        print(f"  {r['score']:.4f}  {r['title']}")
    assert result["total_results"] >= 2, "python query should match multiple docs"
    top_title = result["results"][0]["title"].lower()
    assert "python" in top_title, f"top result should be python-related, got {top_title}"

    # 3) Filter: exclude java
    async with db.session() as session:
        search = SearchService(session, ranker_url=None)
        result = await search.search("programming -java", page=1, per_page=10)
    titles = [r["title"] for r in result["results"]]
    print(f"search 'programming -java': {titles}")
    assert all("java" not in t.lower() for t in titles), "java should be excluded"

    # 4) Zero results
    async with db.session() as session:
        search = SearchService(session, ranker_url=None)
        result = await search.search("nonexistentterm12345", page=1, per_page=10)
    assert result["total_results"] == 0, "should be zero results"
    print("zero-result query OK")

    # 5) Suggest
    async with db.session() as session:
        search = SearchService(session, ranker_url=None)
        suggestions = await search.suggest("py", 10)
    print(f"suggest 'py': {[s['text'] for s in suggestions]}")
    assert all("type" in s and s["type"] for s in suggestions)

    await broker.close()
    await db.disconnect()
    print("\nPIPELINE OK: crawl -> index -> rank -> search verified end to end")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
