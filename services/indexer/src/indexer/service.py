"""Indexing service logic: consume a document payload, build postings."""

from __future__ import annotations

import uuid

from luna_shared.ir.extraction import ExtractedPage
from luna_shared.ir.indexing import build_postings
from luna_shared.ir.embeddings import EmbeddingService
from luna_shared.repositories import (
    DocumentRepository,
    IndexRepository,
    TermStatsRepository,
    SemanticSearchRepository,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def index_document(session: AsyncSession, document_id: uuid.UUID) -> dict:
    """(Re)build the inverted index and semantic vector for an existing document.

    Idempotent: replaces the document's postings and semantic vector, and adjusts
    term stats so repeated runs converge to the same state.
    """
    docs = DocumentRepository(session)
    index = IndexRepository(session)
    terms = TermStatsRepository(session)
    semantic = SemanticSearchRepository(session)
    embedder = EmbeddingService()

    doc = await docs.get(document_id)
    if doc is None:
        raise ValueError(f"document {document_id} not found")

    page = ExtractedPage(
        url=doc.url,
        canonical_url=doc.canonical_url,
        title=doc.title,
        meta_description=doc.meta_description,
        headings=doc.headings or {},
        body_text=doc.body_text,
        outlinks=doc.outlinks or [],
        language=doc.language,
    )
    postings = build_postings(page)

    # 1. Update Sparse Index (BM25)
    previous = await index.postings_for_terms(
        list({p["term"] for p in postings})
    )
    previously_had = {
        term for term, docmap in _invert(previous).items() if document_id in docmap
    }
    new_terms = {p["term"] for p in postings}

    await index.replace_postings(document_id, postings)

    num_docs = await docs.count()
    for term in new_terms - previously_had:
        tf = sum(p["frequency"] for p in postings if p["term"] == term)
        await terms.bump(term, df_delta=1, tf_delta=tf, num_docs=num_docs)
    await terms.recompute_idf(num_docs)

    # 2. Update Dense Index (Semantic)
    # Combine title and body for a rich embedding
    text_to_embed = f"{page.title}\n{page.meta_description}\n{page.body_text}"
    vector = embedder.embed(text_to_embed)
    await semantic.upsert_vector(str(document_id), vector)

    return {"document_id": str(document_id), "postings": len(postings), "terms": len(new_terms), "vectorized": True}


def _invert(
    postings_by_doc: dict[uuid.UUID, dict[str, dict[str, int]]],
) -> dict[str, set[uuid.UUID]]:
    out: dict[str, set[uuid.UUID]] = {}
    for doc_id, term_map in postings_by_doc.items():
        for term in term_map:
            out.setdefault(term, set()).add(doc_id)
    return out


__all__ = ["index_document"]
