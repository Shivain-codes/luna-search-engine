"""Admin API: authentication, crawl control, analytics, settings, API keys."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, Query, Request
from luna_shared.app import create_app
from luna_shared.config import AdminAPISettings
from luna_shared.database import close_db, db, init_db
from luna_shared.errors import AuthenticationError, NotFoundError, ValidationError
from luna_shared.repositories import (
    AdminRepository,
    AnalyticsRepository,
    CrawlRepository,
    DocumentRepository,
    IndexRepository,
    TermStatsRepository,
)
from luna_shared.repositories.analytics import percentile
from luna_shared.security import (
    Permission,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    verify_password,
)
from pydantic import BaseModel, Field

from admin_api.deps import Principal, require

settings = AdminAPISettings()

ALLOWED_SETTING_KEYS = {
    "bm25_k1", "bm25_b", "pagerank_damping", "crawler_delay", "search_cache_ttl",
    "ranking_bm25_weight", "ranking_pagerank_weight",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await init_db()
    yield
    await close_db()


app, health = create_app(settings, title="Luna Admin API", lifespan=lifespan)
health.register("postgres", db.ping)


# ---- Schemas ----
class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class CrawlJobCreate(BaseModel):
    name: str
    seed_urls: list[str]
    allowed_domains: list[str] = Field(default_factory=list)
    blocked_domains: list[str] = Field(default_factory=list)
    max_depth: int = 3
    max_pages: int = 1000
    priority: int = 10


class CrawlJobUpdate(BaseModel):
    action: str  # pause | resume | cancel


class SettingUpdate(BaseModel):
    value: str
    description: str | None = None


class APIKeyCreate(BaseModel):
    name: str
    rate_limit: int = 1000


def _job_dict(job) -> dict:
    return {
        "id": str(job.id),
        "name": job.name,
        "seed_urls": job.seed_urls,
        "allowed_domains": job.allowed_domains,
        "status": job.status,
        "priority": job.priority,
        "max_depth": job.max_depth,
        "max_pages": job.max_pages,
        "pages_crawled": job.pages_crawled,
        "pages_failed": job.pages_failed,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
    }


# ---- Auth ----
@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    async with db.session() as session:
        repo = AdminRepository(session)
        user = await repo.get_user_by_email(payload.email)
        if user is None or not user.is_active or not verify_password(
            payload.password, user.hashed_password
        ):
            raise AuthenticationError("Invalid credentials")
        await repo.touch_login(user)
        access = create_access_token(str(user.id), user.role)
        refresh = create_refresh_token(str(user.id), user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@app.post("/api/v1/auth/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str = Query(...)) -> TokenResponse:
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload is None:
        raise AuthenticationError("Invalid refresh token")
    async with db.session() as session:
        repo = AdminRepository(session)
        user = await repo.get_user(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise AuthenticationError("Account not active")
    access = create_access_token(payload["sub"], payload["role"])
    new_refresh = create_refresh_token(payload["sub"], payload["role"])
    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


# ---- Crawl management ----
@app.get("/api/v1/admin/crawl/jobs")
async def list_jobs(
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Principal = Depends(require(Permission.CRAWL_READ)),
) -> list[dict]:
    async with db.session() as session:
        jobs = await CrawlRepository(session).list_jobs(status, limit, offset)
        return [_job_dict(j) for j in jobs]


@app.post("/api/v1/admin/crawl/jobs", status_code=201)
async def create_job(
    payload: CrawlJobCreate,
    request: Request,
    principal: Principal = Depends(require(Permission.CRAWL_WRITE)),
) -> dict:
    async with db.session() as session:
        repo = CrawlRepository(session)
        job = await repo.create_job(
            name=payload.name,
            seed_urls=payload.seed_urls,
            allowed_domains=payload.allowed_domains,
            blocked_domains=payload.blocked_domains,
            max_depth=payload.max_depth,
            max_pages=payload.max_pages,
            priority=payload.priority,
        )
        await AdminRepository(session).audit(
            action="crawl.create",
            actor_id=uuid.UUID(principal.user_id),
            actor_role=principal.role,
            target_type="crawl_job",
            target_id=str(job.id),
            request_id=getattr(request.state, "request_id", None),
        )
        return _job_dict(job)


@app.get("/api/v1/admin/crawl/jobs/{job_id}")
async def get_job(
    job_id: str, _: Principal = Depends(require(Permission.CRAWL_READ))
) -> dict:
    async with db.session() as session:
        job = await CrawlRepository(session).get_job(uuid.UUID(job_id))
        if job is None:
            raise NotFoundError("Crawl job not found")
        return _job_dict(job)


@app.patch("/api/v1/admin/crawl/jobs/{job_id}")
async def update_job(
    job_id: str,
    payload: CrawlJobUpdate,
    request: Request,
    principal: Principal = Depends(require(Permission.CRAWL_WRITE)),
) -> dict:
    status_map = {"pause": "paused", "resume": "running", "cancel": "cancelled"}
    if payload.action not in status_map:
        raise ValidationError("Invalid action", details={"allowed": list(status_map)})
    async with db.session() as session:
        repo = CrawlRepository(session)
        job = await repo.get_job(uuid.UUID(job_id))
        if job is None:
            raise NotFoundError("Crawl job not found")
        await repo.set_status(job, status_map[payload.action])
        await AdminRepository(session).audit(
            action=f"crawl.{payload.action}",
            actor_id=uuid.UUID(principal.user_id),
            actor_role=principal.role,
            target_type="crawl_job",
            target_id=job_id,
            request_id=getattr(request.state, "request_id", None),
        )
        return _job_dict(job)


@app.get("/api/v1/admin/crawl/queue/stats")
async def crawl_queue_stats(
    job_id: str | None = None, _: Principal = Depends(require(Permission.CRAWL_READ))
) -> dict:
    async with db.session() as session:
        jid = uuid.UUID(job_id) if job_id else None
        return await CrawlRepository(session).queue_stats(jid)


# ---- Index & analytics ----
@app.get("/api/v1/admin/index/stats")
async def index_stats(_: Principal = Depends(require(Permission.ANALYTICS_READ))) -> dict:
    async with db.session() as session:
        return {
            "documents": await DocumentRepository(session).count(),
            "postings": await IndexRepository(session).posting_count(),
            "terms": await TermStatsRepository(session).count(),
        }


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@app.get("/api/v1/admin/analytics/queries")
async def query_analytics(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(10, ge=1, le=100),
    _: Principal = Depends(require(Permission.ANALYTICS_READ)),
) -> dict:
    start, end = _parse_date(start_date), _parse_date(end_date)
    async with db.session() as session:
        repo = AnalyticsRepository(session)
        latency = await repo.latency_samples(start, end)
        return {
            "range": {"start": start_date, "end": end_date},
            "total_queries": await repo.query_volume(start, end),
            "top_queries": await repo.top_queries(start, end, limit),
            "zero_result_queries": await repo.zero_result_queries(start, end, limit),
            "click_through_rate": await repo.click_through_rate(start, end),
            "latency": {
                "p50": percentile(latency, 50),
                "p95": percentile(latency, 95),
                "p99": percentile(latency, 99),
                "samples": len(latency),
            },
        }


# ---- Settings ----
@app.get("/api/v1/admin/settings")
async def list_settings(
    category: str | None = None, _: Principal = Depends(require(Permission.SETTINGS_READ))
) -> list[dict]:
    async with db.session() as session:
        rows = await AdminRepository(session).list_settings(category)
        return [
            {"key": s.key, "value": s.value, "description": s.description, "category": s.category}
            for s in rows
        ]


@app.put("/api/v1/admin/settings/{key}")
async def update_setting(
    key: str,
    payload: SettingUpdate,
    request: Request,
    principal: Principal = Depends(require(Permission.SETTINGS_WRITE)),
) -> dict:
    if key not in ALLOWED_SETTING_KEYS:
        raise ValidationError("Setting not allowlisted", details={"allowed": sorted(ALLOWED_SETTING_KEYS)})
    async with db.session() as session:
        repo = AdminRepository(session)
        setting = await repo.upsert_setting(
            key=key,
            value=payload.value,
            description=payload.description,
            updated_by=uuid.UUID(principal.user_id),
        )
        await repo.audit(
            action="settings.update",
            actor_id=uuid.UUID(principal.user_id),
            actor_role=principal.role,
            target_type="setting",
            target_id=key,
            request_id=getattr(request.state, "request_id", None),
        )
        return {"key": setting.key, "value": setting.value}


# ---- API keys ----
@app.get("/api/v1/admin/api-keys")
async def list_api_keys(_: Principal = Depends(require(Permission.APIKEY_MANAGE))) -> list[dict]:
    async with db.session() as session:
        keys = await AdminRepository(session).list_api_keys()
        return [
            {
                "id": str(k.id),
                "name": k.name,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "rate_limit": k.rate_limit,
                "created_at": k.created_at.isoformat() if k.created_at else None,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            }
            for k in keys
        ]


@app.post("/api/v1/admin/api-keys", status_code=201)
async def create_api_key(
    payload: APIKeyCreate,
    request: Request,
    principal: Principal = Depends(require(Permission.APIKEY_MANAGE)),
) -> dict:
    plaintext, key_hash, prefix = generate_api_key()
    async with db.session() as session:
        repo = AdminRepository(session)
        key = await repo.create_api_key(
            name=payload.name,
            key_hash=key_hash,
            key_prefix=prefix,
            user_id=uuid.UUID(principal.user_id),
            rate_limit=payload.rate_limit,
        )
        await repo.audit(
            action="apikey.create",
            actor_id=uuid.UUID(principal.user_id),
            actor_role=principal.role,
            target_type="api_key",
            target_id=str(key.id),
            request_id=getattr(request.state, "request_id", None),
        )
        # Plaintext returned ONLY on creation.
        return {"id": str(key.id), "name": key.name, "key": plaintext, "key_prefix": prefix}


@app.delete("/api/v1/admin/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    request: Request,
    principal: Principal = Depends(require(Permission.APIKEY_MANAGE)),
) -> None:
    async with db.session() as session:
        repo = AdminRepository(session)
        ok = await repo.revoke_api_key(uuid.UUID(key_id))
        if not ok:
            raise NotFoundError("API key not found")
        await repo.audit(
            action="apikey.revoke",
            actor_id=uuid.UUID(principal.user_id),
            actor_role=principal.role,
            target_type="api_key",
            target_id=key_id,
            request_id=getattr(request.state, "request_id", None),
        )


@app.get("/api/v1/admin/audit")
async def list_audit(
    limit: int = Query(50, ge=1, le=200), _: Principal = Depends(require(Permission.AUDIT_READ))
) -> list[dict]:
    async with db.session() as session:
        events = await AdminRepository(session).list_audit(limit)
        return [
            {
                "id": str(e.id),
                "action": e.action,
                "actor_role": e.actor_role,
                "target_type": e.target_type,
                "target_id": e.target_id,
                "outcome": e.outcome,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
