"""Async database engine and session management (SQLite + PostgreSQL)."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _normalize_async_url(url: str) -> str:
    """Ensure the URL uses an async driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


class Database:
    """Async database connection manager."""

    def __init__(self, database_url: str | None = None) -> None:
        raw = database_url or os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nexus.db")
        self.database_url = _normalize_async_url(raw)
        self.is_sqlite = self.database_url.startswith("sqlite")
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def is_memory(self) -> bool:
        return self.is_sqlite and (":memory:" in self.database_url or self.database_url.endswith("://"))

    def connect(self, pool_size: int = 10, max_overflow: int = 20) -> None:
        if self.engine is not None:
            return
        kwargs: dict = {"echo": os.getenv("SQL_ECHO") == "true"}
        if self.is_memory:
            # A single shared connection so the in-memory schema persists
            # across sessions within the process.
            from sqlalchemy.pool import StaticPool

            kwargs.update(poolclass=StaticPool, connect_args={"check_same_thread": False})
        elif self.is_sqlite:
            # File SQLite: use NullPool so connections are not reused across
            # event loops (important for async test isolation).
            from sqlalchemy.pool import NullPool

            kwargs.update(poolclass=NullPool)
        else:
            kwargs.update(
                pool_pre_ping=True, pool_size=pool_size, max_overflow=max_overflow, pool_recycle=3600
            )
        self.engine = create_async_engine(self.database_url, **kwargs)
        if self.is_sqlite:
            @event.listens_for(self.engine.sync_engine, "connect")
            def _fk_pragma(dbapi_conn, _rec) -> None:  # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
        )

    async def disconnect(self) -> None:
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        if not self.session_factory:
            self.connect()
        assert self.session_factory is not None
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def create_all(self) -> None:
        if not self.engine:
            self.connect()
        assert self.engine is not None
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def ping(self) -> bool:
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


db = Database()


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with db.session() as session:
        yield session


async def init_db(database_url: str | None = None, create: bool = True) -> None:
    global db
    # If an explicit URL is given and differs from the current global, rebuild.
    if database_url and _normalize_async_url(database_url) != db.database_url:
        db = Database(database_url)
    db.connect()
    if create and db.is_sqlite:
        await db.create_all()


async def close_db() -> None:
    await db.disconnect()


__all__ = ["Base", "Database", "close_db", "db", "get_db", "init_db"]
