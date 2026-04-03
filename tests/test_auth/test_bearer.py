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
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code not in (401, 403)


def test_invalid_token_rejected(client):
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer garbage-token"},
    )
    assert resp.status_code == 401


def test_no_auth_header_allowed(client):
    """Dashboard access via Cloudflare Access — no bearer token needed."""
    resp = client.get("/summary?lat=-27.57&lon=151.95")
    assert resp.status_code not in (401, 403)
