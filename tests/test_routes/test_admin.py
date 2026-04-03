from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_update_without_auth_allowed(client):
    """Admin update uses optional auth — no token still gets through to the handler."""
    resp = client.post("/admin/update")
    # 503 = updater socket not available (but auth passed)
    assert resp.status_code in (200, 503)


def test_admin_update_signals_updater(client):
    with patch("src.routes.admin.signal_updater", return_value=True):
        resp = client.post(
            "/admin/update",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Update initiated"
