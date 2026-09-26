"""Repository for semantic search using vector embeddings."""

from __future__ import annotations

import numpy as np
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

class SemanticSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        # In a production system, this would be a connection to Qdrant, Milvus, or Weaviate.
        # For this implementation, we use a simplified in-memory vector index
        # to demonstrate the architecture.
        self.vector_index: dict[str, np.ndarray] = {}

    async def upsert_vector(self, doc_id: str, vector: np.ndarray) -> None:
        """Store a document vector in the index."""
        self.vector_index[doc_id] = vector

    async def search(self, query_vector: np.ndarray, top_k: int = 10) -> list[Tuple[str, float]]:
        """Perform cosine similarity search. Returns list of (doc_id, score)."""
        if not self.vector_index:
            return []

        results = []
        for doc_id, doc_vector in self.vector_index.items():
            # Cosine similarity: (A . B) / (||A|| ||B||)
            norm_a = np.linalg.norm(query_vector)
            norm_b = np.linalg.norm(doc_vector)
            if norm_a == 0 or norm_b == 0:
                score = 0.0
            else:
                score = np.dot(query_vector, doc_vector) / (norm_a * norm_b)
            results.append((doc_id, float(score)))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
