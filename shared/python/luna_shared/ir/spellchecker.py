import uuid
import collections
from typing import Any

class SpellChecker:
    """
    Implements spell correction using Levenshtein distance
    and term frequency from the inverted index.
    """
    def __init__(self, index_repo: Any):
        self.index = index_repo

    def _levenshtein(self, s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return self._levenshtein(s2, s1)
        if not s2:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    async def suggest(self, term: str, max_distance: int = 2) -> str | None:
        """
        Finds the best correction for a term based on:
        1. Levenshtein distance (primary)
        2. Term frequency in index (tie-breaker)
        """
        # Get all unique terms from index
        all_terms = await self.index.get_all_terms()
        if not all_terms:
            return None

        candidates = []
        for candidate, freq in all_terms.items():
            dist = self._levenshtein(term, candidate)
            if dist <= max_distance:
                candidates.append((candidate, dist, freq))

        if not candidates:
            return None

        # Sort by distance (asc) then frequency (desc)
        candidates.sort(key=lambda x: (x[1], -x[2]))

        # Only suggest if the best candidate is significantly better
        # or if the original term is not in the index
        best_term, best_dist, _ = candidates[0]
        if term in all_terms:
            return None

        return best_term
