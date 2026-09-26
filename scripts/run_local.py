"""Run all backend services locally without Docker (SQLite + in-memory).

Starts each FastAPI service with uvicorn in its own process. Uses the shared
SQLite database file and in-memory cache/broker defaults, so no external
infrastructure is required. Press Ctrl-C to stop everything.

Usage:
    uv run python scripts/run_local.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# database file shared by all services
DB_PATH = ROOT / "nexus.db"

SERVICES = [
    ("ranker", "ranker.main:app", 8004),
    ("search-api", "search_api.main:app", 8001),
    ("indexer", "indexer.main:app", 8003),
    ("crawler", "crawler.main:app", 8002),
    ("admin-api", "admin_api.main:app", 8005),
    ("api-gateway", "api_gateway.main:app", 8000),
]


def main() -> int:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")
    env.setdefault("RANKING_API_URL", "http://localhost:8004")
    env.setdefault("SEARCH_API_URL", "http://localhost:8001")
    env.setdefault("ADMIN_API_URL", "http://localhost:8005")

    procs: list[subprocess.Popen] = []
    print("Starting Luna services (SQLite + in-memory infra)...")
    for name, target, port in SERVICES:
        proc = subprocess.Popen(
            ["uvicorn", target, "--host", "0.0.0.0", "--port", str(port)],
            env=env,
        )
        procs.append(proc)
        print(f"  {name:12} http://localhost:{port}")
        time.sleep(0.5)

    print("\nGateway:  http://localhost:8000")
    print("Press Ctrl-C to stop.\n")

    def shutdown(*_):
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    for p in procs:
        p.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
