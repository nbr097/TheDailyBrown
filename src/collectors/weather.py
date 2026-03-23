import httpx
from src.config import settings


async def fetch_weather(lat: float, lon: float) -> dict:
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": settings.openweathermap_api_key,
        "units": "metric",
        "exclude": "minutely,daily,alerts",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    current = data["current"]
    hourly = [
        {
            "dt": h["dt"],
            "temp": h["temp"],
            "precipitation_chance": h.get("pop", 0),
            "condition": h["weather"][0]["main"],
            "icon": h["weather"][0]["icon"],
        }
        for h in data.get("hourly", [])[:8]
    ]

    return {
        "current": {
            "temp": current["temp"],
            "feels_like": current["feels_like"],
            "condition": current["weather"][0]["main"],
            "description": current["weather"][0]["description"],
            "icon": current["weather"][0]["icon"],
            "humidity": current["humidity"],
            "wind_speed": current["wind_speed"],
        },
        "hourly": hourly,
    }
