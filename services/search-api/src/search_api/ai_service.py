"""AI Service for generating search summaries using Nemotron 3 Ultra."""

from __future__ import annotations

import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

class AIService:
    """
    Handles communication with the Nemotron 3 Ultra LLM.
    Implements a RAG (Retrieval-Augmented Generation) pattern to synthesize
    answers based on retrieved search results.
    """
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.nvidia.com/v1"):
        self.api_key = api_key
        self.base_url = base_url

    async def generate_answer(self, query: str, context_docs: list[dict[str, Any]]) -> str | None:
        """
        Synthesizes a concise, professional answer based on the provided search results.
        """
        if not self.api_key:
            # Fallback for development: Return a simulated AI response
            return f"[AI Simulation] Based on the results for '{query}', the most relevant information is found in the top documents. (API Key missing)"

        if not context_docs:
            return None

        # Construct the RAG context
        context_text = "\n\n".join([
            f"Source {i+1} ({doc['url']}):\n{doc['snippet']}"
            for i, doc in enumerate(context_docs[:5])
        ])

        prompt = (
            "You are a professional, concise search assistant. "
            "Using ONLY the provided context, answer the user's query accurately. "
            "If the answer is not in the context, say 'I couldn't find a definitive answer in the indexed pages.' "
            "Keep the answer to 2-3 sentences. Do not mention the sources by index, just synthesize the info.\n\n"
            f"Context:\n{context_text}\n\n"
            f"Query: {query}\n\n"
            "Answer:"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "nemotron-3-ultra", # Model ID as specified
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                        "max_tokens": 150,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"AI Generation Error: {e}")
            return None

__all__ = ["AIService"]
