"""Ensure workspace packages are importable in tests without editable installs."""

import sys
from pathlib import Path

_ROOT = Path(__file__).parent
_PATHS = [
    _ROOT / "shared" / "python",
    _ROOT / "services" / "search-api" / "src",
    _ROOT / "services" / "ranker" / "src",
    _ROOT / "services" / "indexer" / "src",
    _ROOT / "services" / "crawler" / "src",
    _ROOT / "services" / "admin-api" / "src",
    _ROOT / "services" / "api-gateway" / "src",
]
for _p in _PATHS:
    sp = str(_p)
    if sp not in sys.path:
        sys.path.insert(0, sp)
