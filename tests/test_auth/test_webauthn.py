from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import src.database


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setattr(src.database, "DB_PATH", db_file)
    src.database.init_db()
    from src.main import app
    return TestClient(app)


def test_register_options_returns_platform(client):
    resp = client.get("/auth/webauthn/register-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "rp" in data
    assert data["authenticatorSelection"]["authenticatorAttachment"] == "platform"
    assert data["authenticatorSelection"]["userVerification"] == "required"


def test_authenticate_options(client):
    resp = client.get("/auth/webauthn/authenticate-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data


def test_list_credentials_empty(client):
    resp = client.get("/auth/webauthn/credentials")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_credential_not_found(client):
    resp = client.delete("/auth/webauthn/credentials/nonexistent")
    assert resp.status_code == 404
