import os
import uuid
from contextlib import asynccontextmanager

import asyncio
from fastapi import FastAPI, BackgroundTasks
from luna_shared.app import create_app
from luna_shared.config import CrawlerSettings
from luna_shared.database import close_db, db, init_db
import redis.asyncio as redis
from luna_shared.errors import NotFoundError
from luna_shared.messaging import Broker, get_broker
from luna_shared.repositories import CrawlRepository
from pydantic import BaseModel

from crawler.fetcher import Fetcher, PolitenessManager
from crawler.service import CrawlService

settings = CrawlerSettings()
broker: Broker = get_broker()

async def job_watcher_loop():
    """Background loop that automatically picks up pending crawl jobs."""
    while True:
        try:
            async with db.session() as session:
                redis_client = (
                    None
                    if settings.redis_url.startswith("memory://")
                    else redis.from_url(settings.redis_url)
                )
                crawl = CrawlRepository(session, redis_client=redis_client)

                # Find the first pending job
                job = await crawl.get_next_pending_job()
                if job:
                    # Log that we found a job
                    print(f"Watcher: Found pending job {job.id}, starting now...")
                    service = _make_service(session, redis_client)
                    try:
                        await service.run_job(job)
                    finally:
                        await service.fetcher.close()
                        if redis_client is not None:
                            await redis_client.close()
        except Exception as e:
            print(f"Watcher Error: {e}")

        await asyncio.sleep(10) # Check for new jobs every 10 seconds

from fastapi import FastAPI
from luna_shared.app import create_app
from luna_shared.config import CrawlerSettings
from luna_shared.database import close_db, db, init_db
import redis.asyncio as redis
from luna_shared.errors import NotFoundError
from luna_shared.messaging import Broker, get_broker
from luna_shared.repositories import CrawlRepository
from pydantic import BaseModel

from crawler.fetcher import Fetcher, PolitenessManager
from crawler.service import CrawlService

settings = CrawlerSettings()
broker: Broker = get_broker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await init_db()
    await broker.connect()

    # Start the background job watcher
    app.state.watcher_task = asyncio.create_task(job_watcher_loop())

    yield

    app.state.watcher_task.cancel()
    await broker.close()
    await close_db()


app, health = create_app(settings, title="Luna Crawler", lifespan=lifespan)
health.register("postgres", db.ping)
health.register("rabbitmq", broker.ping)


class RunJobRequest(BaseModel):
    job_id: str
    max_pages: int | None = None


def _make_service(session, redis_client) -> CrawlService:
    tor_proxy = os.getenv("TOR_PROXY")
    fetcher = Fetcher(
        user_agent="NexusBot/1.0 (+https://nexussearch.dev/bot)",
        proxy=tor_proxy
    )
    return CrawlService(session, fetcher, broker, redis_client=redis_client, politeness=PolitenessManager(delay=0.0))


@app.post("/api/v1/crawl/run")
async def run_job(request: RunJobRequest) -> dict:
    async with db.session() as session:
        # Local mode uses the database frontier; production can use Redis.
        redis_client = (
            None
            if settings.redis_url.startswith("memory://")
            else redis.from_url(settings.redis_url)
        )
        crawl = CrawlRepository(session, redis_client=redis_client)
        job = await crawl.get_job(uuid.UUID(request.job_id))
        if job is None:
            raise NotFoundError("Crawl job not found")
        service = _make_service(session, redis_client)
        try:
            return await service.run_job(job, max_pages=request.max_pages)
        finally:
            await service.fetcher.close()
            if redis_client is not None:
                await redis_client.close()


@app.get("/api/v1/crawl/queue/stats")
async def queue_stats(job_id: str | None = None) -> dict:
    async with db.session() as session:
        crawl = CrawlRepository(session)
        jid = uuid.UUID(job_id) if job_id else None
        return await crawl.queue_stats(jid)


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
