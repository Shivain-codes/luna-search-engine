"""Auth dependencies and RBAC enforcement for the Admin API."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from luna_shared.database import db
from luna_shared.repositories import AdminRepository
from luna_shared.errors import AuthenticationError, AuthorizationError
from luna_shared.security import Permission, decode_token, has_permission, hash_api_key

_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: str
    role: str


async def current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    # 1. Try JWT Bearer token
    if credentials:
        payload = decode_token(credentials.credentials, expected_type="access")
        if payload:
            return Principal(user_id=payload["sub"], role=payload.get("role", "viewer"))

    # 2. Try API Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        async with db.session() as session:
            repo = AdminRepository(session)
            key_hash = hash_api_key(api_key)
            key_record = await repo.get_api_key_by_hash(key_hash)
            if key_record and key_record.is_active:
                return Principal(user_id=str(key_record.user_id), role="admin") # API keys get admin for simplicity

    raise AuthenticationError("Authentication required (JWT or X-API-Key)")


def require(permission: Permission):
    async def _dep(principal: Principal = Depends(current_principal)) -> Principal:
        if not has_permission(principal.role, permission):
            raise AuthorizationError("Insufficient privileges")
        return principal

    return _dep


__all__ = ["Principal", "current_principal", "require"]
