"""Cache client with Redis and in-memory backends.

When ``REDIS_URL`` is ``memory://`` (the default for local dev), an
in-process TTL cache is used so the stack runs without Redis. Otherwise a
real async Redis client is used. The public API is identical.
"""

from __future__ import annotations

import json
import time
from typing import Any

from luna_shared.config import get_settings


class _MemoryBackend:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float | None, str]] = {}
        self._counts: dict[str, list[float]] = {}

    def _expired(self, key: str) -> bool:
        entry = self._data.get(key)
        if entry is None:
            return True
        expires_at, _ = entry
        if expires_at is not None and expires_at < time.time():
            self._data.pop(key, None)
            return True
        return False

    async def get(self, key: str) -> str | None:
        if self._expired(key):
            return None
        return self._data[key][1]

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        expires_at = time.time() + ttl if ttl else None
        self._data[key] = (expires_at, value)
        return True

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if self._data.pop(key, None) is not None:
                removed += 1
        return removed

    async def incr_window(self, key: str, window: int) -> int:
        now = time.time()
        bucket = [t for t in self._counts.get(key, []) if t > now - window]
        bucket.append(now)
        self._counts[key] = bucket
        return len(bucket)

    async def ping(self) -> bool:
        return True

    async def publish(self, channel: str, message: str) -> int:
        # In-memory backend doesn't support real pub/sub; return 0
        return 0

    async def subscribe(self, channel: str):
        # In-memory backend doesn't support real pub/sub
        return None


    async def close(self) -> None:
        self._data.clear()
        self._counts.clear()


class _RedisBackend:
    def __init__(self, url: str) -> None:
        import redis.asyncio as redis

        self._client = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> bool:
        return bool(await self._client.set(key, value, ex=ttl))

    async def delete(self, *keys: str) -> int:
        return int(await self._client.delete(*keys))

    async def incr_window(self, key: str, window: int) -> int:
        now = time.time()
        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zadd(key, {f"{now}": now})
        pipe.zcard(key)
        pipe.expire(key, window + 1)
        results = await pipe.execute()
        return int(results[2])

    async def ping(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def publish(self, channel: str, message: str) -> int:
        return await self._client.publish(channel, message)

    async def subscribe(self, channel: str):
        return self._client.pubsub()


    async def close(self) -> None:
        await self._client.aclose()


class Cache:
    """High-level cache facade with JSON (de)serialization."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or get_settings().redis_url
        self._backend: _MemoryBackend | _RedisBackend | None = None

    @property
    def is_memory(self) -> bool:
        return self.url.startswith("memory://")

    async def connect(self) -> None:
        if self._backend is not None:
            return
        self._backend = _MemoryBackend() if self.is_memory else _RedisBackend(self.url)

    def _b(self) -> _MemoryBackend | _RedisBackend:
        if self._backend is None:
            self._backend = _MemoryBackend() if self.is_memory else _RedisBackend(self.url)
        return self._backend

    async def get_json(self, key: str, default: Any = None) -> Any:
        raw = await self._b().get(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return default

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self._b().set(key, json.dumps(value, default=str), ttl)

    async def delete(self, *keys: str) -> int:
        return await self._b().delete(*keys)

    async def rate_limit(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        count = await self._b().incr_window(f"ratelimit:{key}", window)
        return count <= limit, count

    async def publish(self, channel: str, message: str) -> int:
        return await self._b().publish(channel, message)

    async def subscribe(self, channel: str):
        return await self._b().subscribe(channel)


    async def ping(self) -> bool:
        return await self._b().ping()


_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


# Backwards-compatible aliases
RedisCache = Cache
get_redis_cache = get_cache

__all__ = ["Cache", "RedisCache", "get_cache", "get_redis_cache"]
