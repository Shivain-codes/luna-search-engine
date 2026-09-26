"""Shared test fixtures: an isolated file-backed SQLite database."""

import os
import tempfile
import uuid

import pytest_asyncio


@pytest_asyncio.fixture
async def database():
    """A fresh migrated SQLite database per test.

    Services import the ``db`` singleton by name at import time, so we mutate
    the existing global object in place (rebind its engine to the test URL)
    rather than replacing it. This keeps every module's ``db`` reference valid.
    """
    import luna_shared.database as dbmod

    path = os.path.join(tempfile.gettempdir(), f"nexus_test_{uuid.uuid4().hex}.db")
    url = f"sqlite+aiosqlite:///{path}"
    prev_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url

    db = dbmod.db
    # Reset the singleton to point at the isolated test database.
    await db.disconnect()
    db.database_url = url
    db.is_sqlite = True
    db.connect()
    await db.create_all()

    try:
        yield db
    finally:
        await db.disconnect()
        if prev_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = prev_env
        if os.path.exists(path):
            os.remove(path)
