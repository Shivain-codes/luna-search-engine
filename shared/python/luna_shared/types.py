"""Portable SQLAlchemy column types.

Luna runs on PostgreSQL in production and on SQLite for local
development and tests. These type aliases pick the best native
representation per dialect while keeping one Python-level type.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

#: Primary key / foreign key identifier type.
#: Renders as native ``UUID`` on PostgreSQL and ``CHAR(32)`` elsewhere.
GUID = sa.Uuid(as_uuid=True)


def json_type() -> sa.types.TypeEngine:
    """JSON document column, using ``JSONB`` on PostgreSQL."""
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def string_list() -> sa.types.TypeEngine:
    """List of strings, stored as JSON for dialect portability."""
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def int_list() -> sa.types.TypeEngine:
    """List of integers (used for token positions)."""
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


#: Floating point score column.
Score = sa.Float()

__all__ = ["GUID", "Score", "int_list", "json_type", "string_list"]
