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

def test_post_outlook_stores_data(client):
    payload = {
        "calendar": [
            {"subject": "Standup", "start": "2026-03-24T09:00:00+10:00",
             "end": "2026-03-24T09:30:00+10:00", "location": "Room 3B",
             "teams_link": "", "source": "work"}
        ],
        "flagged_emails": [
            {"subject": "Budget", "from_name": "Jane", "from_address": "jane@co.com",
             "received": "2026-03-23T14:00:00+10:00", "source": "work"}
        ],
        "unread_emails": [
            {"subject": "Reset", "from_name": "IT", "from_address": "it@co.com",
             "received": "2026-03-23T16:00:00+10:00", "source": "work"}
        ],
    }
    resp = client.post(
        "/data/outlook",
        json=payload,
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stored_calendar"] == 1
    assert data["stored_flagged"] == 1
    assert data["stored_unread"] == 1

def test_post_outlook_rejects_bad_token(client):
    resp = client.post(
        "/data/outlook",
        json={"calendar": [], "flagged_emails": [], "unread_emails": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401
