"""Initial schema — created directly from the SQLAlchemy models.

Building the schema from ``Base.metadata`` keeps migrations and models in
lock-step and works identically on PostgreSQL and SQLite.

Revision ID: 001
Revises:
Create Date: 2024-01-15 10:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from luna_shared.database import Base
import luna_shared.models  # noqa: F401  (register all tables)

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Deterministic creation order (respect foreign keys).
_TABLE_ORDER = [
    "crawl_jobs",
    "admin_users",
    "documents",
    "crawl_queue",
    "inverted_index",
    "term_stats",
    "query_logs",
    "click_logs",
    "api_keys",
    "settings",
    "audit_events",
]


def upgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata
    tables = [metadata.tables[name] for name in _TABLE_ORDER if name in metadata.tables]
    metadata.create_all(bind=bind, tables=tables, checkfirst=True)

    if bind.dialect.name == "postgresql":
        op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_documents_title_trgm "
            "ON documents USING gin (title gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_query_logs_normalized_query_trgm "
            "ON query_logs USING gin (normalized_query gin_trgm_ops)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    metadata = Base.metadata
    tables = [metadata.tables[name] for name in reversed(_TABLE_ORDER) if name in metadata.tables]
    metadata.drop_all(bind=bind, tables=tables, checkfirst=True)
