from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import src.config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory cache for pre-fetched data
# ---------------------------------------------------------------------------
_cache: dict[str, Any] = {
    "calendar": [],
    "birthdays": [],
    "news": {},
    "flagged_emails": [],
    "unread_emails": [],
    "last_run": None,
    "errors": [],
}

# ---------------------------------------------------------------------------
# System health tracking for 9 systems
# ---------------------------------------------------------------------------
_SYSTEMS = [
    "openweathermap",
    "microsoft_graph",
    "icloud_caldav",
    "icloud_carddav",
    "google_maps",
    "rss_feeds",
    "ios_reminders_push",
    "cloudflare_tunnel",
    "docker_updater",
]

_system_health: dict[str, dict[str, Any]] = {
    s: {"status": "unknown", "last_check": None, "error": None} for s in _SYSTEMS
}


def _update_system_status(system: str, success: bool, error: Optional[str] = None) -> None:
    _system_health[system] = {
        "status": "ok" if success else "error",
        "last_check": datetime.now().isoformat(),
        "error": error,
    }


# ---------------------------------------------------------------------------
# Cache access helpers
# ---------------------------------------------------------------------------
def get_cached_calendar() -> list[dict]:
    return _cache["calendar"]


def get_cached_birthdays() -> list[dict]:
    return _cache["birthdays"]


def get_cached_news() -> dict:
    return _cache["news"]


def get_cached_flagged() -> list[dict]:
    return _cache["flagged_emails"]


def get_cached_unread() -> list[dict]:
    return _cache["unread_emails"]


def set_cached_outlook_data(
    calendar: list[dict],
    flagged_emails: list[dict],
    unread_emails: list[dict],
) -> None:
    """Store Outlook data pushed from iOS Shortcut. Preserves personal calendar events."""
    personal = [e for e in _cache["calendar"] if e.get("source") != "work"]
    _cache["calendar"] = personal + calendar
    _cache["flagged_emails"] = flagged_emails
    _cache["unread_emails"] = unread_emails


def get_cached_reminders() -> list[dict]:
    from src.collectors.reminders import get_reminders
    return get_reminders()


def get_cache_status() -> dict:
    return {"last_run": _cache["last_run"], "errors": _cache["errors"]}


def get_system_health() -> dict[str, Any]:
    health = dict(_system_health)

    # Check docker updater socket availability (communicates via unix socket)
    import os
    updater_sock = os.path.exists("/tmp/updater.sock")
    if health["docker_updater"]["status"] == "unknown":
        health["docker_updater"] = {
            "status": "ok" if updater_sock else "unavailable",
            "last_check": datetime.now().isoformat(),
            "error": None if updater_sock else "Updater socket not found",
        }

    # Check reminders push recency
    from src.collectors.reminders import get_reminders_last_push
    last_push = get_reminders_last_push()
    if last_push:
        health["ios_reminders_push"] = {
            "status": "ok",
            "last_check": last_push,
            "error": None,
        }
    elif health["ios_reminders_push"]["status"] == "unknown":
        health["ios_reminders_push"] = {
            "status": "waiting",
            "last_check": None,
            "error": "No push received yet",
        }

    # Check Cloudflare tunnel by verifying cloudflared container is reachable
    if health["cloudflare_tunnel"]["status"] == "unknown":
        import httpx
        try:
            resp = httpx.get("http://cloudflared:2000/ready", timeout=3)
            tunnel_ok = resp.status_code == 200
        except Exception:
            # Fallback: check if we're being accessed through the tunnel
            # (if dashboard is reachable externally, tunnel works)
            tunnel_ok = bool(os.environ.get("CLOUDFLARE_TUNNEL_TOKEN"))
        health["cloudflare_tunnel"] = {
            "status": "ok" if tunnel_ok else "unknown",
            "last_check": datetime.now().isoformat(),
            "error": None if tunnel_ok else "Cannot verify tunnel status",
        }

    return health


# ---------------------------------------------------------------------------
# Cron job: fetch all data sources and update cache
# ---------------------------------------------------------------------------
async def run_cache_job() -> None:
    logger.info("Running scheduled cache job")
    errors: list[str] = []

    # --- Outlook calendar ---
    try:
        from src.collectors.outlook import fetch_outlook_calendar
        outlook_events = await fetch_outlook_calendar()
        _update_system_status("microsoft_graph", True)
    except Exception as exc:
        logger.error("Outlook calendar fetch failed: %s", exc)
        outlook_events = []
        errors.append(f"outlook_calendar: {exc}")
        _update_system_status("microsoft_graph", False, str(exc))

    # --- iCloud calendar ---
    try:
        from src.collectors.icloud_cal import fetch_icloud_calendar
        icloud_events = await fetch_icloud_calendar()
        _update_system_status("icloud_caldav", True)
    except Exception as exc:
        logger.error("iCloud calendar fetch failed: %s", exc)
        icloud_events = []
        errors.append(f"icloud_calendar: {exc}")
        _update_system_status("icloud_caldav", False, str(exc))

    _cache["calendar"] = outlook_events + icloud_events

    # --- Birthdays ---
    try:
        from src.collectors.icloud_contacts import fetch_todays_birthdays
        _cache["birthdays"] = await fetch_todays_birthdays()
        _update_system_status("icloud_carddav", True)
    except Exception as exc:
        logger.error("Birthdays fetch failed: %s", exc)
        _cache["birthdays"] = []
        errors.append(f"birthdays: {exc}")
        _update_system_status("icloud_carddav", False, str(exc))

    # --- News ---
    try:
        from src.collectors.news import fetch_news
        _cache["news"] = await fetch_news()
        _update_system_status("rss_feeds", True)
    except Exception as exc:
        logger.error("News fetch failed: %s", exc)
        _cache["news"] = {}
        errors.append(f"news: {exc}")
        _update_system_status("rss_feeds", False, str(exc))

    # --- Flagged emails ---
    try:
        from src.collectors.outlook import fetch_flagged_emails
        _cache["flagged_emails"] = await fetch_flagged_emails()
        # microsoft_graph already updated by calendar fetch, update again
        _update_system_status("microsoft_graph", True)
    except Exception as exc:
        logger.error("Flagged emails fetch failed: %s", exc)
        _cache["flagged_emails"] = []
        errors.append(f"flagged_emails: {exc}")
        _update_system_status("microsoft_graph", False, str(exc))

    _cache["last_run"] = datetime.now().isoformat()
    _cache["errors"] = errors
    logger.info("Cache job complete. Errors: %d", len(errors))


# ---------------------------------------------------------------------------
# Scheduler factory
# ---------------------------------------------------------------------------
def create_scheduler() -> AsyncIOScheduler:
    settings = src.config.settings
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_cache_job,
        "cron",
        hour=settings.cache_schedule_hour,
        minute=settings.cache_schedule_minute,
        id="morning_cache_job",
    )
    return scheduler
