from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.database import init_db
from src.main import app


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def test_webauthn_register_options(client):
    resp = client.get("/auth/webauthn/register-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "rp" in data


def test_webauthn_authenticate_options(client):
    resp = client.get("/auth/webauthn/authenticate-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
