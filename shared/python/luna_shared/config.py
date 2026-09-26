"""Shared configuration for Luna services.

Configuration precedence: typed code defaults < environment variables.
YAML policy files (crawler/ranking) are loaded separately by the services
that own them. Secrets are never emitted by :meth:`Settings.effective`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SECRET_KEYS = {"jwt_secret", "database_url", "rabbitmq_url", "redis_url", "nemotron_api_key"}
_DEV_SECRET_DEFAULTS = {"changeme", "your-super-secret-jwt-key-change-in-production"}


class Settings(BaseSettings):
    """Base settings shared by all services."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    service_name: str = "luna-service"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Data stores. Default to local SQLite / in-memory so the stack runs
    # without external infrastructure; override via env for Postgres etc.
    database_url: str = Field(default="sqlite+aiosqlite:///./nexus.db")
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    redis_url: str = Field(default="memory://")
    rabbitmq_url: str = Field(default="memory://")

    # HTTP
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    request_timeout_seconds: float = Field(default=30.0)

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://localhost:8000"])

    # JWT
    jwt_secret: str = Field(default="changeme")
    jwt_algorithm: str = Field(default="HS256")
    jwt_issuer: str = Field(default="nexussearch")
    jwt_audience: str = Field(default="nexussearch")
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # Search
    search_default_per_page: int = Field(default=10)
    search_max_per_page: int = Field(default=50)
    search_cache_ttl: int = Field(default=300)
    suggest_min_length: int = Field(default=2)
    suggest_max_limit: int = Field(default=20)

    # BM25 / PageRank defaults (may be overridden by ranking.yaml)
    bm25_k1: float = Field(default=1.5)
    bm25_b: float = Field(default=0.75)
    pagerank_damping: float = Field(default=0.85)
    pagerank_iterations: int = Field(default=100)
    pagerank_tolerance: float = Field(default=1e-6)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def validate_for_startup(self) -> None:
        """Reject unsafe configuration before a service is marked ready."""
        if self.jwt_access_token_expire_minutes <= 0:
            raise ValueError("jwt_access_token_expire_minutes must be positive")
        if self.rate_limit_requests <= 0 or self.rate_limit_window <= 0:
            raise ValueError("rate limit values must be positive")
        if self.search_max_per_page < self.search_default_per_page:
            raise ValueError("search_max_per_page must be >= search_default_per_page")
        if not (0.0 <= self.bm25_b <= 1.0):
            raise ValueError("bm25_b must be within [0, 1]")
        if self.is_production and self.jwt_secret in _DEV_SECRET_DEFAULTS:
            raise ValueError(
                "JWT_SECRET uses a development-only default; set a strong secret in production"
            )

    def effective(self) -> dict[str, Any]:
        """Return effective configuration with secrets redacted."""
        data = self.model_dump()
        for key in _SECRET_KEYS:
            if key in data and data[key]:
                data[key] = "[redacted]"
        return data


class SearchAPISettings(Settings):
    service_name: str = "search-api"
    api_port: int = 8001
    ranker_url: str = Field(default="http://localhost:8004", alias="RANKING_API_URL")
    # Never hardcode secrets. Provide via the NEMOTRON_API_KEY environment
    # variable (see .env.example). Empty default disables AI summaries.
    nemotron_api_key: str = Field(default="", alias="NEMOTRON_API_KEY")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False,
        extra="ignore", populate_by_name=True,
    )


class RankerSettings(Settings):
    service_name: str = "ranker"
    api_port: int = 8004


class IndexerSettings(Settings):
    service_name: str = "indexer"
    api_port: int = 8003


class CrawlerSettings(Settings):
    service_name: str = "crawler"
    api_port: int = 8002
    crawler_config_path: str = Field(default="config/crawler.yaml")


class AdminAPISettings(Settings):
    service_name: str = "admin-api"
    api_port: int = 8005


class APIGatewaySettings(Settings):
    service_name: str = "api-gateway"
    api_port: int = 8000
    search_api_url: str = Field(default="http://localhost:8001", alias="SEARCH_API_URL")
    admin_api_url: str = Field(default="http://localhost:8005", alias="ADMIN_API_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False,
        extra="ignore", populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sync_database_url(url: str | None = None) -> str:
    """Return a synchronous SQLAlchemy URL for the configured database."""
    url = url or os.getenv("DATABASE_URL") or get_settings().database_url
    return url.replace("+asyncpg", "").replace("+aiosqlite", "")


__all__ = [
    "AdminAPISettings",
    "APIGatewaySettings",
    "CrawlerSettings",
    "IndexerSettings",
    "RankerSettings",
    "SearchAPISettings",
    "Settings",
    "get_settings",
    "sync_database_url",
]
