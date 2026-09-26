"""FastAPI application factory with shared middleware and health routes."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from luna_shared.config import Settings
from luna_shared.errors import install_error_handlers
from luna_shared.health import HealthRegistry
from luna_shared.logging import RequestContextMiddleware, configure_logging


def create_app(settings: Settings, *, title: str, lifespan: Any = None) -> tuple[FastAPI, HealthRegistry]:
    """Create a configured FastAPI app plus a health registry."""
    configure_logging(settings.log_level)
    app = FastAPI(title=title, version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    health = HealthRegistry(settings.service_name)

    @app.get("/health/live")
    async def _live(request: Request) -> dict:
        return health.liveness(getattr(request.state, "request_id", None))

    @app.get("/health/ready")
    async def _ready(request: Request) -> JSONResponse:
        body, ok = await health.readiness(getattr(request.state, "request_id", None))
        return JSONResponse(status_code=200 if ok else 503, content=body)

    @app.get("/health")
    async def _health(request: Request) -> JSONResponse:
        body, ok = await health.readiness(getattr(request.state, "request_id", None))
        body["status"] = "healthy" if ok else "degraded"
        return JSONResponse(status_code=200, content=body)

    return app, health


__all__ = ["create_app"]
