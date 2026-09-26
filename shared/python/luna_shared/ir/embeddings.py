"""Simple embedding service for document vectorization."""

from __future__ import annotations

import numpy as np
import hashlib

class EmbeddingService:
    """
    Generates document embeddings.
    In a production system, this would call an LLM embedding API (e.g., OpenAI, Cohere)
    or run a local model (e.g., Sentence-Transformers).
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def embed(self, text: str) -> np.ndarray:
        """
        Generate a deterministic mock embedding for the given text.
        This ensures the project is runnable without external API keys
        while maintaining the architecture of a real vector search engine.
        """
        # Create a deterministic seed from the text hash
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        np.random.seed(seed)

        # Generate a random unit vector
        vec = np.random.randn(self.dimension)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

__all__ = ["EmbeddingService"]
