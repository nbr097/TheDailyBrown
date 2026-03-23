import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.collectors.outlook import fetch_outlook_calendar, fetch_flagged_emails

MOCK_CALENDAR_RESPONSE = {
    "value": [
        {
            "subject": "Sprint Planning",
            "start": {"dateTime": "2026-03-23T09:00:00", "timeZone": "Australia/Brisbane"},
            "end": {"dateTime": "2026-03-23T10:00:00", "timeZone": "Australia/Brisbane"},
            "location": {"displayName": "Room 3"},
            "onlineMeeting": {"joinUrl": "https://teams.microsoft.com/meet/123"},
            "isOnlineMeeting": True,
        }
    ]
}

MOCK_FLAGGED_RESPONSE = {
    "value": [
        {
            "subject": "Review Q1 report",
            "from": {"emailAddress": {"name": "Jane", "address": "jane@work.com"}},
            "receivedDateTime": "2026-03-22T14:00:00Z",
        }
    ]
}

@pytest.mark.asyncio
async def test_fetch_outlook_calendar():
    with patch("src.collectors.outlook._get_access_token", return_value="fake-token"):
        with patch("src.collectors.outlook.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = MOCK_CALENDAR_RESPONSE
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_outlook_calendar()

    assert len(result) == 1
    assert result[0]["subject"] == "Sprint Planning"
    assert result[0]["teams_link"] == "https://teams.microsoft.com/meet/123"
    assert result[0]["source"] == "work"

@pytest.mark.asyncio
async def test_fetch_flagged_emails():
    with patch("src.collectors.outlook._get_access_token", return_value="fake-token"):
        with patch("src.collectors.outlook.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.json.return_value = MOCK_FLAGGED_RESPONSE
            mock_resp.raise_for_status = MagicMock()
            mock_client.get.return_value = mock_resp
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_flagged_emails()

    assert len(result) == 1
    assert result[0]["subject"] == "Review Q1 report"
    assert result[0]["from_name"] == "Jane"
