from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_admin_update_requires_auth(client):
    resp = client.post("/admin/update")
    assert resp.status_code == 403


def test_admin_update_signals_updater(client):
    with patch("src.routes.admin.signal_updater", return_value=True):
        resp = client.post(
            "/admin/update",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Update initiated"
