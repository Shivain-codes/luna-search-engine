"""Integration tests for the Admin API: auth, RBAC, crawl, analytics."""

import pytest
from fastapi.testclient import TestClient
from luna_shared.repositories import AdminRepository
from luna_shared.security import create_access_token, hash_password

pytestmark = pytest.mark.asyncio


async def _seed_admin(database, email="admin@test.dev", role="admin") -> str:
    async with database.session() as session:
        user = await AdminRepository(session).create_user(
            email=email, hashed_password=hash_password("password123"), role=role
        )
        return str(user.id)


async def test_login_success_and_failure(database):
    await _seed_admin(database)
    from admin_api.main import app

    with TestClient(app) as client:
        ok = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.dev", "password": "password123"},
        )
        assert ok.status_code == 200
        assert "access_token" in ok.json()

        bad = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.dev", "password": "wrong"},
        )
        assert bad.status_code == 401
        # Error message must not reveal whether the account exists.
        assert "credential" in bad.json()["error"]["message"].lower()


async def test_unauthenticated_returns_401(database):
    from admin_api.main import app

    with TestClient(app) as client:
        assert client.get("/api/v1/admin/index/stats").status_code == 401


async def test_rbac_viewer_cannot_create_job(database):
    import uuid

    from admin_api.main import app

    token = create_access_token(str(uuid.uuid4()), "viewer")
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/crawl/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "x", "seed_urls": ["https://a.com"]},
        )
        assert resp.status_code == 403


async def test_operator_can_create_job(database):
    import uuid

    from admin_api.main import app

    token = create_access_token(str(uuid.uuid4()), "operator")
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/crawl/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "job1", "seed_urls": ["https://a.com"]},
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "pending"

        listing = client.get(
            "/api/v1/admin/crawl/jobs", headers={"Authorization": f"Bearer {token}"}
        )
        assert listing.status_code == 200
        assert len(listing.json()) == 1


async def test_api_key_returned_once(database):
    admin_id = await _seed_admin(database)
    from admin_api.main import app

    token = create_access_token(admin_id, "admin")
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/admin/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "test-key"},
        )
        assert resp.status_code == 201
        created = resp.json()
        assert created["key"].startswith("nxs_")

        # Listing must not expose the plaintext key.
        listing = client.get(
            "/api/v1/admin/api-keys", headers={"Authorization": f"Bearer {token}"}
        )
        for key in listing.json():
            assert "key" not in key or not key.get("key", "").startswith("nxs_")


async def test_analytics_empty_is_honest(database):
    from admin_api.main import app

    token = create_access_token("admin-id", "admin")
    with TestClient(app) as client:
        resp = client.get(
            "/api/v1/admin/analytics/queries", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_queries"] == 0
        assert data["click_through_rate"] is None
        assert data["latency"]["p95"] is None
