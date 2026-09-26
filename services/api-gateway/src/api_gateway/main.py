"""API Gateway: public search ingress + authenticated admin forwarding."""

from __future__ import annotations
# ... existing imports ...
from contextlib import asynccontextmanager
import asyncio
import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect

from fastapi.responses import JSONResponse, Response
from luna_shared.app import create_app
from luna_shared.cache import get_cache

from luna_shared.config import APIGatewaySettings
from luna_shared.errors import DependencyError, RateLimitError, TimeoutError
from luna_shared.logging import request_id_var
from luna_shared.security import get_rate_limiter

settings = APIGatewaySettings()
cache = get_cache()
rate_limiter = get_rate_limiter()

# Per-endpoint-prefix rate limits (requests per window)
RATE_LIMITS = {
    "/api/v1/search": (settings.rate_limit_requests, settings.rate_limit_window),
    "/api/v1/suggest": (settings.rate_limit_requests * 3, settings.rate_limit_window),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_for_startup()
    await cache.connect()
    yield
    await cache.close()


app, health = create_app(settings, title="Luna API Gateway", lifespan=lifespan)
health.register("redis", cache.ping)


async def _search_ready() -> bool:
    return await _ping(settings.search_api_url)


async def _admin_ready() -> bool:
    return await _ping(settings.admin_api_url)


async def _ping(base: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{base}/health/live")
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


health.register("search-api", _search_ready)
health.register("admin-api", _admin_ready)


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


async def _forward(request: Request, base_url: str, path: str) -> Response:
    rid = request_id_var.get()
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    if rid:
        headers["X-Request-ID"] = rid
    body = await request.body()
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.request(
                method=request.method,
                url=f"{base_url}{path}",
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )
    except httpx.TimeoutException as exc:
        raise TimeoutError("Downstream timed out") from exc
    except httpx.HTTPError as exc:
        raise DependencyError("Downstream unavailable") from exc

    media = resp.headers.get("content-type", "application/json")
    return Response(content=resp.content, status_code=resp.status_code, media_type=media)


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


# Public routes -> Search API
@app.api_route("/api/v1/search", methods=["GET"])
async def search(request: Request) -> Response:
    return await _forward(request, settings.search_api_url, "/api/v1/search")


@app.api_route("/api/v1/suggest", methods=["GET"])
async def suggest(request: Request) -> Response:
    return await _forward(request, settings.search_api_url, "/api/v1/suggest")


@app.api_route("/api/v1/clicks", methods=["POST"])
async def clicks(request: Request) -> Response:
    return await _forward(request, settings.search_api_url, "/api/v1/clicks")


@app.api_route("/api/v1/documents/{doc_id}", methods=["GET"])
async def document(request: Request, doc_id: str) -> Response:
    return await _forward(request, settings.search_api_url, f"/api/v1/documents/{doc_id}")


# Auth + admin routes -> Admin API
@app.api_route("/api/v1/auth/{path:path}", methods=["POST"])
async def auth(request: Request, path: str) -> Response:
    return await _forward(request, settings.admin_api_url, f"/api/v1/auth/{path}")


@app.websocket("/api/v1/admin/ws/analytics")
async def analytics_ws(websocket: WebSocket):
    await websocket.accept()
    cache = get_cache()
    pubsub = await cache.subscribe("analytics:search_events")

    if pubsub is None:
        # Memory backend doesn't support pubsub
        try:
            while True:
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass
        return

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("analytics:search_events")


@app.api_route(
    "/api/v1/admin/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def admin(request: Request, path: str) -> Response:
    return await _forward(request, settings.admin_api_url, f"/api/v1/admin/{path}")



def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
