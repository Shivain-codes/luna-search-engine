"""Versioned message envelope for RabbitMQ transport."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Envelope(BaseModel):
    """Standard event envelope shared by producers and consumers."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    schema_version: int = 1
    occurred_at: str = Field(default_factory=_now)
    correlation_id: str | None = None
    idempotency_key: str
    payload: dict[str, Any]

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_bytes(cls, data: bytes | str) -> Envelope:
        if isinstance(data, bytes):
            data = data.decode()
        return cls.model_validate_json(data)


__all__ = ["Envelope"]
