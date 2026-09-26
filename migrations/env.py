"""Alembic environment (synchronous engine, models as metadata source)."""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make luna_shared importable.
sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))

from luna_shared.config import sync_database_url  # noqa: E402
from luna_shared.models import Base  # noqa: E402
import luna_shared.models  # noqa: E402,F401  (register all tables)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    import os

    raw = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    return sync_database_url(raw)


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
