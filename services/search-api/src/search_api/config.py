"""Search API configuration."""

from __future__ import annotations

from luna_shared.config import SearchAPISettings


def get_settings() -> SearchAPISettings:
    return SearchAPISettings()


__all__ = ["get_settings"]
