"""Unified Cloud API: Combines Gateway, Search, Admin, and Ranker into one process."""

from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, JSONResponse
from fastapi.responses import Response

from luna_shared.app import create_app
from luna_shared.cache import get_cache
from luna_shared.database import close_db, db, init_db
from luna_shared.config import APIGatewaySettings
from luna_shared.errors import RateLimitError
from luna_shared.logging import request_id_var
from luna_shared.security import get_rate_limiter

# Import the sub-apps from existing services
from search_api.main import app as search_app
from admin_api.main import app as admin_app
from ranker.main import app as ranker_app

settings = APIGatewaySettings()
cache = get_cache()
rate_limiter = get_rate_limiter()

# Per-endpoint-prefix rate limits
RATE_LIMITS = {
    "/api/v1/search": (settings.rate_limit_requests, settings.rate_limit_window),
    "/api/v1/suggest": (settings.rate_limit_requests * 3, settings.rate_limit_window),
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Combined startup: Initialize DB and Cache once for the whole monolith
    await init_db()
    await cache.connect()
    yield
    # Combined shutdown
    await cache.close()
    await close_db()

# Create the main unified app
app, health = create_app(settings, title="Luna Cloud API", lifespan=lifespan)

# Mount the sub-apps.
# Because they are mounted at "/", they will handle their own internal routes
# (e.g., /api/v1/search) without needing HTTP forwarding.
app.mount("/", search_app)
app.mount("/", admin_app)
app.mount("/", ranker_app)

async def _enforce_rate_limit(request: Request) -> None:
    if not settings.rate_limit_enabled:
        return
    for prefix, (limit, window) in RATE_LIMITS.items():
        if request.url.path.startswith(prefix):
            client_ip = request.client.host if request.client else "unknown"
            allowed, _count = await rate_limiter.check(
                f"{prefix}:{client_ip}", limit, window
            )
            if not allowed:
                raise RateLimitError("Rate limit exceeded")
            return

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        await _enforce_rate_limit(request)
    except RateLimitError as exc:
        rid = request_id_var.get()
        return JSONResponse(
            status_code=429,
            content={"error": {"code": exc.code, "message": exc.message, "details": {}, "request_id": rid}},
        )
    return await call_next(request)

# Health checks for the monolith
health.register("postgres", db.ping)
health.register("redis", cache.ping)

def run() -> None:
    import uvicorn
    # Use port 8000 as the single entry point for the cloud
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    run()
