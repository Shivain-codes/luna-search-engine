"""Authentication primitives: password hashing, JWT, and API keys.

Passwords use scrypt from the standard library so no native bcrypt build
is required. Tokens are signed JWTs carrying subject, role, type, issuer,
audience, and expiry claims.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from luna_shared.config import get_settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEYLEN = 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEYLEN
    )
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, hash_hex = stored.split("$", 2)
        if scheme != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.scrypt(
            password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEYLEN
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# Backwards-compatible alias
get_password_hash = hash_password


def _base_claims(subject: str, role: str, token_type: str) -> dict[str, Any]:
    settings = get_settings()
    return {
        "sub": subject,
        "role": role,
        "type": token_type,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": datetime.now(UTC),
    }


def create_access_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    claims = _base_claims(subject, role, "access")
    delta = expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    claims["exp"] = datetime.now(UTC) + delta
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, role: str, expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    claims = _base_claims(subject, role, "refresh")
    delta = expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days)
    claims["exp"] = datetime.now(UTC) + delta
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str | None = None) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    return payload


def generate_api_key() -> tuple[str, str, str]:
    """Return ``(plaintext, key_hash, prefix)`` for a new API key."""
    key = f"nxs_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, key_hash, key[:12]


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_api_key",
    "get_password_hash",
    "hash_api_key",
    "hash_password",
    "verify_password",
]
