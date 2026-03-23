from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from src.auth.bearer import verify_bearer
from src.cache import location_cache, TTLCache
from src.collectors.weather import fetch_weather
from src.collectors.commute import fetch_commute
from src.scheduler import (
    get_cached_calendar,
    get_cached_birthdays,
    get_cached_news,
    get_cached_reminders,
    get_cached_flagged,
    get_cache_status,
    _update_system_status,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary")
async def summary(
    lat: float = Query(...),
    lon: float = Query(...),
    _=Depends(verify_bearer),
):
    # --- Weather (dynamic with TTL cache) ---
    weather_key = TTLCache.coord_key("weather", lat, lon)
    weather = location_cache.get(weather_key)
    if weather is None:
        try:
            weather = await fetch_weather(lat, lon)
            location_cache.set(weather_key, weather)
            _update_system_status("openweathermap", True)
        except Exception as exc:
            logger.error("Weather fetch failed: %s", exc)
            weather = {"error": str(exc)}
            _update_system_status("openweathermap", False, str(exc))

    # --- Commute (dynamic with TTL cache) ---
    commute_key = TTLCache.coord_key("commute", lat, lon)
    commute = location_cache.get(commute_key)
    if commute is None:
        try:
            # Use first calendar event to calculate leave_by
            calendar = get_cached_calendar()
            first_meeting = None
            if calendar:
                first_meeting = calendar[0].get("start")
            commute = await fetch_commute(lat, lon, first_meeting_time=first_meeting)
            location_cache.set(commute_key, commute)
            _update_system_status("google_maps", True)
        except Exception as exc:
            logger.error("Commute fetch failed: %s", exc)
            commute = {"error": str(exc)}
            _update_system_status("google_maps", False, str(exc))

    return {
        "weather": weather,
        "commute": commute,
        "calendar": get_cached_calendar(),
        "birthdays": get_cached_birthdays(),
        "news": get_cached_news(),
        "reminders": get_cached_reminders(),
        "flagged_emails": get_cached_flagged(),
        "cache_status": get_cache_status(),
    }
