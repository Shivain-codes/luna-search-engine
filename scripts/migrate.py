"""Run database migrations (used by the compose migration gate).

Waits for the database to accept connections, then runs
``alembic upgrade head``. Safe to run repeatedly.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from luna_shared.config import sync_database_url
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent.parent


def wait_for_db(url: str, attempts: int = 30, delay: float = 2.0) -> None:
    engine = create_engine(url)
    for i in range(1, attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"database reachable after {i} attempt(s)")
            engine.dispose()
            return
        except Exception as exc:  # noqa: BLE001
            print(f"waiting for database ({i}/{attempts}): {exc}")
            time.sleep(delay)
    engine.dispose()
    raise SystemExit("database did not become reachable in time")


def main() -> int:
    url = sync_database_url(os.getenv("DATABASE_URL"))
    if url.startswith("postgresql"):
        wait_for_db(url)
    cfg = Config(str(ROOT / "migrations" / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(cfg, "head")
    print("migrations applied: head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
