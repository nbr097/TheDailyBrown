from __future__ import annotations

import time
from datetime import datetime, timedelta

import httpx
import msal

from src.config import settings
from src.database import get_db

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SCOPES = ["Calendars.Read", "Mail.Read"]


def _get_access_token() -> str:
    """Refresh the Microsoft access token using the stored refresh token.

    If no refresh token is found in the database, raises RuntimeError
    instructing the user to run the install script for initial auth.
    """
    conn = get_db()
    row = conn.execute(
        "SELECT access_token, refresh_token, expires_at FROM oauth_tokens WHERE provider = ?",
        ("microsoft",),
    ).fetchone()
    conn.close()

    if row is None or not row["refresh_token"]:
        raise RuntimeError(
            "No Microsoft refresh token found. Run the install script to authenticate."
        )

    # If current token is still valid, return it
    if row["expires_at"] and time.time() < row["expires_at"] - 60:
        return row["access_token"]

    app = msal.PublicClientApplication(
        client_id=settings.ms_client_id,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )

    result = app.acquire_token_by_refresh_token(
        refresh_token=row["refresh_token"],
        scopes=SCOPES,
    )

    if "access_token" not in result:
        raise RuntimeError(
            f"Failed to refresh Microsoft token: {result.get('error_description', 'unknown error')}. "
            "Run the install script to re-authenticate."
        )

    conn = get_db()
    conn.execute(
        "UPDATE oauth_tokens SET access_token = ?, refresh_token = ?, expires_at = ? WHERE provider = ?",
        (
            result["access_token"],
            result.get("refresh_token", row["refresh_token"]),
            time.time() + result.get("expires_in", 3600),
            "microsoft",
        ),
    )
    conn.commit()
    conn.close()

    return result["access_token"]


async def fetch_outlook_calendar() -> list[dict]:
    """Fetch today's calendar events from Microsoft Graph."""
    token = _get_access_token()
    tz = settings.timezone

    now = datetime.now()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    params = {
        "startDateTime": start_of_day.isoformat(),
        "endDateTime": end_of_day.isoformat(),
        "$orderby": "start/dateTime",
        "$top": "50",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": f'outlook.timezone="{tz}"',
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/calendarview",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    events = []
    for item in data.get("value", []):
        event = {
            "subject": item["subject"],
            "start": item["start"]["dateTime"],
            "end": item["end"]["dateTime"],
            "location": item.get("location", {}).get("displayName", ""),
            "is_online": item.get("isOnlineMeeting", False),
            "teams_link": (
                item.get("onlineMeeting", {}) or {}
            ).get("joinUrl", ""),
            "source": "work",
        }
        events.append(event)

    return events


async def fetch_flagged_emails() -> list[dict]:
    """Fetch flagged emails from Microsoft Graph."""
    token = _get_access_token()

    params = {
        "$filter": "flag/flagStatus eq 'flagged'",
        "$orderby": "receivedDateTime desc",
        "$top": "20",
        "$select": "subject,from,receivedDateTime,flag,webLink",
    }
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/messages",
            params=params,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    emails = []
    for item in data.get("value", []):
        from_info = item.get("from", {}).get("emailAddress", {})
        email = {
            "subject": item["subject"],
            "from_name": from_info.get("name", ""),
            "from_address": from_info.get("address", ""),
            "received": item.get("receivedDateTime", ""),
            "source": "work",
        }
        emails.append(email)

    return emails
