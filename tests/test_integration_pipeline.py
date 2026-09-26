"""Integration tests for the crawl -> index -> search pipeline."""


import pytest
from luna_shared.ir.extraction import extract_page
from luna_shared.ir.indexing import build_postings, distinct_terms
from luna_shared.repositories import (
    DocumentRepository,
    IndexRepository,
    TermStatsRepository,
)

pytestmark = pytest.mark.asyncio

HTML = {
    "https://x.com/python": "<html><head><title>Python Guide</title></head>"
    "<body><p>learn python programming today python</p></body></html>",
    "https://x.com/java": "<html><head><title>Java Guide</title></head>"
    "<body><p>java programming for enterprise</p></body></html>",
}


async def _index_all(database):
    async with database.session() as session:
        docs = DocumentRepository(session)
        index = IndexRepository(session)
        terms = TermStatsRepository(session)
        for url, html in HTML.items():
            page = extract_page(html, url)
            doc, _ = await docs.upsert(
                url=page.url,
                canonical_url=page.canonical_url,
                content_hash=page.content_hash,
                title=page.title,
                meta_description=page.meta_description,
                headings=page.headings,
                body_text=page.body_text,
                language=page.language,
                outlinks=page.outlinks,
                crawl_id=None,
            )
            postings = build_postings(page)
            await index.replace_postings(doc.id, postings)
            num = await docs.count()
            for term in distinct_terms(postings):
                await terms.bump(term, 1, 1, num)


async def test_documents_and_postings_created(database):
    await _index_all(database)
    async with database.session() as session:
        assert await DocumentRepository(session).count() == 2
        assert await IndexRepository(session).posting_count() > 0
        assert await TermStatsRepository(session).count() > 0


async def test_search_ranks_relevant_first(database):
    from search_api.service import SearchService

    await _index_all(database)
    async with database.session() as session:
        svc = SearchService(session, ranker_url=None)
        result = await svc.search("python programming", page=1, per_page=10)
    assert result["total_results"] >= 1
    assert "python" in result["results"][0]["title"].lower()


async def test_search_exclusion_filter(database):
    from search_api.service import SearchService

    await _index_all(database)
    async with database.session() as session:
        svc = SearchService(session, ranker_url=None)
        result = await svc.search("programming -java", page=1, per_page=10)
    for r in result["results"]:
        assert "java" not in r["title"].lower()


async def test_zero_result_query(database):
    from search_api.service import SearchService

    await _index_all(database)
    async with database.session() as session:
        svc = SearchService(session, ranker_url=None)
        result = await svc.search("nonexistentxyz", page=1, per_page=10)
    assert result["total_results"] == 0
    assert result["results"] == []


async def test_index_idempotency(database):
    """Re-indexing a document must not duplicate postings."""
    from indexer.service import index_document

    await _index_all(database)
    async with database.session() as session:
        docs = DocumentRepository(session)
        doc = await docs.get_by_url("https://x.com/python")
        before = await IndexRepository(session).posting_count()

    async with database.session() as session:
        await index_document(session, doc.id)
        await index_document(session, doc.id)

    async with database.session() as session:
        after = await IndexRepository(session).posting_count()
    assert after == before


async def test_suggest_returns_typed_suggestions(database):
    from search_api.service import SearchService

    await _index_all(database)
    async with database.session() as session:
        svc = SearchService(session, ranker_url=None)
        suggestions = await svc.suggest("py", 10)
    assert all("type" in s and s["type"] for s in suggestions)
