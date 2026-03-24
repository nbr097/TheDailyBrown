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


def test_register_options_blocked_when_credential_exists(client):
    """Should reject registration when a credential already exists."""
    from src.database import get_db
    import time
    conn = get_db()
    conn.execute(
        "INSERT INTO webauthn_credentials (id, public_key, sign_count, created_at) VALUES (?, ?, ?, ?)",
        ("test-cred-id", b"fake-key", 0, time.time()),
    )
    conn.commit()
    conn.close()

    resp = client.get("/auth/webauthn/register-options")
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()
