"""Script to remove demo data and re-index remaining real documents.
This ensures that only real, accessible websites appear in search results.
"""

from __future__ import annotations
import asyncio
import sys
from sqlalchemy import delete, select

from luna_shared.database import Database
from luna_shared.models import Document, CrawlJob, InvertedIndex, TermStats
from luna_shared.repositories import (
    CrawlRepository,
    DocumentRepository,
    IndexRepository,
    TermStatsRepository
)
from luna_shared.ir.indexing import build_postings, distinct_terms
from luna_shared.ir.bm25 import idf

def extract_page_from_doc(doc):
    """Convert a Document model instance into an ExtractedPage-like object for indexing."""
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

async def clear_demo_data():
    db = Database()
    db.connect()

    # Point the shared global db at the same engine for repositories.
    import luna_shared.database as dbmod
    dbmod.db = db

    async with db.session() as session:
        print("🔍 Searching for Demo Corpus...")
        crawl_repo = CrawlRepository(session)
        jobs = await crawl_repo.list_jobs()
        demo_job = next((j for j in jobs if j.name == "Demo Corpus"), None)

        if not demo_job:
            print("✅ No Demo Corpus found. Your index is already clean.")
            await db.disconnect()
            return

        job_id = demo_job.id
        print(f"🗑️ Removing documents from job: {demo_job.name} ({job_id})")

        # Delete documents associated with the demo job
        await session.execute(
            delete(Document).where(Document.crawl_id == job_id)
        )

        # Delete the job itself
        await session.execute(
            delete(CrawlJob).where(CrawlJob.id == job_id)
        )

        print("✅ Demo documents and job removed.")

        # --- RE-INDEXING PHASE ---
        print("♻️ Re-indexing remaining real documents...")

        # 1. Clear existing index and stats
        await session.execute(delete(InvertedIndex))
        await session.execute(delete(TermStats))

        # 2. Re-calculate postings and stats for remaining docs
        res = await session.execute(select(Document.id))
        all_ids = res.scalars().all()

        doc_repo = DocumentRepository(session)
        all_docs = await doc_repo.get_many(all_ids)

        num_docs = len(all_docs)
        if num_docs == 0:
            print("⚠️ No documents left to index.")
        else:
            df_counter: dict[str, int] = {}
            tf_counter: dict[str, int] = {}
            index_repo = IndexRepository(session)

            for doc in all_docs.values():
                page = extract_page_from_doc(doc)
                postings = build_postings(page)
                await index_repo.replace_postings(doc.id, postings)

                for term in distinct_terms(postings):
                    df_counter[term] = df_counter.get(term, 0) + 1
                    tf_counter[term] = tf_counter.get(term, 0) + sum(
                        p["frequency"] for p in postings if p["term"] == term
                    )

            # 3. Persist new TermStats
            for term, df in df_counter.items():
                session.add(
                    TermStats(
                        term=term,
                        document_frequency=df,
                        total_frequency=tf_counter[term],
                        idf=idf(num_docs, df),
                    )
                )

            await session.commit()
            print(f"✅ Successfully re-indexed {num_docs} real documents.")

    await db.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(clear_demo_data())
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
