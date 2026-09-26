"""Crawl orchestration: frontier processing, extraction, and indexing hand-off."""

from __future__ import annotations

from luna_shared.ir.extraction import extract_page
from luna_shared.messaging import Broker, Envelope, ExchangeNames, QueueNames, RoutingKeys
from luna_shared.models import CrawlJob, CrawlStatus
from luna_shared.repositories import CrawlRepository, DocumentRepository
from luna_shared.utils.url import extract_domain, should_crawl_url
from sqlalchemy.ext.asyncio import AsyncSession

from crawler.fetcher import Fetcher, PolitenessManager, RobotsCache


import redis.asyncio as redis

class CrawlService:
    def __init__(
        self,
        session: AsyncSession,
        fetcher: Fetcher,
        broker: Broker,
        redis_client: redis.Redis | None = None,
        *,
        politeness: PolitenessManager | None = None,
        robots: RobotsCache | None = None,
        max_retries: int = 3,
    ) -> None:
        self.session = session
        self.fetcher = fetcher
        self.broker = broker
        self.redis_client = redis_client
        self.politeness = politeness or PolitenessManager()
        self.robots = robots or RobotsCache()
        self.max_retries = max_retries
        self.crawl = CrawlRepository(session, redis_client=redis_client)
        self.docs = DocumentRepository(session)

    async def seed(self, job: CrawlJob) -> int:
        """Enqueue seed URLs. Returns number enqueued."""
        count = 0
        for url in job.seed_urls:
            if await self.crawl.enqueue_url(job.id, url, depth=0, priority=100):
                count += 1
        return count

    def _url_allowed(self, job: CrawlJob, url: str) -> bool:
        return should_crawl_url(
            url,
            allowed_domains=job.allowed_domains or None,
            blocked_domains=job.blocked_domains or None,
        )

    async def process_next(self, job: CrawlJob) -> bool:
        """Process a single frontier entry. Returns False when queue empty."""
        entry = await self.crawl.next_pending(job.id)
        if entry is None:
            return False

        # Policy gates before fetching
        if not self._url_allowed(job, entry.url):
            await self.crawl.mark_queue(entry, "failed", error="blocked by policy")
            return True
        if job.respect_robots_txt:
            allowed = await self.robots.allowed(
                self.fetcher, entry.url, job.user_agent or self.fetcher.user_agent
            )
            if not allowed:
                await self.crawl.mark_queue(entry, "failed", error="robots disallow")
                return True

        domain = extract_domain(entry.url)
        result = None
        for _attempt in range(self.max_retries):
            await self.politeness.acquire(domain)
            try:
                result = await self.fetcher.fetch(entry.url)
            finally:
                self.politeness.release(domain)
            if result.ok or not result.retryable:
                break

        if result is None or not result.ok:
            await self.crawl.mark_queue(
                entry, "failed", error=(result.error if result else "no result")
            )
            await self.crawl.increment_counters(job, failed=1)
            return True

        page = extract_page(result.html, entry.url)
        doc, _created = await self.docs.upsert(
            url=page.url,
            canonical_url=page.canonical_url,
            content_hash=page.content_hash,
            title=page.title,
            meta_description=page.meta_description,
            headings=page.headings,
            body_text=page.body_text,
            images=page.images,
            language=page.language,
            outlinks=page.outlinks,
            crawl_id=job.id,
            status_code=result.status_code,
        )
        await self.crawl.mark_queue(entry, "done")
        await self.crawl.increment_counters(
            job, crawled=1, bytes_downloaded=len(result.html.encode("utf-8", "ignore"))
        )

        # Enqueue discovered links within depth/policy
        if entry.depth < job.max_depth:
            for link in page.outlinks:
                if self._url_allowed(job, link):
                    await self.crawl.enqueue_url(
                        job.id, link, depth=entry.depth + 1, priority=50
                    )

        # Emit index task AFTER the document commit (session commits on exit).
        await self._publish_index_task(doc.id, page.url, page.content_hash)
        return True

    async def _publish_index_task(self, document_id, url: str, content_hash: str) -> None:
        envelope = Envelope(
            event_type=RoutingKeys.INDEX_REQUESTED,
            idempotency_key=f"{document_id}:{content_hash}",
            payload={"document_id": str(document_id), "url": url, "content_hash": content_hash},
        )
        await self.broker.publish(
            ExchangeNames.INDEX, QueueNames.INDEX_REQUESTED, envelope
        )

    async def recover_leases(self) -> int:
        """Recover URLs that were leased but not marked done."""
        if not self.redis_client:
            return 0
        from luna_shared.repositories.redis_frontier import RedisFrontier
        frontier = RedisFrontier(self.redis_client)
        return await frontier.recover_expired()

    async def run_job(self, job: CrawlJob, max_pages: int | None = None) -> dict:
        """Run a job to completion using concurrent workers."""
        job_id = job.id
        limit = max_pages if max_pages is not None else job.max_pages
        await self.crawl.set_status(job, CrawlStatus.RUNNING)

        # Recover any expired leases before starting
        recovered = await self.recover_leases()

        await self.seed(job)

        processed_count = 0
        processed_lock = asyncio.Lock()

        # Limit concurrency to avoid system exhaustion and bans
        # In a real production system, this would be a config value
        CONCURRENCY_LIMIT = 20
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        async def worker():
            nonlocal processed_count
            while True:
                async with semaphore:
                    # Check limit before processing next
                    async with processed_lock:
                        if processed_count >= limit:
                            break

                    more = await self.process_next(job)
                    if not more:
                        break

                    async with processed_lock:
                        processed_count += 1

        # Spawn workers
        workers = [asyncio.create_task(worker()) for _ in range(CONCURRENCY_LIMIT)]
        await asyncio.gather(*workers)

        await self.crawl.set_status(job, CrawlStatus.COMPLETED)
        return {"job_id": str(job_id), "processed": processed_count, "recovered": recovered}


__all__ = ["CrawlService"]
