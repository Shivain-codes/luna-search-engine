"""Shared health / readiness helpers."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

DependencyCheck = Callable[[], Awaitable[bool]]


class HealthRegistry:
    """Collects named async dependency probes for readiness reporting."""

    def __init__(self, service: str, version: str = "0.1.0") -> None:
        self.service = service
        self.version = version
        self._checks: dict[str, DependencyCheck] = {}

    def register(self, name: str, check: DependencyCheck) -> None:
        self._checks[name] = check

    async def _probe(self, name: str, check: DependencyCheck) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            ok = await check()
        except Exception:
            ok = False
        return {
            "status": "ready" if ok else "unavailable",
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    async def readiness(self, request_id: str | None = None) -> tuple[dict[str, Any], bool]:
        deps: dict[str, Any] = {}
        all_ok = True
        for name, check in self._checks.items():
            result = await self._probe(name, check)
            deps[name] = result
            all_ok = all_ok and result["status"] == "ready"
        body = {
            "service": self.service,
            "status": "ready" if all_ok else "degraded",
            "version": self.version,
            "dependencies": deps,
            "request_id": request_id,
        }
        return body, all_ok

    def liveness(self, request_id: str | None = None) -> dict[str, Any]:
        return {
            "service": self.service,
            "status": "alive",
            "version": self.version,
            "request_id": request_id,
        }


__all__ = ["HealthRegistry"]
