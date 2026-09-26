"""Inverted index and term statistics models."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from luna_shared.database import Base
from luna_shared.types import GUID, Score, int_list


class InvertedIndex(Base):
    """Postings: term -> document mapping with positions per field."""

    __tablename__ = "inverted_index"

    term: Mapped[str] = mapped_column(String(256), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    field: Mapped[str] = mapped_column(String(32), primary_key=True, default="body")
    shard_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    positions: Mapped[list[int]] = mapped_column(int_list(), default=list, nullable=False)
    tf_idf: Mapped[float] = mapped_column(Score, default=0.0, nullable=False)

    __table_args__ = (
        Index("ix_inverted_index_document_id", "document_id"),
        Index("ix_inverted_index_term_field", "term", "field"),
        Index("ix_inverted_index_shard_term", "shard_id", "term"),
        Index("ix_inverted_index_tf_idf_desc", sa.desc("tf_idf")),
    )


class TermStats(Base):
    """Global term statistics for IDF calculation."""

    __tablename__ = "term_stats"

    term: Mapped[str] = mapped_column(String(256), primary_key=True)
    document_frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_frequency: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    idf: Mapped[float] = mapped_column(Score, default=0.0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


__all__ = ["InvertedIndex", "TermStats"]
