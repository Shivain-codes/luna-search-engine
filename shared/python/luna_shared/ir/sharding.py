"""Utilities for term-based sharding of the inverted index."""

from __future__ import annotations

import hashlib

def get_shard_id(term: str, num_shards: int) -> int:
    """Route a term to a shard ID using a consistent hash."""
    # Use MD5 for a stable, well-distributed hash
    hash_val = int(hashlib.md5(term.encode()).hexdigest(), 16)
    return hash_val % num_shards
