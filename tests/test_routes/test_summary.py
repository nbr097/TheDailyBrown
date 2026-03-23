import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_summary_requires_coords(client):
    resp = client.get(
        "/summary",
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 422

def test_summary_returns_all_sections(client):
    mock_weather = {"current": {"temp": 22}, "hourly": []}
    mock_commute = {"duration_text": "20 mins", "leave_by": "08:40"}

    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value=mock_weather), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value=mock_commute), \
         patch("src.routes.summary.get_cached_calendar", return_value=[{"subject": "Standup", "start": "09:00", "source": "work"}]), \
         patch("src.routes.summary.get_cached_birthdays", return_value=[{"name": "Jane"}]), \
         patch("src.routes.summary.get_cached_news", return_value={"headlines": [], "ai": []}), \
         patch("src.routes.summary.get_cached_reminders", return_value=[{"title": "Buy milk"}]), \
         patch("src.routes.summary.get_cached_flagged", return_value=[{"subject": "Review report"}]):

        resp = client.get(
            "/summary?lat=-27.57&lon=151.95",
            headers={"Authorization": "Bearer test-bearer-token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "weather" in data
    assert "commute" in data
    assert "calendar" in data
    assert "birthdays" in data
    assert "news" in data
    assert "reminders" in data
    assert "flagged_emails" in data
