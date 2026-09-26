"""Crawl job and URL frontier models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from luna_shared.database import Base
from luna_shared.types import GUID, json_type, string_list


class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    seed_urls: Mapped[list[str]] = mapped_column(string_list(), default=list, nullable=False)
    allowed_domains: Mapped[list[str]] = mapped_column(string_list(), default=list)
    blocked_domains: Mapped[list[str]] = mapped_column(string_list(), default=list)
    max_depth: Mapped[int] = mapped_column(Integer, default=3)
    max_pages: Mapped[int] = mapped_column(Integer, default=10000)
    max_pages_per_domain: Mapped[int] = mapped_column(Integer, default=1000)
    crawl_delay: Mapped[float] = mapped_column(Float, default=5.0)
    respect_robots_txt: Mapped[bool] = mapped_column(Boolean, default=True)
    user_agent: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=CrawlStatus.PENDING.value, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_failed: Mapped[int] = mapped_column(Integer, default=0)
    bytes_downloaded: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    documents: Mapped[list[Document]] = relationship(back_populates="crawl_job")  # noqa: F821
    queue_items: Mapped[list[CrawlQueue]] = relationship(
        back_populates="crawl_job", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_crawl_jobs_status_priority", "status", "priority"),)


class CrawlQueue(Base):
    __tablename__ = "crawl_queue"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    crawl_job_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    normalized_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    depth: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    crawl_job: Mapped[CrawlJob] = relationship(back_populates="queue_items")

    __table_args__ = (
        Index("ix_crawl_queue_domain_status", "domain", "status"),
        Index("ix_crawl_queue_priority_scheduled", "priority", "scheduled_at"),
        Index("ix_crawl_queue_unique_url", "crawl_job_id", "normalized_url", unique=True),
    )


__all__ = ["CrawlJob", "CrawlQueue", "CrawlStatus"]
