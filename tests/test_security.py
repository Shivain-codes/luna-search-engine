"""Unit tests for auth, JWT, RBAC, and API keys."""


from luna_shared.security import (
    Permission,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    has_permission,
    hash_api_key,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pw")
    assert verify_password("s3cret-pw", h)
    assert not verify_password("wrong", h)


def test_password_hash_is_salted():
    assert hash_password("same") != hash_password("same")


def test_access_token_roundtrip():
    token = create_access_token("user-1", "admin")
    payload = decode_token(token, expected_type="access")
    assert payload is not None
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"


def test_token_type_enforced():
    access = create_access_token("u", "viewer")
    assert decode_token(access, expected_type="refresh") is None
    refresh = create_refresh_token("u", "viewer")
    assert decode_token(refresh, expected_type="access") is None


def test_tampered_token_rejected():
    token = create_access_token("u", "admin")
    assert decode_token(token[:-3] + "xxx") is None


def test_rbac_matrix():
    assert has_permission("admin", Permission.USER_MANAGE)
    assert has_permission("operator", Permission.CRAWL_WRITE)
    assert not has_permission("viewer", Permission.CRAWL_WRITE)
    assert not has_permission("operator", Permission.USER_MANAGE)
    assert has_permission("viewer", Permission.ANALYTICS_READ)


def test_api_key_generation():
    key, key_hash, prefix = generate_api_key()
    assert key.startswith("nxs_")
    assert hash_api_key(key) == key_hash
    assert key.startswith(prefix)
    assert key_hash != key
