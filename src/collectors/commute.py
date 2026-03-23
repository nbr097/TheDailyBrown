from __future__ import annotations

from datetime import datetime, timedelta

import httpx

from src.config import settings


async def fetch_commute(
    lat: float,
    lon: float,
    first_meeting_time: str | None = None,
) -> dict:
    """Fetch commute info from Google Maps Directions API.

    Args:
        lat: Origin latitude.
        lon: Origin longitude.
        first_meeting_time: Optional HH:MM string for first meeting.

    Returns:
        Dict with duration_seconds, duration_text, distance_text,
        and optionally leave_by.
    """
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": f"{lat},{lon}",
        "destination": settings.work_address,
        "key": settings.google_maps_api_key,
        "departure_time": "now",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    leg = data["routes"][0]["legs"][0]

    # Prefer duration_in_traffic when available, fall back to duration
    traffic = leg.get("duration_in_traffic", leg["duration"])
    duration_seconds = traffic["value"]
    duration_text = traffic["text"]
    distance_text = leg["distance"]["text"]

    result: dict = {
        "duration_seconds": duration_seconds,
        "duration_text": duration_text,
        "distance_text": distance_text,
    }

    if first_meeting_time is not None:
        try:
            meeting_dt = datetime.fromisoformat(first_meeting_time)
        except (ValueError, TypeError):
            meeting_dt = datetime.strptime(first_meeting_time, "%H:%M")
        leave_dt = meeting_dt - timedelta(seconds=duration_seconds) - timedelta(minutes=5)
        result["leave_by"] = leave_dt.strftime("%-I:%M %p").lower()

    return result
