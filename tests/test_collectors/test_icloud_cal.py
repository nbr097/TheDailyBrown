import pytest
from unittest.mock import patch, MagicMock
from src.collectors.icloud_cal import fetch_icloud_calendar

@pytest.mark.asyncio
async def test_fetch_icloud_calendar():
    mock_event = MagicMock()
    mock_event.vobject_instance.vevent.summary.value = "Dinner with partner"
    mock_event.vobject_instance.vevent.dtstart.value = MagicMock()
    mock_event.vobject_instance.vevent.dtstart.value.isoformat.return_value = "2026-03-23T18:00:00"
    mock_event.vobject_instance.vevent.dtend.value = MagicMock()
    mock_event.vobject_instance.vevent.dtend.value.isoformat.return_value = "2026-03-23T20:00:00"
    mock_event.vobject_instance.vevent.contents = {}

    mock_calendar = MagicMock()
    mock_calendar.search.return_value = [mock_event]

    with patch("src.collectors.icloud_cal.caldav.DAVClient") as MockDAV:
        mock_client = MagicMock()
        mock_client.principal.return_value.calendars.return_value = [mock_calendar]
        MockDAV.return_value = mock_client

        result = await fetch_icloud_calendar()

    assert len(result) == 1
    assert result[0]["subject"] == "Dinner with partner"
    assert result[0]["source"] == "personal"
