"""Recompute PageRank over the document link graph and persist scores.

Usage:
    uv run python scripts/compute_pagerank.py
"""

from __future__ import annotations

import asyncio
import sys

from luna_shared.config import get_settings
from luna_shared.database import Database
from luna_shared.ir.pagerank import compute_pagerank
from luna_shared.repositories import DocumentRepository


async def main() -> int:
    settings = get_settings()
    db = Database(settings.database_url)
    db.connect()
    if db.is_sqlite:
        await db.create_all()
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
    await db.disconnect()
    print(f"PageRank recomputed: {len(nodes)} nodes, {len(edges)} edges, {updated} documents updated")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
