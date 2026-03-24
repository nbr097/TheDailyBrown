from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.database import init_db
from src.main import app


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def test_bearer_token_accepted(client):
    """Raw bearer token should still work (widget/shortcuts).
    Note: /summary calls real collectors that fail with test keys,
    so we just verify we get past auth (not 401/403)."""
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code not in (401, 403)


def test_jwt_accepted(client):
    """JWT from Face ID auth should work."""
    from src.auth.jwt import create_jwt
    token = create_jwt("nic")
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code not in (401, 403)


def test_invalid_token_rejected(client):
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer garbage-token"},
    )
    assert resp.status_code == 401


def test_expired_jwt_rejected(client):
    from src.auth.jwt import create_jwt
    token = create_jwt("nic", expires_hours=-1)
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_no_auth_header_rejected(client):
    resp = client.get("/summary?lat=-27.57&lon=151.95")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no header
