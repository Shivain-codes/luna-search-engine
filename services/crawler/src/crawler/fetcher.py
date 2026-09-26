"""HTTP fetching with politeness, robots, and content limits."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from luna_shared.utils.url import get_robots_txt_url

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass
class FetchResult:
    url: str
    status_code: int
    html: str | None
    content_type: str
    error: str | None = None
    retryable: bool = False

    @property
    def ok(self) -> bool:
        return self.status_code == 200 and self.html is not None


class RobotsCache:
    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, RobotFileParser | None]] = {}

    async def allowed(self, fetcher: Fetcher, url: str, user_agent: str) -> bool:
        domain = urlparse(url).netloc
        now = time.time()
        cached = self._cache.get(domain)
        if cached is None or cached[0] < now:
            parser = await self._load(fetcher, url)
            self._cache[domain] = (now + self.ttl, parser)
        else:
            parser = cached[1]
        if parser is None:
            return True
        return parser.can_fetch(user_agent, url)

    async def _load(self, fetcher: Fetcher, url: str) -> RobotFileParser | None:
        robots_url = get_robots_txt_url(url)
        try:
            text = await fetcher.get_text(robots_url)
        except Exception:
            return None
        if text is None:
            return None
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        return parser


class Fetcher:
    """Async HTTP fetcher. Injectable for offline testing."""

    def __init__(
        self,
        *,
        user_agent: str = "NexusBot/1.0",
        timeout: float = 30.0,
        max_body_bytes: int = 10 * 1024 * 1024,
        max_redirects: int = 10,
        transport: httpx.AsyncBaseTransport | None = None,
        proxy: str | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_body_bytes = max_body_bytes
        self._proxy = proxy
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=max_redirects,
            headers={"User-Agent": user_agent},
            transport=transport,
            proxy=proxy,
        )

    async def get_text(self, url: str) -> str | None:
        resp = await self._client.get(url)
        if resp.status_code != 200:
            return None
        return resp.text

    async def fetch(self, url: str) -> FetchResult:
        try:
            resp = await self._client.get(url)
        except httpx.TimeoutException:
            return FetchResult(url, 0, None, "", error="timeout", retryable=True)
        except httpx.HTTPError as exc:
            return FetchResult(url, 0, None, "", error=str(exc), retryable=True)

        content_type = resp.headers.get("content-type", "").split(";")[0].strip()
        if resp.status_code in RETRYABLE_STATUS:
            return FetchResult(url, resp.status_code, None, content_type,
                               error=f"status {resp.status_code}", retryable=True)
        if resp.status_code != 200:
            return FetchResult(url, resp.status_code, None, content_type,
                               error=f"status {resp.status_code}", retryable=False)
        if content_type and "html" not in content_type and "xml" not in content_type:
            return FetchResult(url, resp.status_code, None, content_type,
                               error="unsupported content type", retryable=False)
        body = resp.text
        if len(body.encode("utf-8", errors="ignore")) > self.max_body_bytes:
            body = body[: self.max_body_bytes]
        return FetchResult(url, 200, body, content_type or "text/html")

    async def close(self) -> None:
        await self._client.aclose()


class PolitenessManager:
    """Per-domain delay + concurrency and global concurrency limiter."""

    def __init__(self, delay: float = 1.0, per_domain: int = 2, global_limit: int = 50) -> None:
        self.delay = delay
        self._domain_last: dict[str, float] = {}
        self._domain_sems: dict[str, asyncio.Semaphore] = {}
        self._per_domain = per_domain
        self._global = asyncio.Semaphore(global_limit)

    def _domain_sem(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_sems:
            self._domain_sems[domain] = asyncio.Semaphore(self._per_domain)
        return self._domain_sems[domain]

    async def acquire(self, domain: str) -> None:
        await self._global.acquire()
        await self._domain_sem(domain).acquire()
        last = self._domain_last.get(domain, 0.0)
        wait = self.delay - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)

    def release(self, domain: str) -> None:
        self._domain_last[domain] = time.monotonic()
        self._domain_sem(domain).release()
        self._global.release()

__all__ = ["FetchResult", "Fetcher", "PolitenessManager", "RobotsCache", "RETRYABLE_STATUS"]
