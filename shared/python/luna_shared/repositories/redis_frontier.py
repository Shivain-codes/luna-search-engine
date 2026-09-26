"""Redis-backed distributed frontier for the web crawler."""

from __future__ import annotations

import time
import json
from typing import Tuple, Optional
import redis.asyncio as redis

class RedisFrontier:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.pending_key = "frontier:pending"
        self.processing_key = "frontier:processing"
        self.lease_timeout = 300  # 5 minutes

    async def enqueue(self, url: str, priority: int) -> None:
        """Add a URL to the priority queue. Higher priority = processed first."""
        # Use negative priority because ZPOPMIN pops the smallest score.
        await self.redis.zadd(self.pending_key, {url: -priority})

    async def pop_next(self) -> Optional[str]:
        """Atomically pop the highest priority URL and lease it."""
        # Lua script to ensure atomicity
        lua_script = """
        local url = redis.call('ZPOPMIN', KEYS[1])
        if url[1] then
            local url_val = url[1]
            local priority = -url[2]
            local expiry = ARGV[1]
            redis.call('HSET', KEYS[2], url_val, cjson.encode({priority=priority, expiry=expiry}))
            return url_val
        end
        return nil
        """
        expiry = time.time() + self.lease_timeout
        result = await self.redis.eval(lua_script, 2, self.pending_key, self.processing_key, expiry)
        return result if result else None

    async def mark_done(self, url: str) -> None:
        """Remove URL from processing set."""
        await self.redis.hdel(self.processing_key, url)

    async def recover_expired(self) -> int:
        """Recover URLs that were leased but not marked done within the timeout."""
        now = time.time()
        recovered_count = 0

        processing = await self.redis.hgetall(self.processing_key)
        for url, data_json in processing.items():
            try:
                # Redis returns bytes
                data = json.loads(data_json if isinstance(data_json, str) else data_json.decode())
                if now > data["expiry"]:
                    # Re-enqueue with original priority
                    await self.redis.zadd(self.pending_key, {url.decode() if isinstance(url, bytes) else url: -data["priority"]})
                    await self.redis.hdel(self.processing_key, url)
                    recovered_count += 1
            except (json.JSONDecodeError, KeyError):
                continue

        return recovered_count
