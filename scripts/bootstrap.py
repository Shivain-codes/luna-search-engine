"""Bootstrap the local dev environment.

uv's strict editable finder is unreliable on some Python versions, so we
write a ``sitecustomize.py`` into the active virtualenv's site-packages that
puts the shared library and each service ``src`` directory on ``sys.path``.
This runs automatically at interpreter startup and survives ``uv sync``.

Usage:
    uv run python scripts/bootstrap.py
"""

from __future__ import annotations

import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATHS = [
    ROOT / "shared" / "python",
    ROOT / "services" / "search-api" / "src",
    ROOT / "services" / "ranker" / "src",
    ROOT / "services" / "indexer" / "src",
    ROOT / "services" / "crawler" / "src",
    ROOT / "services" / "admin-api" / "src",
    ROOT / "services" / "api-gateway" / "src",
]


def main() -> int:
    site_packages = Path(site.getsitepackages()[0])
    content = "import sys\n"
    for p in PATHS:
        content += f'_p = {str(p)!r}\n'
        content += "if _p not in sys.path:\n    sys.path.insert(0, _p)\n"
    target = site_packages / "sitecustomize.py"
    target.write_text(content)
    print(f"wrote {target}")
    # Verify importability.
    for p in PATHS:
        sys.path.insert(0, str(p))
    import importlib

    for mod in [
        "luna_shared",
        "search_api.main",
        "ranker.main",
        "indexer.main",
        "crawler.main",
        "admin_api.main",
        "api_gateway.main",
    ]:
        importlib.import_module(mod)
    print("all packages import OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
