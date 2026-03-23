import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_post_reminders_stores_data(client):
    payload = {
        "reminders": [
            {"title": "Buy milk", "due": "2026-03-23T09:00:00"},
            {"title": "Call dentist", "due": "2026-03-23T14:00:00"},
        ]
    }
    resp = client.post(
        "/data/reminders",
        json=payload,
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["stored"] == 2

def test_post_reminders_rejects_bad_token(client):
    resp = client.post(
        "/data/reminders",
        json={"reminders": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401
