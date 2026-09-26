"""Repository for crawl jobs and the URL frontier."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import redis.asyncio as redis
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from luna_shared.models import CrawlJob, CrawlQueue, CrawlStatus
from luna_shared.utils.url import extract_domain, normalize_url


from luna_shared.repositories.redis_frontier import RedisFrontier

class CrawlRepository:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis | None = None) -> None:
        self.session = session
        self.redis_client = redis_client
        self.frontier = RedisFrontier(redis_client) if redis_client else None


    async def create_job(self, **kwargs) -> CrawlJob:
        job = CrawlJob(**kwargs)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job(self, job_id: uuid.UUID) -> CrawlJob | None:
        return await self.session.get(CrawlJob, job_id)

    async def list_jobs(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[CrawlJob]:
        stmt = select(CrawlJob).order_by(CrawlJob.created_at.desc())
        if status:
            stmt = stmt.where(CrawlJob.status == status)
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_status(
        self, job: CrawlJob, status: CrawlStatus | str, error: str | None = None
    ) -> CrawlJob:
        value = status.value if isinstance(status, CrawlStatus) else status
        job.status = value
        now = datetime.now(UTC)
        if value == CrawlStatus.RUNNING.value and job.started_at is None:
            job.started_at = now
        if value in {
            CrawlStatus.COMPLETED.value,
            CrawlStatus.FAILED.value,
            CrawlStatus.CANCELLED.value,
        }:
            job.completed_at = now
        if error:
            job.error_message = error
        await self.session.flush()
        return job

    async def get_next_pending_job(self) -> CrawlJob | None:
        """Find the first job that is currently pending."""
        stmt = select(CrawlJob).where(CrawlJob.status == "pending").order_by(CrawlJob.created_at.asc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def enqueue_url(
        self, job_id: uuid.UUID, url: str, depth: int, priority: int

    ) -> bool:
        """Add a URL to the frontier. Returns False if it is a duplicate."""
        normalized = normalize_url(url)
        # Pre-check avoids relying on rollback (which would expire the whole
        # session's identity map). Combined with the unique index this is
        # safe for the single-worker crawl loop.
        existing = await self.session.execute(
            select(CrawlQueue.id).where(
                CrawlQueue.crawl_job_id == job_id,
                CrawlQueue.normalized_url == normalized,
            )
        )
        if existing.first() is not None:
            return False
        entry = CrawlQueue(
            crawl_job_id=job_id,
            url=url,
            normalized_url=normalized,
            domain=extract_domain(normalized),
            depth=depth,
            priority=priority,
        )
        self.session.add(entry)
        try:
            await self.session.flush()
            if self.frontier:
                await self.frontier.enqueue(url, priority)
            return True
        except IntegrityError:
            return False

    async def next_pending(self, job_id: uuid.UUID) -> CrawlQueue | None:
        if self.frontier:
            url = await self.frontier.pop_next()
            if not url:
                return None

            # Fetch the record from DB for this URL and job
            stmt = select(CrawlQueue).where(
                CrawlQueue.crawl_job_id == job_id,
                CrawlQueue.url == url,
                CrawlQueue.status == "pending"
            ).limit(1)
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()

        stmt = (
            select(CrawlQueue)
            .where(CrawlQueue.crawl_job_id == job_id, CrawlQueue.status == "pending")
            .order_by(CrawlQueue.priority.desc(), CrawlQueue.scheduled_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_queue(
        self, entry: CrawlQueue, status: str, error: str | None = None
    ) -> None:
        entry.status = status
        entry.attempts += 1
        if status == "done":
            entry.crawled_at = datetime.now(UTC)
        if error:
            entry.last_error = error
        await self.session.flush()
        if self.frontier:
            await self.frontier.mark_done(entry.url)

    async def queue_stats(self, job_id: uuid.UUID | None = None) -> dict:
        stmt = select(CrawlQueue.status, func.count()).group_by(CrawlQueue.status)
        if job_id:
            stmt = stmt.where(CrawlQueue.crawl_job_id == job_id)
        result = await self.session.execute(stmt)
        by_status = {row[0]: int(row[1]) for row in result.all()}

        dom_stmt = select(CrawlQueue.domain, func.count()).group_by(CrawlQueue.domain)
        if job_id:
            dom_stmt = dom_stmt.where(CrawlQueue.crawl_job_id == job_id)
        dom_result = await self.session.execute(dom_stmt)
        by_domain = {row[0]: int(row[1]) for row in dom_result.all()}

        return {
            "pending": by_status.get("pending", 0),
            "in_progress": by_status.get("in_progress", 0),
            "done": by_status.get("done", 0),
            "failed": by_status.get("failed", 0),
            "total": sum(by_status.values()),
            "domains": by_domain,
        }

    async def increment_counters(
        self, job: CrawlJob, crawled: int = 0, failed: int = 0, bytes_downloaded: int = 0
    ) -> None:
        job.pages_crawled += crawled
        job.pages_failed += failed
        job.bytes_downloaded += bytes_downloaded
        await self.session.flush()


__all__ = ["CrawlRepository"]
