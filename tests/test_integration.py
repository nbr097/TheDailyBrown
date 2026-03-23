import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_full_flow_health_to_summary(client):
    # Health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # Summary with mocked collectors
    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value={"current": {}, "hourly": []}), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value={"duration_text": "N/A"}), \
         patch("src.routes.summary.get_cached_calendar", return_value=[]), \
         patch("src.routes.summary.get_cached_birthdays", return_value=[]), \
         patch("src.routes.summary.get_cached_news", return_value={}), \
         patch("src.routes.summary.get_cached_reminders", return_value=[]), \
         patch("src.routes.summary.get_cached_flagged", return_value=[]):

        resp = client.get(
            "/summary?lat=-27.57&lon=151.95",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(k in data for k in ["weather", "commute", "calendar", "birthdays", "news", "reminders", "flagged_emails"])

def test_reminders_ingestion_and_retrieval(client):
    # Push reminders
    client.post(
        "/data/reminders",
        json={"reminders": [{"title": "Test reminder", "due": "2026-03-23T09:00:00"}]},
        headers={"Authorization": "Bearer test-bearer-token"},
    )

    # Verify they appear in summary
    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value={"current": {}, "hourly": []}), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value={}), \
         patch("src.routes.summary.get_cached_calendar", return_value=[]), \
         patch("src.routes.summary.get_cached_birthdays", return_value=[]), \
         patch("src.routes.summary.get_cached_news", return_value={}), \
         patch("src.routes.summary.get_cached_flagged", return_value=[]):

        resp = client.get(
            "/summary?lat=-27.57&lon=151.95",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
        assert resp.json()["reminders"][0]["title"] == "Test reminder"
