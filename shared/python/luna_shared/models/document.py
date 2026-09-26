"""Document model for indexed web pages."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from luna_shared.database import Base
from luna_shared.types import GUID, Score, json_type, string_list


class Document(Base):
    """A crawled and indexed web document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False, index=True)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headings: Mapped[dict] = mapped_column(json_type(), default=dict)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    images: Mapped[list[str]] = mapped_column(string_list(), default=list)
    content_type: Mapped[str] = mapped_column(String(100), default="text/html")
    content_length: Mapped[int] = mapped_column(Integer, default=0)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status_code: Mapped[int] = mapped_column(Integer, default=200)
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    crawl_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("crawl_jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    outlinks: Mapped[list[str]] = mapped_column(string_list(), default=list)
    inlinks_count: Mapped[int] = mapped_column(Integer, default=0)
    pagerank: Mapped[float] = mapped_column(Score, default=0.0, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    crawl_job: Mapped[CrawlJob] = relationship(back_populates="documents")  # noqa: F821

    __table_args__ = (
        Index("ix_documents_pagerank_desc", sa.desc("pagerank")),
        Index("ix_documents_crawled_desc", sa.desc("crawled_at")),
    )


__all__ = ["Document"]
