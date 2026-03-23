# Morning Briefing System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Dockerised morning briefing system on a Raspberry Pi that aggregates weather, calendars, commute, news, birthdays, reminders, and flagged emails into a Scriptable iOS widget and a glassmorphism web dashboard.

**Architecture:** Python/FastAPI backend with APScheduler for 4am data pre-cache. Three Docker containers: app (FastAPI + static dashboard), cloudflared (tunnel), and updater (sidecar with Docker socket). Scriptable widget on iOS sends GPS coords, API returns location-aware JSON. Web dashboard served from same container, secured via Cloudflare Access + WebAuthn/Face ID.

**Tech Stack:** Python 3.11+, FastAPI, APScheduler, SQLite, Docker Compose, Cloudflare Tunnel, Tailwind CSS (CDN), Phosphor Icons (CDN), vanilla JS, Scriptable (iOS)

**Spec:** `docs/superpowers/specs/2026-03-23-morning-briefing-design.md`

---

## File Structure

```
morning-briefing/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── install.sh
├── manage.sh
├── .env.example
├── .gitignore
├── src/
│   ├── main.py                  # FastAPI app entry, mounts routes, serves dashboard
│   ├── config.py                # Pydantic settings from env vars
│   ├── database.py              # SQLite connection, schema init
│   ├── cache.py                 # TTL cache (10-min for weather/commute)
│   ├── scheduler.py             # APScheduler setup, 4am job
│   ├── auth/
│   │   ├── bearer.py            # Bearer token dependency for API routes
│   │   └── webauthn.py          # WebAuthn registration + verification endpoints
│   ├── collectors/
│   │   ├── weather.py           # OpenWeatherMap API
│   │   ├── outlook.py           # Microsoft Graph (calendar + flagged emails)
│   │   ├── icloud_cal.py        # iCloud CalDAV (personal calendar)
│   │   ├── icloud_contacts.py   # iCloud CardDAV (birthdays)
│   │   ├── commute.py           # Google Maps Directions API
│   │   ├── news.py              # RSS feed parser
│   │   └── reminders.py         # Data model for iOS Shortcut push
│   └── routes/
│       ├── summary.py           # GET /summary?lat=X&lon=Y
│       ├── admin.py             # POST /admin/update
│       └── data.py              # POST /data/reminders
├── dashboard/
│   ├── index.html               # Single page, Tailwind CDN, Phosphor Icons CDN
│   ├── css/
│   │   └── glass.css            # Glassmorphism custom styles (backdrop-blur, borders)
│   └── js/
│       ├── app.js               # Fetches /summary, renders cards, manages tabs
│       ├── auth.js              # WebAuthn client-side (register + authenticate)
│       └── admin.js             # Update button + Face ID confirmation
├── updater/
│   ├── Dockerfile               # Alpine + docker CLI + socat
│   └── updater.sh               # Listens on Unix socket, pulls + restarts app
├── scriptable/
│   └── morning-widget.js        # Scriptable widget template
├── shortcuts/
│   └── SETUP.md                 # iOS Shortcut setup instructions (charger trigger, 6:30am fallback, reminders push)
└── tests/
    ├── conftest.py              # Shared fixtures (test client, mock env, temp DB)
    ├── test_config.py
    ├── test_database.py
    ├── test_cache.py
    ├── test_collectors/
    │   ├── test_weather.py
    │   ├── test_outlook.py
    │   ├── test_icloud_cal.py
    │   ├── test_icloud_contacts.py
    │   ├── test_commute.py
    │   └── test_news.py
    ├── test_routes/
    │   ├── test_summary.py
    │   ├── test_health.py
    │   ├── test_admin.py
    │   └── test_data.py
    └── test_auth/
        ├── test_bearer.py
        └── test_webauthn.py
```

---

## Task 1: Project Scaffold & Config

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/config.py`
- Create: `src/main.py`
- Test: `tests/conftest.py`, `tests/test_config.py`

- [ ] **Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.env
*.db
.venv/
.pytest_cache/
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
apscheduler==3.11.0
httpx==0.28.1
feedparser==6.0.11
caldav==1.4.0
vobject==0.9.8
msal==1.32.0
py-webauthn==2.5.0
python-dotenv==1.1.0
pydantic-settings==2.8.1
cbor2==5.6.5
pytest==8.3.5
pytest-asyncio==0.25.3
```

- [ ] **Step 3: Create `.env.example`**

Copy the env var block from the spec verbatim. This is the template for the install script.

```
# Schedule
CACHE_SCHEDULE_HOUR=4
CACHE_SCHEDULE_MINUTE=0
TIMEZONE=Australia/Brisbane

# Weather
OPENWEATHERMAP_API_KEY=

# Microsoft 365
MS_CLIENT_ID=
MS_CLIENT_SECRET=
MS_TENANT_ID=

# iCloud
ICLOUD_USERNAME=
ICLOUD_APP_PASSWORD=

# Google Maps
GOOGLE_MAPS_API_KEY=

# Commute
WORK_ADDRESS=305 Taylor St, Wilsonton QLD 4350

# Auth
API_BEARER_TOKEN=
DASHBOARD_DOMAIN=morning.yourdomain.com

# Cloudflare
CLOUDFLARE_TUNNEL_TOKEN=
```

- [ ] **Step 4: Write failing test for config**

```python
# tests/conftest.py
import os
import pytest

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set minimal env vars for all tests."""
    env = {
        "CACHE_SCHEDULE_HOUR": "4",
        "CACHE_SCHEDULE_MINUTE": "0",
        "TIMEZONE": "Australia/Brisbane",
        "OPENWEATHERMAP_API_KEY": "test-weather-key",
        "MS_CLIENT_ID": "test-ms-id",
        "MS_CLIENT_SECRET": "test-ms-secret",
        "MS_TENANT_ID": "test-ms-tenant",
        "ICLOUD_USERNAME": "test@icloud.com",
        "ICLOUD_APP_PASSWORD": "test-icloud-pw",
        "GOOGLE_MAPS_API_KEY": "test-gmaps-key",
        "WORK_ADDRESS": "305 Taylor St, Wilsonton QLD 4350",
        "API_BEARER_TOKEN": "test-bearer-token",
        "DASHBOARD_DOMAIN": "morning.test.com",
        "CLOUDFLARE_TUNNEL_TOKEN": "test-cf-token",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
```

```python
# tests/test_config.py
from src.config import Settings

def test_settings_loads_from_env():
    settings = Settings()
    assert settings.timezone == "Australia/Brisbane"
    assert settings.cache_schedule_hour == 4
    assert settings.openweathermap_api_key == "test-weather-key"
    assert settings.work_address == "305 Taylor St, Wilsonton QLD 4350"
    assert settings.api_bearer_token == "test-bearer-token"
```

- [ ] **Step 5: Run test to verify it fails**

Run: `cd ~/morning-briefing && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 6: Implement config**

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Schedule
    cache_schedule_hour: int = 4
    cache_schedule_minute: int = 0
    timezone: str = "Australia/Brisbane"

    # Weather
    openweathermap_api_key: str = ""

    # Microsoft 365
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_tenant_id: str = ""

    # iCloud
    icloud_username: str = ""
    icloud_app_password: str = ""

    # Google Maps
    google_maps_api_key: str = ""

    # Commute
    work_address: str = "305 Taylor St, Wilsonton QLD 4350"

    # Auth
    api_bearer_token: str = ""
    dashboard_domain: str = "morning.localhost"

    # Cloudflare
    cloudflare_tunnel_token: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

- [ ] **Step 7: Create minimal FastAPI app**

```python
# src/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.config import settings

app = FastAPI(title="Morning Briefing", docs_url=None, redoc_url=None)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: Run tests, verify passing**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 8.5: Create all `__init__.py` files**

```bash
touch src/__init__.py src/auth/__init__.py src/collectors/__init__.py src/routes/__init__.py tests/__init__.py tests/test_collectors/__init__.py tests/test_routes/__init__.py tests/test_auth/__init__.py
```

Create the directory structure too:
```bash
mkdir -p src/auth src/collectors src/routes tests/test_collectors tests/test_routes tests/test_auth
```

- [ ] **Step 9: Commit**

```bash
git add .gitignore requirements.txt .env.example src/ tests/
git commit -m "feat: project scaffold with config and FastAPI skeleton"
```

---

## Task 2: Database & Cache Layer

**Files:**
- Create: `src/database.py`
- Create: `src/cache.py`
- Test: `tests/test_cache.py`, `tests/test_database.py`

- [ ] **Step 1: Write failing test for TTL cache**

```python
# tests/test_cache.py
import time
from src.cache import TTLCache

def test_cache_set_and_get():
    cache = TTLCache(ttl_seconds=60)
    cache.set("weather::-27.6:151.9", {"temp": 22})
    assert cache.get("weather::-27.6:151.9") == {"temp": 22}

def test_cache_expired():
    cache = TTLCache(ttl_seconds=0.1)
    cache.set("key", "value")
    time.sleep(0.2)
    assert cache.get("key") is None

def test_cache_rounds_coordinates():
    cache = TTLCache(ttl_seconds=60)
    key1 = TTLCache.coord_key("weather", -27.5712, 151.9534)
    key2 = TTLCache.coord_key("weather", -27.5748, 151.9501)
    assert key1 == key2  # Rounded to 1 decimal place
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.cache'`

- [ ] **Step 3: Implement TTL cache**

```python
# src/cache.py
import time
from typing import Any

class TTLCache:
    def __init__(self, ttl_seconds: int = 600):
        self._store: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time(), value)

    def get(self, key: str) -> Any | None:
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    @staticmethod
    def coord_key(prefix: str, lat: float, lon: float) -> str:
        return f"{prefix}:{round(lat, 1)}:{round(lon, 1)}"

location_cache = TTLCache(ttl_seconds=600)
```

- [ ] **Step 4: Run tests, verify passing**

Run: `python -m pytest tests/test_cache.py -v`
Expected: PASS

- [ ] **Step 5: Write failing test for database**

```python
# tests/test_database.py
import os
import tempfile
import pytest
from unittest.mock import patch

def test_init_db_creates_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        with patch("src.database.DB_PATH", db_path):
            from src.database import init_db, get_db
            init_db()
            conn = get_db()
            tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = [t["name"] for t in tables]
            assert "oauth_tokens" in table_names
            assert "webauthn_credentials" in table_names
            assert "cache_status" in table_names
            conn.close()
```

- [ ] **Step 6: Implement database module**

```python
# src/database.py
import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "data/morning.db")

def get_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            provider TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at REAL
        );
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            public_key BLOB,
            sign_count INTEGER DEFAULT 0,
            created_at REAL
        );
        CREATE TABLE IF NOT EXISTS cache_status (
            source TEXT PRIMARY KEY,
            last_success REAL,
            last_error TEXT,
            data TEXT
        );
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 6: Commit**

```bash
git add src/cache.py src/database.py tests/test_cache.py
git commit -m "feat: add TTL cache and SQLite database layer"
```

---

## Task 3: Weather Collector

**Files:**
- Create: `src/collectors/weather.py`
- Test: `tests/test_collectors/test_weather.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_collectors/test_weather.py
import pytest
from unittest.mock import AsyncMock, patch
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
        mock_client.get.return_value.json.return_value = MOCK_OWM_RESPONSE
        mock_client.get.return_value.raise_for_status = lambda: None
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_weather(-27.57, 151.95)

    assert result["current"]["temp"] == 22.5
    assert result["current"]["condition"] == "Clear"
    assert len(result["hourly"]) == 2
    assert result["hourly"][1]["precipitation_chance"] == 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_weather.py -v`
Expected: FAIL

- [ ] **Step 3: Implement weather collector**

```python
# src/collectors/weather.py
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
```

- [ ] **Step 4: Run tests, verify passing**

Run: `python -m pytest tests/test_collectors/test_weather.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/__init__.py src/collectors/weather.py tests/test_collectors/__init__.py tests/test_collectors/test_weather.py
git commit -m "feat: add OpenWeatherMap weather collector"
```

---

## Task 4: Microsoft Graph Collector (Outlook Calendar + Flagged Emails)

**Files:**
- Create: `src/collectors/outlook.py`
- Test: `tests/test_collectors/test_outlook.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_collectors/test_outlook.py
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
            mock_client.get.return_value.json.return_value = MOCK_CALENDAR_RESPONSE
            mock_client.get.return_value.raise_for_status = lambda: None
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
            mock_client.get.return_value.json.return_value = MOCK_FLAGGED_RESPONSE
            mock_client.get.return_value.raise_for_status = lambda: None
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await fetch_flagged_emails()

    assert len(result) == 1
    assert result[0]["subject"] == "Review Q1 report"
    assert result[0]["from_name"] == "Jane"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_outlook.py -v`
Expected: FAIL

- [ ] **Step 3: Implement Outlook collector**

```python
# src/collectors/outlook.py
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from msal import PublicClientApplication
from src.config import settings
from src.database import get_db

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
# Delegated scopes — device code flow grants user context, required for /me/ endpoints
SCOPES = ["Calendars.Read", "Mail.Read"]

def _get_msal_app() -> PublicClientApplication:
    return PublicClientApplication(
        client_id=settings.ms_client_id,
        authority=f"https://login.microsoftonline.com/{settings.ms_tenant_id}",
    )

def _get_access_token() -> str:
    """Get access token via refresh token (stored during install-time device code flow).

    The install script performs the initial device code flow and stores the refresh token.
    This function only refreshes — it never initiates a new login.
    """
    db = get_db()
    row = db.execute("SELECT * FROM oauth_tokens WHERE provider = 'microsoft'").fetchone()
    db.close()

    if not row or not row["refresh_token"]:
        raise RuntimeError(
            "No Microsoft refresh token found. Run the install script to authenticate via device code flow."
        )

    app = _get_msal_app()
    result = app.acquire_token_by_refresh_token(row["refresh_token"], scopes=SCOPES)

    if "access_token" not in result:
        raise RuntimeError(f"Microsoft token refresh failed: {result.get('error_description', 'Unknown')}. Re-run install script to re-authenticate.")

    # Store updated tokens
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO oauth_tokens (provider, access_token, refresh_token, expires_at) VALUES (?, ?, ?, ?)",
        ("microsoft", result["access_token"], result.get("refresh_token", row["refresh_token"]), result.get("expires_in", 3600) + datetime.now().timestamp()),
    )
    db.commit()
    db.close()

    return result["access_token"]

async def fetch_outlook_calendar() -> list[dict]:
    token = _get_access_token()
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0).isoformat()
    end = (now.replace(hour=23, minute=59, second=59)).isoformat()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/calendarview",
            params={"startdatetime": start, "enddatetime": end, "$orderby": "start/dateTime"},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    events = []
    for ev in data.get("value", []):
        events.append({
            "subject": ev["subject"],
            "start": ev["start"]["dateTime"],
            "end": ev["end"]["dateTime"],
            "location": ev.get("location", {}).get("displayName", ""),
            "teams_link": ev.get("onlineMeeting", {}).get("joinUrl") if ev.get("isOnlineMeeting") else None,
            "source": "work",
        })
    return events

async def fetch_flagged_emails() -> list[dict]:
    token = _get_access_token()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GRAPH_BASE}/me/messages",
            params={
                "$filter": "flag/flagStatus eq 'flagged'",
                "$select": "subject,from,receivedDateTime",
                "$top": 10,
                "$orderby": "receivedDateTime desc",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        {
            "subject": msg["subject"],
            "from_name": msg["from"]["emailAddress"]["name"],
            "from_email": msg["from"]["emailAddress"]["address"],
            "received": msg["receivedDateTime"],
        }
        for msg in data.get("value", [])
    ]
```

- [ ] **Step 4: Run tests, verify passing**

Run: `python -m pytest tests/test_collectors/test_outlook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/outlook.py tests/test_collectors/test_outlook.py
git commit -m "feat: add Microsoft Graph collector for calendar and flagged emails"
```

---

## Task 5: iCloud Collectors (Personal Calendar + Birthdays)

**Files:**
- Create: `src/collectors/icloud_cal.py`
- Create: `src/collectors/icloud_contacts.py`
- Test: `tests/test_collectors/test_icloud_cal.py`, `tests/test_collectors/test_icloud_contacts.py`

- [ ] **Step 1: Write failing test for iCloud calendar**

```python
# tests/test_collectors/test_icloud_cal.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_icloud_cal.py -v`
Expected: FAIL

- [ ] **Step 3: Implement iCloud calendar collector**

```python
# src/collectors/icloud_cal.py
import caldav
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import settings

ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"

async def fetch_icloud_calendar() -> list[dict]:
    client = caldav.DAVClient(
        url=ICLOUD_CALDAV_URL,
        username=settings.icloud_username,
        password=settings.icloud_app_password,
    )
    principal = client.principal()
    calendars = principal.calendars()

    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    events = []
    for cal in calendars:
        for event in cal.search(start=start, end=end, event=True, expand=True):
            vevent = event.vobject_instance.vevent
            location = ""
            if "location" in vevent.contents:
                location = vevent.location.value

            events.append({
                "subject": vevent.summary.value,
                "start": vevent.dtstart.value.isoformat(),
                "end": vevent.dtend.value.isoformat(),
                "location": location,
                "teams_link": None,
                "source": "personal",
            })

    events.sort(key=lambda e: e["start"])
    return events
```

- [ ] **Step 4: Write failing test for birthdays**

```python
# tests/test_collectors/test_icloud_contacts.py
import pytest
from unittest.mock import patch, AsyncMock
from src.collectors.icloud_contacts import fetch_todays_birthdays

MOCK_CARDDAV_RESPONSE = """BEGIN:VCARD
VERSION:3.0
FN:Jane Smith
BDAY:19900323
END:VCARD

BEGIN:VCARD
VERSION:3.0
FN:John Doe
BDAY:19851225
END:VCARD"""

@pytest.mark.asyncio
async def test_fetch_todays_birthdays():
    with patch("src.collectors.icloud_contacts._fetch_all_vcards", new_callable=AsyncMock, return_value=MOCK_CARDDAV_RESPONSE):
        with patch("src.collectors.icloud_contacts.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "0323"
            mock_dt.side_effect = lambda *a, **kw: __import__("datetime").datetime(*a, **kw)
            result = await fetch_todays_birthdays()

    assert len(result) == 1
    assert result[0]["name"] == "Jane Smith"

@pytest.mark.asyncio
async def test_no_birthdays_today():
    with patch("src.collectors.icloud_contacts._fetch_all_vcards", new_callable=AsyncMock, return_value=MOCK_CARDDAV_RESPONSE):
        with patch("src.collectors.icloud_contacts.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "0101"
            mock_dt.side_effect = lambda *a, **kw: __import__("datetime").datetime(*a, **kw)
            result = await fetch_todays_birthdays()

    assert len(result) == 0
```

- [ ] **Step 5: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_icloud_contacts.py -v`
Expected: FAIL

- [ ] **Step 6: Implement birthdays collector**

Uses raw HTTP requests to iCloud CardDAV (not the `caldav` library, which only supports CalDAV):

```python
# src/collectors/icloud_contacts.py
import httpx
import vobject
from datetime import datetime
from zoneinfo import ZoneInfo
from src.config import settings

ICLOUD_CARDDAV_URL = "https://contacts.icloud.com"

PROPFIND_BODY = """<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:">
  <d:prop><d:resourcetype/></d:prop>
</d:propfind>"""

REPORT_BODY = """<?xml version="1.0" encoding="utf-8"?>
<card:addressbook-query xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
  <d:prop>
    <card:address-data/>
  </d:prop>
</card:addressbook-query>"""

async def _fetch_all_vcards() -> str:
    """Fetch all vCards from iCloud CardDAV using REPORT method."""
    auth = (settings.icloud_username, settings.icloud_app_password)

    async with httpx.AsyncClient() as client:
        # Step 1: Discover addressbook URL via PROPFIND on principal
        propfind_resp = await client.request(
            "PROPFIND",
            f"{ICLOUD_CARDDAV_URL}/{settings.icloud_username}/carddavhome/card/",
            auth=auth,
            headers={"Content-Type": "application/xml", "Depth": "0"},
            content=PROPFIND_BODY,
        )
        propfind_resp.raise_for_status()

        # Step 2: REPORT to get all vCards
        report_resp = await client.request(
            "REPORT",
            f"{ICLOUD_CARDDAV_URL}/{settings.icloud_username}/carddavhome/card/",
            auth=auth,
            headers={"Content-Type": "application/xml", "Depth": "1"},
            content=REPORT_BODY,
        )
        report_resp.raise_for_status()
        return report_resp.text

async def fetch_todays_birthdays() -> list[dict]:
    tz = ZoneInfo(settings.timezone)
    today = datetime.now(tz)
    today_mmdd = today.strftime("%m%d")

    raw = await _fetch_all_vcards()
    birthdays = []

    # Parse individual vCards from the response
    for vcard_str in raw.split("BEGIN:VCARD"):
        if not vcard_str.strip():
            continue
        try:
            vcard = vobject.readOne("BEGIN:VCARD" + vcard_str)
            if hasattr(vcard, "bday"):
                bday_str = vcard.bday.value.replace("-", "")
                # Handle YYYYMMDD or --MMDD formats
                if len(bday_str) == 8:
                    bday_mmdd = bday_str[4:]
                elif len(bday_str) == 4:
                    bday_mmdd = bday_str
                else:
                    continue

                if bday_mmdd == today_mmdd:
                    birthdays.append({"name": vcard.fn.value})
        except Exception:
            continue

    return birthdays
```

- [ ] **Step 7: Run tests, verify passing**

Run: `python -m pytest tests/test_collectors/test_icloud_cal.py tests/test_collectors/test_icloud_contacts.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/collectors/icloud_cal.py src/collectors/icloud_contacts.py tests/test_collectors/test_icloud_cal.py tests/test_collectors/test_icloud_contacts.py
git commit -m "feat: add iCloud calendar and birthday collectors via CalDAV/CardDAV"
```

---

## Task 6: Commute Collector

**Files:**
- Create: `src/collectors/commute.py`
- Test: `tests/test_collectors/test_commute.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_collectors/test_commute.py
import pytest
from unittest.mock import AsyncMock, patch
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
        mock_client.get.return_value.json.return_value = MOCK_GMAPS_RESPONSE
        mock_client.get.return_value.raise_for_status = lambda: None
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
        mock_client.get.return_value.json.return_value = MOCK_GMAPS_RESPONSE
        mock_client.get.return_value.raise_for_status = lambda: None
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await fetch_commute(-27.57, 151.95, first_meeting_time="09:00")

    assert result["leave_by"] == "08:38"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_commute.py -v`
Expected: FAIL

- [ ] **Step 3: Implement commute collector**

```python
# src/collectors/commute.py
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import settings

DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

async def fetch_commute(lat: float, lon: float, first_meeting_time: str | None = None) -> dict:
    params = {
        "origin": f"{lat},{lon}",
        "destination": settings.work_address,
        "key": settings.google_maps_api_key,
        "departure_time": "now",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(DIRECTIONS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    if data["status"] != "OK" or not data.get("routes"):
        return {"error": "No route found", "duration_seconds": 0, "duration_text": "N/A", "distance_text": "N/A", "leave_by": None}

    leg = data["routes"][0]["legs"][0]
    duration = leg.get("duration_in_traffic", leg["duration"])

    result = {
        "duration_seconds": duration["value"],
        "duration_text": duration["text"],
        "distance_text": leg["distance"]["text"],
        "leave_by": None,
    }

    if first_meeting_time:
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        meeting_hour, meeting_min = map(int, first_meeting_time.split(":"))
        meeting_dt = now.replace(hour=meeting_hour, minute=meeting_min, second=0, microsecond=0)
        leave_dt = meeting_dt - timedelta(seconds=duration["value"])
        result["leave_by"] = leave_dt.strftime("%H:%M")

    return result
```

- [ ] **Step 4: Run tests, verify passing**

Run: `python -m pytest tests/test_collectors/test_commute.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/commute.py tests/test_collectors/test_commute.py
git commit -m "feat: add Google Maps commute collector with leave-by calculation"
```

---

## Task 7: News Collector (RSS)

**Files:**
- Create: `src/collectors/news.py`
- Test: `tests/test_collectors/test_news.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_collectors/test_news.py
import pytest
from unittest.mock import patch, MagicMock
from src.collectors.news import fetch_news, RSS_FEEDS

def _mock_feed(title, entries):
    feed = MagicMock()
    feed.entries = []
    for e in entries:
        entry = MagicMock()
        entry.title = e["title"]
        entry.link = e["link"]
        entry.get.return_value = e.get("summary", "")
        entry.published_parsed = None
        feed.entries.append(entry)
    return feed

def test_rss_feeds_has_all_categories():
    assert "headlines" in RSS_FEEDS
    assert "ai" in RSS_FEEDS
    assert "movies" in RSS_FEEDS
    assert "tesla" in RSS_FEEDS
    assert "stremio" in RSS_FEEDS

@pytest.mark.asyncio
async def test_fetch_news_returns_structured_data():
    mock_feed = _mock_feed("Test Feed", [
        {"title": "AI Breakthrough", "link": "https://example.com/1", "summary": "Big news"},
    ])

    with patch("src.collectors.news.feedparser.parse", return_value=mock_feed):
        result = await fetch_news()

    assert "headlines" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_collectors/test_news.py -v`
Expected: FAIL

- [ ] **Step 3: Implement news collector**

```python
# src/collectors/news.py
import feedparser
from datetime import datetime
from time import mktime

RSS_FEEDS = {
    "headlines": [
        "https://www.abc.net.au/news/feed/2942460/rss.xml",
        "https://www.sbs.com.au/news/feed",
    ],
    "ai": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ],
    "movies": [
        "https://collider.com/feed/",
        "https://screenrant.com/feed/",
    ],
    "tesla": [
        "https://electrek.co/feed/",
        "https://www.teslarati.com/feed/",
    ],
    "stremio": [
        "https://blog.stremio.com/feed/",
    ],
}

MAX_ARTICLES_PER_CATEGORY = 6

async def fetch_news() -> dict[str, list[dict]]:
    result = {}
    for category, urls in RSS_FEEDS.items():
        articles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries:
                    published = None
                    if entry.get("published_parsed"):
                        published = datetime.fromtimestamp(mktime(entry.published_parsed)).isoformat()

                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.get("summary", ""),
                        "published": published,
                        "source": feed.feed.get("title", url),
                    })
            except Exception:
                continue

        # Sort by published date (newest first), None dates go last
        articles.sort(key=lambda a: a["published"] or "", reverse=True)
        result[category] = articles[:MAX_ARTICLES_PER_CATEGORY]

    return result
```

- [ ] **Step 4: Run tests, verify passing**

Run: `python -m pytest tests/test_collectors/test_news.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/news.py tests/test_collectors/test_news.py
git commit -m "feat: add RSS news collector with headlines, AI, movies, Tesla, Stremio feeds"
```

---

## Task 8: Reminders Ingestion Endpoint

**Files:**
- Create: `src/collectors/reminders.py`
- Create: `src/routes/data.py`
- Test: `tests/test_routes/test_data.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_routes/test_data.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_post_reminders_stores_data(client):
    payload = {
        "reminders": [
            {"title": "Buy milk", "due": "2026-03-23T09:00:00"},
            {"title": "Call dentist", "due": "2026-03-23T14:00:00"},
        ]
    }
    resp = client.post(
        "/data/reminders",
        json=payload,
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["stored"] == 2

def test_post_reminders_rejects_bad_token(client):
    resp = client.post(
        "/data/reminders",
        json={"reminders": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_routes/test_data.py -v`
Expected: FAIL

- [ ] **Step 3: Implement bearer auth dependency**

```python
# src/auth/bearer.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from src.config import settings

security = HTTPBearer()

async def verify_bearer(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    if credentials.credentials != settings.api_bearer_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
```

- [ ] **Step 4: Implement reminders model and data route**

```python
# src/collectors/reminders.py
from pydantic import BaseModel

class Reminder(BaseModel):
    title: str
    due: str | None = None

class RemindersPayload(BaseModel):
    reminders: list[Reminder]

# In-memory store, refreshed daily by iOS Shortcut push
_stored_reminders: list[dict] = []
_last_push: str | None = None

def store_reminders(reminders: list[Reminder]) -> int:
    global _stored_reminders, _last_push
    from datetime import datetime
    _stored_reminders = [r.model_dump() for r in reminders]
    _last_push = datetime.now().isoformat()
    return len(_stored_reminders)

def get_reminders() -> list[dict]:
    return _stored_reminders

def get_reminders_last_push() -> str | None:
    return _last_push
```

```python
# src/routes/data.py
from fastapi import APIRouter, Depends
from src.auth.bearer import verify_bearer
from src.collectors.reminders import RemindersPayload, store_reminders

router = APIRouter()

@router.post("/data/reminders")
async def post_reminders(payload: RemindersPayload, _=Depends(verify_bearer)):
    count = store_reminders(payload.reminders)
    return {"stored": count}
```

- [ ] **Step 5: Register route in main.py**

Add to `src/main.py`:
```python
from src.routes.data import router as data_router
app.include_router(data_router)
```

- [ ] **Step 6: Run tests, verify passing**

Run: `python -m pytest tests/test_routes/test_data.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/auth/__init__.py src/auth/bearer.py src/collectors/reminders.py src/routes/__init__.py src/routes/data.py tests/test_routes/__init__.py tests/test_routes/test_data.py src/main.py
git commit -m "feat: add reminders ingestion endpoint with bearer auth"
```

---

## Task 9: Summary API Endpoint

**Files:**
- Create: `src/routes/summary.py`
- Modify: `src/main.py`
- Create: `src/scheduler.py`
- Test: `tests/test_routes/test_summary.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_routes/test_summary.py
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
    assert resp.status_code == 422  # Missing lat/lon

def test_summary_returns_all_sections(client):
    mock_weather = {"current": {"temp": 22}, "hourly": []}
    mock_commute = {"duration_text": "20 mins", "leave_by": "08:40"}
    mock_calendar = [{"subject": "Standup", "start": "09:00", "source": "work"}]
    mock_birthdays = [{"name": "Jane"}]
    mock_news = {"headlines": [], "ai": []}
    mock_reminders = [{"title": "Buy milk"}]
    mock_flagged = [{"subject": "Review report"}]

    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value=mock_weather), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value=mock_commute), \
         patch("src.routes.summary.get_cached_calendar", return_value=mock_calendar), \
         patch("src.routes.summary.get_cached_birthdays", return_value=mock_birthdays), \
         patch("src.routes.summary.get_cached_news", return_value=mock_news), \
         patch("src.routes.summary.get_cached_reminders", return_value=mock_reminders), \
         patch("src.routes.summary.get_cached_flagged", return_value=mock_flagged):

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_routes/test_summary.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scheduler with cache store**

```python
# src/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.config import settings

logger = logging.getLogger(__name__)

# In-memory cache populated by scheduled job
_cache: dict = {
    "calendar": [],
    "birthdays": [],
    "news": {},
    "flagged_emails": [],
    "last_run": None,
    "errors": {},
}

# Per-system health tracking
_system_health: dict = {
    "openweathermap": {"status": "unknown", "last_check": None, "error": None},
    "microsoft_graph": {"status": "unknown", "last_check": None, "error": None},
    "icloud_caldav": {"status": "unknown", "last_check": None, "error": None},
    "icloud_carddav": {"status": "unknown", "last_check": None, "error": None},
    "google_maps": {"status": "unknown", "last_check": None, "error": None},
    "rss_feeds": {"status": "unknown", "last_check": None, "error": None},
    "ios_reminders_push": {"status": "unknown", "last_check": None, "error": None},
    "cloudflare_tunnel": {"status": "unknown", "last_check": None, "error": None},
    "docker_updater": {"status": "unknown", "last_check": None, "error": None},
}

def _update_system_status(system: str, success: bool, error: str | None = None):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(settings.timezone)
    _system_health[system] = {
        "status": "healthy" if success else "error",
        "last_check": datetime.now(tz).isoformat(),
        "error": error,
    }

def get_cached_calendar() -> list:
    return _cache["calendar"]

def get_cached_birthdays() -> list:
    return _cache["birthdays"]

def get_cached_news() -> dict:
    return _cache["news"]

def get_cached_flagged() -> list:
    return _cache["flagged_emails"]

def get_cached_reminders() -> list:
    from src.collectors.reminders import get_reminders
    return get_reminders()

def get_cache_status() -> dict:
    return {"last_run": _cache["last_run"], "errors": _cache["errors"]}

def get_system_health() -> dict:
    """Detailed health of all systems powering the morning briefing."""
    import socket
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(settings.timezone)

    # Check updater sidecar connectivity
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect("/tmp/updater.sock")
        sock.close()
        _system_health["docker_updater"]["status"] = "healthy"
    except Exception:
        _system_health["docker_updater"]["status"] = "unreachable"

    # Check reminders push recency (healthy if data received in last 26 hours)
    from src.collectors.reminders import get_reminders_last_push
    last_push = get_reminders_last_push()
    if last_push:
        _system_health["ios_reminders_push"]["status"] = "healthy"
        _system_health["ios_reminders_push"]["last_check"] = last_push
    else:
        _system_health["ios_reminders_push"]["status"] = "no data received yet"

    all_healthy = all(s["status"] == "healthy" for s in _system_health.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(tz).isoformat(),
        "last_cache_run": _cache["last_run"],
        "systems": _system_health,
    }

async def run_cache_job():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from src.collectors.outlook import fetch_outlook_calendar, fetch_flagged_emails
    from src.collectors.icloud_cal import fetch_icloud_calendar
    from src.collectors.icloud_contacts import fetch_todays_birthdays
    from src.collectors.news import fetch_news

    tz = ZoneInfo(settings.timezone)
    logger.info("Starting scheduled data cache...")

    errors = {}

    try:
        outlook_cal = await fetch_outlook_calendar()
        _update_system_status("microsoft_graph", True)
    except Exception as e:
        outlook_cal = _cache["calendar"]  # Keep stale
        errors["outlook_calendar"] = str(e)
        _update_system_status("microsoft_graph", False, str(e))
        logger.error(f"Outlook calendar failed: {e}")

    try:
        icloud_cal = await fetch_icloud_calendar()
        _update_system_status("icloud_caldav", True)
    except Exception as e:
        icloud_cal = []
        errors["icloud_calendar"] = str(e)
        _update_system_status("icloud_caldav", False, str(e))
        logger.error(f"iCloud calendar failed: {e}")

    try:
        _cache["birthdays"] = await fetch_todays_birthdays()
        _update_system_status("icloud_carddav", True)
    except Exception as e:
        errors["birthdays"] = str(e)
        _update_system_status("icloud_carddav", False, str(e))
        logger.error(f"Birthdays failed: {e}")

    try:
        _cache["news"] = await fetch_news()
        _update_system_status("rss_feeds", True)
    except Exception as e:
        errors["news"] = str(e)
        _update_system_status("rss_feeds", False, str(e))
        logger.error(f"News failed: {e}")

    try:
        _cache["flagged_emails"] = await fetch_flagged_emails()
        # microsoft_graph already updated above — this confirms emails work too
    except Exception as e:
        errors["flagged_emails"] = str(e)
        _update_system_status("microsoft_graph", False, str(e))
        logger.error(f"Flagged emails failed: {e}")

    # Merge calendars and sort by start time
    _cache["calendar"] = sorted(outlook_cal + icloud_cal, key=lambda e: e["start"])
    _cache["last_run"] = datetime.now(tz).isoformat()
    _cache["errors"] = errors

    logger.info(f"Cache job complete. Errors: {len(errors)}")

def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_cache_job,
        "cron",
        hour=settings.cache_schedule_hour,
        minute=settings.cache_schedule_minute,
        id="morning_cache",
    )
    return scheduler
```

- [ ] **Step 4: Implement summary route**

```python
# src/routes/summary.py
from fastapi import APIRouter, Depends, Query
from src.auth.bearer import verify_bearer
from src.collectors.weather import fetch_weather
from src.collectors.commute import fetch_commute
from src.cache import location_cache, TTLCache
from src.scheduler import get_cached_calendar, get_cached_birthdays, get_cached_news, get_cached_reminders, get_cached_flagged, _update_system_status

router = APIRouter()

@router.get("/summary")
async def get_summary(
    lat: float = Query(...),
    lon: float = Query(...),
    _=Depends(verify_bearer),
):
    # Weather with TTL cache
    weather_key = TTLCache.coord_key("weather", lat, lon)
    weather = location_cache.get(weather_key)
    if weather is None:
        try:
            weather = await fetch_weather(lat, lon)
            location_cache.set(weather_key, weather)
            _update_system_status("openweathermap", True)
        except Exception as e:
            weather = {"current": {}, "hourly": [], "error": str(e)}
            _update_system_status("openweathermap", False, str(e))

    # Commute with TTL cache
    commute_key = TTLCache.coord_key("commute", lat, lon)
    commute = location_cache.get(commute_key)
    if commute is None:
        try:
            calendar = get_cached_calendar()
            first_meeting_time = None
            if calendar:
                # Extract HH:MM from first event
                start = calendar[0]["start"]
                first_meeting_time = start[11:16] if len(start) > 16 else None
            commute = await fetch_commute(lat, lon, first_meeting_time)
            location_cache.set(commute_key, commute)
            _update_system_status("google_maps", True)
        except Exception as e:
            commute = {"error": str(e), "duration_text": "N/A", "leave_by": None}
            _update_system_status("google_maps", False, str(e))

    return {
        "weather": weather,
        "commute": commute,
        "calendar": get_cached_calendar(),
        "birthdays": get_cached_birthdays(),
        "news": get_cached_news(),
        "reminders": get_cached_reminders(),
        "flagged_emails": get_cached_flagged(),
    }
```

- [ ] **Step 5: Update main.py to wire everything together**

```python
# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.config import settings
from src.database import init_db
from src.scheduler import create_scheduler, run_cache_job, get_cache_status
from src.routes.summary import router as summary_router
from src.routes.data import router as data_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = create_scheduler()
    scheduler.start()
    # Run cache job on startup in background (non-blocking — don't delay app start if APIs are down)
    import asyncio
    asyncio.create_task(run_cache_job())
    yield
    scheduler.shutdown()

app = FastAPI(title="Morning Briefing", docs_url=None, redoc_url=None, lifespan=lifespan)

app.include_router(summary_router)
app.include_router(data_router)

@app.get("/health")
async def health():
    from src.scheduler import get_system_health
    return get_system_health()
```

- [ ] **Step 6: Run tests, verify passing**

Run: `python -m pytest tests/test_routes/test_summary.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/scheduler.py src/routes/summary.py src/main.py tests/test_routes/test_summary.py
git commit -m "feat: add summary endpoint with scheduler, cache integration, and health check"
```

---

## Task 10: Admin Route

**Files:**
- Create: `src/routes/admin.py`
- Test: `tests/test_routes/test_health.py`, `tests/test_routes/test_admin.py`

Note: The `/health` endpoint is defined in `src/main.py` (Task 9). No separate `src/routes/health.py` file needed.

- [ ] **Step 1: Write health endpoint test**

```python
# tests/test_routes/test_health.py
from fastapi.testclient import TestClient
from src.main import app

def test_health_returns_detailed_system_status():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
    assert "systems" in data
    assert "openweathermap" in data["systems"]
    assert "microsoft_graph" in data["systems"]
    assert "icloud_caldav" in data["systems"]
    assert "icloud_carddav" in data["systems"]
    assert "google_maps" in data["systems"]
    assert "rss_feeds" in data["systems"]
    assert "ios_reminders_push" in data["systems"]
    assert "docker_updater" in data["systems"]
    assert "cloudflare_tunnel" in data["systems"]
    # Each system has status, last_check, error
    for system in data["systems"].values():
        assert "status" in system
        assert "last_check" in system
```

Run: `python -m pytest tests/test_routes/test_health.py -v`
Expected: PASS (already implemented in main.py from Task 9)

- [ ] **Step 2: Write failing test for admin update**

```python
# tests/test_routes/test_admin.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_admin_update_requires_auth(client):
    resp = client.post("/admin/update")
    assert resp.status_code == 403  # No token

def test_admin_update_signals_updater(client):
    with patch("src.routes.admin.signal_updater", return_value=True):
        resp = client.post(
            "/admin/update",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Update initiated"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python -m pytest tests/test_routes/test_admin.py -v`
Expected: FAIL

- [ ] **Step 5: Implement admin route**

```python
# src/routes/admin.py
import socket
import os
from fastapi import APIRouter, Depends, HTTPException
from src.auth.bearer import verify_bearer

router = APIRouter()

UPDATER_SOCKET = "/tmp/updater.sock"

def signal_updater() -> bool:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(UPDATER_SOCKET)
        sock.sendall(b"update")
        sock.close()
        return True
    except Exception:
        return False

@router.post("/admin/update")
async def trigger_update(_=Depends(verify_bearer)):
    if signal_updater():
        return {"message": "Update initiated"}
    raise HTTPException(status_code=503, detail="Updater sidecar not available")
```

- [ ] **Step 6: Register admin route in main.py**

Add to `src/main.py`:
```python
from src.routes.admin import router as admin_router
app.include_router(admin_router)
```

- [ ] **Step 7: Run tests, verify passing**

Run: `python -m pytest tests/test_routes/test_admin.py tests/test_routes/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/routes/admin.py tests/test_routes/test_admin.py tests/test_routes/test_health.py src/main.py
git commit -m "feat: add health check and admin update routes"
```

---

## Task 11: WebAuthn (Face ID) Authentication

**Files:**
- Create: `src/auth/webauthn.py`
- Test: `tests/test_auth/test_webauthn.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_auth/test_webauthn.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_webauthn_register_options(client):
    resp = client.get("/auth/webauthn/register-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "rp" in data

def test_webauthn_authenticate_options_no_credential(client):
    resp = client.get("/auth/webauthn/authenticate-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_auth/test_webauthn.py -v`
Expected: FAIL

- [ ] **Step 3: Implement WebAuthn endpoints**

```python
# src/auth/webauthn.py
import json
import time
from fastapi import APIRouter, HTTPException, Request
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
)
from src.config import settings
from src.database import get_db

router = APIRouter(prefix="/auth/webauthn")

RP_ID = settings.dashboard_domain
RP_NAME = "Morning Briefing"
ORIGIN = f"https://{RP_ID}"

# Temporary challenge store (in production, use session or short-lived cache)
_challenges: dict[str, bytes] = {}

@router.get("/register-options")
async def register_options():
    db = get_db()
    existing = db.execute("SELECT COUNT(*) as c FROM webauthn_credentials").fetchone()
    db.close()
    if existing["c"] > 0:
        raise HTTPException(status_code=409, detail="Credential already registered. Use manage.sh reset-webauthn to clear.")

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=b"morning-user",
        user_name="Nathan",
        user_display_name="Nathan",
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
    )
    _challenges["register"] = options.challenge
    return json.loads(options_to_json(options))

@router.post("/register")
async def register(request: Request):
    body = await request.json()
    try:
        verification = verify_registration_response(
            credential=body,
            expected_challenge=_challenges.pop("register", b""),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = get_db()
    db.execute(
        "INSERT INTO webauthn_credentials (id, public_key, sign_count, created_at) VALUES (?, ?, ?, ?)",
        (verification.credential_id.hex(), verification.credential_public_key, verification.sign_count, time.time()),
    )
    db.commit()
    db.close()
    return {"status": "registered"}

@router.get("/authenticate-options")
async def authenticate_options():
    db = get_db()
    creds = db.execute("SELECT id FROM webauthn_credentials").fetchall()
    db.close()

    allow_credentials = [{"id": bytes.fromhex(c["id"]), "type": "public-key"} for c in creds]

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials if creds else None,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    _challenges["auth"] = options.challenge
    return json.loads(options_to_json(options))

@router.post("/authenticate")
async def authenticate(request: Request):
    body = await request.json()
    cred_id = body.get("id", "")

    db = get_db()
    cred = db.execute("SELECT * FROM webauthn_credentials WHERE id = ?", (cred_id,)).fetchone()
    if not cred:
        db.close()
        raise HTTPException(status_code=401, detail="Unknown credential")

    try:
        verification = verify_authentication_response(
            credential=body,
            expected_challenge=_challenges.pop("auth", b""),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=cred["public_key"],
            credential_current_sign_count=cred["sign_count"],
        )
    except Exception as e:
        db.close()
        raise HTTPException(status_code=401, detail=str(e))

    db.execute("UPDATE webauthn_credentials SET sign_count = ? WHERE id = ?", (verification.new_sign_count, cred_id))
    db.commit()
    db.close()
    return {"status": "authenticated"}
```

- [ ] **Step 4: Register WebAuthn routes in main.py**

Add to `src/main.py`:
```python
from src.auth.webauthn import router as webauthn_router
app.include_router(webauthn_router)
```

- [ ] **Step 5: Run tests, verify passing**

Run: `python -m pytest tests/test_auth/test_webauthn.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/auth/webauthn.py tests/test_auth/__init__.py tests/test_auth/test_webauthn.py src/main.py
git commit -m "feat: add WebAuthn/Face ID registration and authentication"
```

---

## Task 12: Web Dashboard — HTML Shell & Glassmorphism Styles

**Files:**
- Create: `dashboard/index.html`
- Create: `dashboard/css/glass.css`
- Modify: `src/main.py` (mount static files)

- [ ] **Step 1: Create dashboard HTML**

`dashboard/index.html` — single page with:
- Tailwind CSS CDN (`<script src="https://cdn.tailwindcss.com"></script>`)
- Phosphor Icons CDN (`<script src="https://unpkg.com/@phosphor-icons/web"></script>`)
- Custom glassmorphism CSS import
- Container div with card sections matching spec:
  1. Header (greeting, date, location)
  2. Weather card
  3. Commute card
  4. Calendar card
  5. Birthdays card (conditional)
  6. News section (tabbed)
  7. Reminders & flagged emails card
  8. Admin section
- Script imports: `auth.js`, `app.js`, `admin.js`
- WebAuthn gate: auth screen shown first, dashboard hidden until authenticated

Layout: `min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900`, cards use glassmorphism classes.

- [ ] **Step 2: Create glassmorphism CSS**

`dashboard/css/glass.css`:
```css
.glass-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 1rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.glass-card-hover:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.12);
}

.glass-tab {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 0.5rem;
}

.glass-tab.active {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.15);
}

.precip-high {
    color: #60a5fa;
    font-weight: 600;
}

.source-work {
    border-left: 3px solid #818cf8;
}

.source-personal {
    border-left: 3px solid #34d399;
}
```

- [ ] **Step 3: Mount dashboard static files in main.py**

Add to `src/main.py`:
```python
import os
dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")
```

Update the `/dashboard` route to redirect to the static file server.

- [ ] **Step 4: Commit**

```bash
git add dashboard/index.html dashboard/css/glass.css src/main.py
git commit -m "feat: add dashboard HTML shell with glassmorphism styles and Tailwind/Phosphor CDN"
```

---

## Task 13: Dashboard JavaScript — Auth, Data Fetching, Card Rendering

**Files:**
- Create: `dashboard/js/auth.js`
- Create: `dashboard/js/app.js`
- Create: `dashboard/js/admin.js`

- [ ] **Step 1: Create auth.js — WebAuthn client-side**

Handles:
- Check if credential exists (call `/auth/webauthn/authenticate-options`)
- If no credentials: show registration UI, call `/auth/webauthn/register-options`, create credential via `navigator.credentials.create()`, POST to `/auth/webauthn/register`
- If credential exists: call `navigator.credentials.get()` for Face ID, POST to `/auth/webauthn/authenticate`
- On success: hide auth screen, show dashboard, call `loadDashboard()`

- [ ] **Step 2: Create app.js — Data fetching and card rendering**

Handles:
- `loadDashboard()`: get GPS via `navigator.geolocation`, fetch `/summary?lat=X&lon=Y` with bearer token
- Render functions for each card section:
  - `renderHeader(data)` — greeting, date, location (reverse geocode from coords)
  - `renderWeather(data)` — current conditions, hourly ribbon
  - `renderCommute(data)` — drive time, leave-by
  - `renderCalendar(data)` — merged timeline, color-coded work/personal
  - `renderBirthdays(data)` — conditional display
  - `renderNews(data)` — tabbed interface with category switching
  - `renderReminders(data)` — reminders + flagged emails
- Error state rendering if API unreachable
- Phosphor icon mapping for weather conditions

- [ ] **Step 3: Create admin.js — Update button, Face ID, and system health panel**

Handles:
- Update button click → trigger WebAuthn authentication (Face ID) → POST `/admin/update`
- Show loading spinner during update
- Show success/failure message
- **System Health Panel:** Fetches `GET /health` and renders a status grid showing all 9 systems:
  - Each system shows: name, status badge (green `Heartbeat` icon = healthy, amber `Warning` = degraded, red `XCircle` = error), last checked time, error message if any
  - Systems: OpenWeatherMap, Microsoft Graph, iCloud CalDAV, iCloud CardDAV, Google Maps, RSS Feeds, iOS Reminders Push, Cloudflare Tunnel, Docker Updater
  - Overall status banner at top: "All Systems Healthy" (green) or "X Systems Degraded" (amber)
  - Refresh button to re-fetch health status

- [ ] **Step 4: Test in browser manually**

Start dev server: `cd ~/morning-briefing && uvicorn src.main:app --reload --port 8000`
Open: `http://localhost:8000/dashboard`
Verify: auth screen loads, cards render with mock/empty data gracefully

- [ ] **Step 5: Commit**

```bash
git add dashboard/js/auth.js dashboard/js/app.js dashboard/js/admin.js
git commit -m "feat: add dashboard JavaScript — WebAuthn auth, data rendering, admin controls"
```

---

## Task 14: Docker Setup

**Files:**
- Create: `Dockerfile`
- Create: `updater/Dockerfile`
- Create: `updater/updater.sh`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create app Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY dashboard/ dashboard/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create updater sidecar**

```dockerfile
# updater/Dockerfile
FROM docker:cli
RUN apk add --no-cache socat bash
COPY updater.sh /updater.sh
RUN chmod +x /updater.sh
CMD ["/updater.sh"]
```

```bash
# updater/updater.sh
#!/bin/bash
SOCKET="/tmp/updater.sock"
rm -f "$SOCKET"

echo "Updater sidecar listening on $SOCKET"

while true; do
    socat UNIX-LISTEN:"$SOCKET",fork EXEC:"bash -c '
        echo \"Pulling latest image...\"
        docker compose -f /compose/docker-compose.yml pull morning-briefing
        echo \"Recreating app container...\"
        docker compose -f /compose/docker-compose.yml up -d morning-briefing
        echo \"Pruning old images...\"
        docker image prune -f
        echo \"Update complete\"
    '"
done
```

- [ ] **Step 3: Create docker-compose.yml**

```yaml
# docker-compose.yml
version: "3.8"

services:
  morning-briefing:
    build: .
    container_name: morning-briefing
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./data:/app/data
      - /tmp/updater.sock:/tmp/updater.sock
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  updater:
    build: ./updater
    container_name: morning-updater
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /tmp/updater.sock:/tmp/updater.sock
      - ./docker-compose.yml:/compose/docker-compose.yml:ro
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: morning-cloudflared
    restart: unless-stopped
    command: tunnel run
    environment:
      - TUNNEL_TOKEN=${CLOUDFLARE_TUNNEL_TOKEN}
    logging:
      driver: json-file
      options:
        max-size: "5m"
        max-file: "2"
```

- [ ] **Step 4: Test Docker build locally**

Run: `docker compose build`
Expected: Builds successfully

- [ ] **Step 5: Commit**

```bash
git add Dockerfile updater/Dockerfile updater/updater.sh docker-compose.yml
git commit -m "feat: add Docker setup — app, updater sidecar, cloudflared tunnel"
```

---

## Task 15: Install Script & Management CLI

**Files:**
- Create: `install.sh`
- Create: `manage.sh`

- [ ] **Step 1: Create install.sh**

Interactive install script that:
1. Checks OS (Linux/ARM for Pi)
2. Installs Docker + Docker Compose if missing
3. Clones repo to `~/morning-briefing`
4. Prompts for each credential interactively
5. Runs Microsoft device code flow for OAuth
6. Generates random bearer token (`openssl rand -hex 32`)
7. Writes `.env`
8. Runs `docker compose up -d`
9. Waits for health check
10. Prints summary with URLs and bearer token

- [ ] **Step 2: Create manage.sh**

Helper script:
```bash
#!/bin/bash
case "$1" in
    reset-webauthn)
        sqlite3 data/morning.db "DELETE FROM webauthn_credentials;"
        echo "WebAuthn credentials cleared. Re-register on next dashboard visit."
        ;;
    logs)
        docker compose logs -f morning-briefing
        ;;
    restart)
        docker compose restart morning-briefing
        ;;
    status)
        curl -s http://localhost:8000/health | python3 -m json.tool
        ;;
    *)
        echo "Usage: ./manage.sh {reset-webauthn|logs|restart|status}"
        ;;
esac
```

- [ ] **Step 3: Make scripts executable and commit**

```bash
chmod +x install.sh manage.sh
git add install.sh manage.sh
git commit -m "feat: add install script and management CLI"
```

---

## Task 16: Scriptable Widget

**Files:**
- Create: `scriptable/morning-widget.js`

- [ ] **Step 1: Create Scriptable widget**

`scriptable/morning-widget.js` — a Scriptable script that:
- Configuration section at top: `API_URL`, `BEARER_TOKEN` (user fills in)
- Gets current GPS location via `Location.current()`
- Fetches `/summary?lat=X&lon=Y` with bearer token
- Renders medium or large widget:
  - **Medium:** date/time, weather temp + icon, next event, commute "leave by"
  - **Large:** all of medium + more calendar events, precipitation, birthdays
- Semi-transparent background (glassmorphism-style for widgets)
- Tap action: opens `morning.<domain>.com`
- Error state: "Could not connect" with retry icon
- Sends push notification: "Your morning briefing is ready" with subtitle

- [ ] **Step 2: Commit**

```bash
git add scriptable/morning-widget.js
git commit -m "feat: add Scriptable iOS widget template"
```

---

## Task 17: iOS Shortcuts Documentation

**Files:**
- Create: `shortcuts/SETUP.md`

- [ ] **Step 1: Write setup instructions**

`shortcuts/SETUP.md` with step-by-step guides for creating three iOS Shortcuts:

**Shortcut 1: Morning Briefing Trigger (Charger)**
- Automation: "When iPhone is disconnected from power"
- Action: Run Scriptable script "Morning Widget"
- Action: Show notification "Your morning briefing is ready"

**Shortcut 2: Morning Briefing Fallback (6:30am)**
- Automation: "Time of Day" → 6:30am
- Condition: Only if Shortcut 1 hasn't run today
- Action: Same as Shortcut 1

**Shortcut 3: Reminders Push (4:00am)**
- Automation: "Time of Day" → 4:00am
- Action: Find Reminders where "Due Date is Today"
- Action: For each reminder, build JSON array
- Action: POST to `https://morning.<domain>.com/data/reminders` with bearer token header
- Include screenshots or detailed step descriptions

- [ ] **Step 2: Commit**

```bash
git add shortcuts/SETUP.md
git commit -m "docs: add iOS Shortcuts setup instructions"
```

---

## Task 18: Integration Test & Final Wiring

**Files:**
- Modify: `src/main.py` (final wiring check)
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_full_flow_health_to_summary(client):
    """Test that health returns OK and summary endpoint is wired correctly."""
    # Health check
    resp = client.get("/health")
    assert resp.status_code == 200

    # Summary with mocked collectors
    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value={"current": {}, "hourly": []}), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value={"duration_text": "N/A"}), \
         patch("src.routes.summary.get_cached_calendar", return_value=[]), \
         patch("src.routes.summary.get_cached_birthdays", return_value=[]), \
         patch("src.routes.summary.get_cached_news", return_value={}), \
         patch("src.routes.summary.get_cached_reminders", return_value=[]), \
         patch("src.routes.summary.get_cached_flagged", return_value=[]):

        resp = client.get(
            "/summary?lat=-27.57&lon=151.95",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(k in data for k in ["weather", "commute", "calendar", "birthdays", "news", "reminders", "flagged_emails"])

def test_reminders_ingestion_and_retrieval(client):
    """Test that reminders pushed via iOS Shortcut appear in summary."""
    # Push reminders
    client.post(
        "/data/reminders",
        json={"reminders": [{"title": "Test reminder", "due": "2026-03-23T09:00:00"}]},
        headers={"Authorization": "Bearer test-bearer-token"},
    )

    # Verify they appear in summary
    with patch("src.routes.summary.fetch_weather", new_callable=AsyncMock, return_value={"current": {}, "hourly": []}), \
         patch("src.routes.summary.fetch_commute", new_callable=AsyncMock, return_value={}), \
         patch("src.routes.summary.get_cached_calendar", return_value=[]), \
         patch("src.routes.summary.get_cached_birthdays", return_value=[]), \
         patch("src.routes.summary.get_cached_news", return_value={}), \
         patch("src.routes.summary.get_cached_flagged", return_value=[]):

        resp = client.get(
            "/summary?lat=-27.57&lon=151.95",
            headers={"Authorization": "Bearer test-bearer-token"},
        )
        assert resp.json()["reminders"][0]["title"] == "Test reminder"
```

- [ ] **Step 2: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for full API flow"
```

---

## Task 19: Dashboard Staleness Indicators & Error States

**Files:**
- Modify: `dashboard/js/app.js`
- Modify: `src/routes/summary.py` (add `cache_status` to response)

- [ ] **Step 1: Add cache_status to summary response**

Modify `src/routes/summary.py` to include staleness metadata:
```python
from src.scheduler import get_cache_status

# Add to the return dict in get_summary():
    return {
        ...existing fields...,
        "cache_status": get_cache_status(),  # includes last_run and per-source errors
    }
```

- [ ] **Step 2: Add staleness indicators in app.js**

In each card renderer, check `cache_status.errors` for that source. If an error exists, show a subtle indicator:
- Small Phosphor `Warning` icon in card header
- Tooltip or subtitle: "Data may be stale — last updated [time]"
- Use `text-amber-400` for the warning colour

- [ ] **Step 3: Add OAuth failure banner**

If `cache_status.errors` contains `outlook_calendar` with a token refresh error, show a persistent banner at the top of the dashboard:
- "Outlook authentication expired. Please re-run the install script on your Pi to re-authenticate."
- Phosphor icon: `WarningCircle`

- [ ] **Step 4: Commit**

```bash
git add src/routes/summary.py dashboard/js/app.js
git commit -m "feat: add per-card staleness indicators and OAuth failure banner"
```

---

## Task 20: Structured JSON Logging

**Files:**
- Modify: `src/main.py`

- [ ] **Step 1: Configure JSON log formatter**

Add to `src/main.py` before app creation:
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "ts": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        })

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
```

- [ ] **Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add structured JSON logging"
```

---

## Task 21: Cloudflare Access Setup Guide

**Files:**
- Create: `shortcuts/CLOUDFLARE-SETUP.md`

- [ ] **Step 1: Write Cloudflare setup guide**

Step-by-step instructions for:
1. Creating a Cloudflare Tunnel in the dashboard
2. Configuring the tunnel to point to `localhost:8000`
3. Setting up the subdomain (`morning.<domain>.com`)
4. Creating a Cloudflare Access application:
   - Application name: "Morning Briefing"
   - Session duration: 30 days
   - Policy: Allow — email matches `<user's email>`
5. Copying the tunnel token for the install script

- [ ] **Step 2: Commit**

```bash
git add shortcuts/CLOUDFLARE-SETUP.md
git commit -m "docs: add Cloudflare Tunnel and Access setup guide"
```

---

## Task 22: Run Full Suite & Final Commit

- [ ] **Step 1: Run full test suite**

Run: `python -m pytest tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run Docker build test**

Run: `docker compose build`
Expected: Builds without errors

- [ ] **Step 3: Final commit and tag**

```bash
git add -A
git commit -m "chore: final cleanup and project structure"
git tag v0.1.0
```

---

## Notes

- **Dashboard JS (Tasks 12-13)** has no automated tests — these are manually tested in browser. E2E testing (e.g. Playwright) can be added later as a follow-up.
- **Cloudflare Access** (Task 21) is configured via the Cloudflare dashboard, not code — the guide covers the manual steps.
- **Stremio** is treated as its own news category. Confirm the RSS feed URL (`https://blog.stremio.com/feed/`) works during implementation; if not, check for alternative feed paths.
