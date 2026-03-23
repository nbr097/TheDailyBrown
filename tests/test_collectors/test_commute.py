import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.collectors.commute import fetch_commute

MOCK_GMAPS_RESPONSE = {
    "routes": [{
        "legs": [{
            "duration_in_traffic": {"value": 1320, "text": "22 mins"},
            "duration": {"value": 1200, "text": "20 mins"},
            "distance": {"value": 15000, "text": "15 km"},
        }]
    }],
    "status": "OK",
}

@pytest.mark.asyncio
async def test_fetch_commute():
    with patch("src.collectors.commute.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_GMAPS_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_commute(-27.57, 151.95)

    assert result["duration_seconds"] == 1320
    assert result["duration_text"] == "22 mins"
    assert result["distance_text"] == "15 km"

@pytest.mark.asyncio
async def test_fetch_commute_calculates_leave_by():
    with patch("src.collectors.commute.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_GMAPS_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_commute(-27.57, 151.95, first_meeting_time="09:00")

    assert result["leave_by"] == "08:38"
