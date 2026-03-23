import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.collectors.weather import fetch_weather

MOCK_OWM_RESPONSE = {
    "current": {
        "temp": 22.5,
        "feels_like": 21.0,
        "weather": [{"main": "Clear", "description": "clear sky", "icon": "01d"}],
        "humidity": 45,
        "wind_speed": 3.2,
    },
    "hourly": [
        {"dt": 1700000000, "temp": 22, "pop": 0.1, "weather": [{"main": "Clear", "icon": "01d"}]},
        {"dt": 1700003600, "temp": 21, "pop": 0.3, "weather": [{"main": "Clouds", "icon": "02d"}]},
    ],
}

@pytest.mark.asyncio
async def test_fetch_weather_returns_structured_data():
    with patch("src.collectors.weather.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = MOCK_OWM_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_client.get.return_value = mock_resp
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_weather(-27.57, 151.95)

    assert result["current"]["temp"] == 22.5
    assert result["current"]["condition"] == "Clear"
    assert len(result["hourly"]) == 2
    assert result["hourly"][1]["precipitation_chance"] == 0.3
