"""Role-based access control matrix."""

from __future__ import annotations

from enum import Enum


class Permission(str, Enum):
    ANALYTICS_READ = "analytics:read"
    CRAWL_READ = "crawl:read"
    CRAWL_WRITE = "crawl:write"
    SETTINGS_READ = "settings:read"
    SETTINGS_WRITE = "settings:write"
    APIKEY_MANAGE = "apikey:manage"
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"


_ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "viewer": {
        Permission.ANALYTICS_READ,
        Permission.CRAWL_READ,
        Permission.SETTINGS_READ,
    },
    "operator": {
        Permission.ANALYTICS_READ,
        Permission.CRAWL_READ,
        Permission.CRAWL_WRITE,
        Permission.SETTINGS_READ,
        Permission.SETTINGS_WRITE,
    },
    "admin": set(Permission),
}


def role_permissions(role: str) -> set[Permission]:
    return _ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: Permission) -> bool:
    return permission in role_permissions(role)


__all__ = ["Permission", "has_permission", "role_permissions"]
