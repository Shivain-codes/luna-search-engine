"""Rate limiting backed by the shared cache (sliding window)."""

from __future__ import annotations

from luna_shared.cache.redis_client import Cache, get_cache


class RateLimiter:
    def __init__(self, cache: Cache | None = None) -> None:
        self.cache = cache or get_cache()

    async def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Return ``(allowed, current_count)`` for the sliding window."""
        return await self.cache.rate_limit(key, limit, window_seconds)


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


__all__ = ["RateLimiter", "get_rate_limiter"]
