"""Foundation validation: imports, migrations, and app wiring.

Verifies the repository is in a runnable state without requiring Docker or
external infrastructure. Exits non-zero if any check fails.

Usage:
    uv run python scripts/validate_foundation.py
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile


def check_imports() -> list[str]:
    failures = []
    modules = [
        "luna_shared",
        "luna_shared.ir",
        "luna_shared.repositories",
        "search_api.main",
        "ranker.main",
        "indexer.main",
        "crawler.main",
        "admin_api.main",
        "api_gateway.main",
    ]
    for mod in modules:
        try:
            importlib.import_module(mod)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"import {mod}: {exc}")
    return failures


def check_migration() -> list[str]:
    tmp = os.path.join(tempfile.gettempdir(), "nexus_foundation.db")
    if os.path.exists(tmp):
        os.remove(tmp)
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp}"
    try:
        from pathlib import Path

        from alembic import command
        from alembic.config import Config

        root = Path(__file__).resolve().parent.parent
        cfg = Config(str(root / "migrations" / "alembic.ini"))
        cfg.set_main_option("script_location", str(root / "migrations"))
        command.upgrade(cfg, "head")
    except Exception as exc:  # noqa: BLE001
        return [f"migration: {exc}"]
    import sqlite3

    conn = sqlite3.connect(tmp)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    required = {"documents", "inverted_index", "term_stats", "crawl_jobs", "admin_users"}
    missing = required - tables
    return [f"missing tables: {missing}"] if missing else []


def check_apps() -> list[str]:
    failures = []
    for mod_name in [
        "search_api.main",
        "ranker.main",
        "indexer.main",
        "crawler.main",
        "admin_api.main",
        "api_gateway.main",
    ]:
        mod = importlib.import_module(mod_name)
        if not hasattr(mod, "app"):
            failures.append(f"{mod_name} has no `app`")
    return failures


def main() -> int:
    all_failures: list[str] = []
    print("[1/3] imports...")
    all_failures += check_imports()
    print("[2/3] migrations...")
    all_failures += check_migration()
    print("[3/3] app wiring...")
    all_failures += check_apps()

    if all_failures:
        print("\nFOUNDATION FAILED:")
        for f in all_failures:
            print(f"  - {f}")
        return 1
    print("\nFOUNDATION OK: imports, migrations, and app wiring all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
