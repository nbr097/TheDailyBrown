# Morning Briefing System — Design Spec

## Overview

A personal morning briefing system that aggregates weather, calendars, commute, news, birthdays, and reminders into a glanceable iOS widget and a full web dashboard. Replaces an existing iOS Shortcut that spoke a summary to a HomePod.

### Problem Statement

The existing iOS Shortcut has three limitations:
1. Audio output wakes a sleeping partner
2. Locked to home WiFi — doesn't work at partner's house
3. Limited data sources — no work calendar, news, commute, or reminders

### Goals

- Silent, visual morning briefing available on the phone home screen
- Works from any location (home, partner's house, travel)
- Aggregates: weather, Outlook calendar, personal calendar, commute, birthdays, news, reminders, flagged emails
- Clean, modern glassmorphism UI with Phosphor Icons
- Dead-simple deployment and maintenance on existing Raspberry Pi

---

## System Architecture

### Three Layers

**1. Data Engine (Python, Raspberry Pi, Docker)**
Scheduled service runs at 4:00am AEST daily. Collects data from all sources and caches locally. Uses APScheduler internally (not system cron) — everything stays inside Docker. Timezone: `Australia/Brisbane`.

**2. API Layer (FastAPI, same container)**
Serves cached data with dynamic location-aware enrichment:
- `GET /summary?lat=X&lon=Y` — full briefing as JSON (weather and commute calculated from provided coords)
- `GET /dashboard` — serves the web dashboard
- `POST /admin/update` — signals the updater sidecar to pull latest image and restart the app container
- `GET /health` — container status, last cache time, per-source health

Pre-cached data (news, calendars, birthdays, reminders) is served from cache. Location-sensitive data (weather, commute) is fetched/calculated per request using the coordinates sent by the phone. Weather and commute responses are cached with a 10-minute TTL keyed by rounded coordinates to avoid redundant API calls.

**3. Display Layer (two consumers)**
- **Scriptable widget** — compact home screen widget, taps open the dashboard
- **Web dashboard** — `morning.<userdomain>.com`, full detail view

### Data Flow

```
4:00am AEST → Pi fetches & caches: calendars, news, birthdays, reminders, flagged emails
                    ↓
Phone wakes up → iOS Shortcut automation fires
                    ↓
Scriptable widget → sends GPS coords to Pi API
                    ↓
Pi returns JSON → weather + commute calculated dynamically from coords
                → cached data (calendars, news, etc.) included
                    ↓
Widget renders compact view
Push notification: "Your morning briefing is ready"
                    ↓
User taps widget → Safari opens morning.<domain>.com → Face ID → full dashboard
```

---

## Data Sources & Integrations

### Weather — OpenWeatherMap API
- Free tier
- Current conditions + hourly forecast + precipitation chance
- Called dynamically per request with phone GPS coordinates
- Phosphor icons: `Sun`, `Cloud`, `CloudRain`, `Thermometer`, `Drop`, `Wind`

### Outlook Calendar — Microsoft Graph API
- OAuth2 using **device code flow** (Pi is headless — install script displays a code, you authenticate on your phone/laptop at microsoft.com/devicelogin)
- Pulls today's events: title, time, location, online meeting link
- Refresh token stored in local SQLite database on Pi
- Phosphor icons: `CalendarBlank`, `VideoCamera`

### Personal Calendar — Apple Calendar via CalDAV
- Connects to iCloud CalDAV endpoint
- Uses app-specific password (prompted during install)
- Merged with Outlook into a single timeline on the dashboard
- Phosphor icon: `CalendarBlank` (color-coded to distinguish from work)

### Commute — Google Maps Directions API
- Uses $200/month free credit (one request/day costs ~$0.005/day — well within free credit, but requires a billing-enabled Google Cloud account)
- Destination from `WORK_ADDRESS` env var (default: 305 Taylor St, Wilsonton QLD 4350)
- Origin: phone GPS coordinates sent per request
- Returns drive time with current traffic conditions
- Calculates "leave by" time: first meeting time minus commute duration
- Phosphor icons: `Car`, `Clock`, `NavigationArrow`

### Birthdays — Apple Contacts via CardDAV
- iCloud CardDAV endpoint (same auth as calendar)
- Checks for contacts with today's birthday
- Phosphor icon: `Gift`

### News — RSS Feeds
- No API key required, more reliable long-term than NewsAPI
- Categories and suggested sources:
  - **Headlines:** ABC News Australia, SBS News
  - **AI:** TechCrunch AI, The Verge AI
  - **Movies:** Collider, Screen Rant
  - **Tesla:** Electrek, Teslarati
-**Stremio** https://blog.stremio.com (sort my latest date first)
- 5-6 articles per category
- Phosphor icons: `Newspaper`, `Robot`, `FilmSlate`, `Lightning`

### Reminders — iOS Shortcut Push (Fallback-First Approach)
- Apple Reminders are not reliably accessible via CalDAV (proprietary protocol, progressively locked down)
- **Primary method:** An iOS Shortcut automation runs daily at 4:00am, fetches today's reminders using the native "Find Reminders" action, and POSTs the data as JSON to the Pi API (`POST /data/reminders`)
- **Fallback exploration:** During implementation, attempt CalDAV VTODO access via `pyicloud` — if it works reliably, use it instead and retire the Shortcut push
- Phosphor icon: `CheckSquare`

### Flagged Emails — Microsoft Graph API
- Same OAuth auth as Outlook Calendar
- Pulls flagged/important emails
- Phosphor icon: `Flag`

---

## UI Design

### Design System

- **Style:** Glassmorphism — frosted glass cards, backdrop blur, semi-transparent borders, soft shadows
- **Background:** Dark with subtle gradient
- **Text:** Light
- **Icons:** Phosphor Icons throughout (no emojis anywhere)
- **Layout:** Mobile-first, responsive

### Scriptable Widget (iOS Home Screen)

Medium-size widget but can be resized into a large-size widget. Compact layout:
- **Top row:** Current time, date, location name
- **Middle row:** Weather temp + condition icon, precipitation chance
- **Bottom row:** Next calendar event + commute time, "leave by" time
- **Background:** Semi-transparent frosted glass panel
- **Tap action:** Opens `morning.<domain>.com`

### Push Notification

Triggered by iOS Shortcut automation:
- **Primary trigger:** Phone removed from charger
- **Fallback trigger:** Time-of-day automation at 6:30am (in case phone wasn't on charger overnight)
- Title: "Your morning briefing is ready"
- Subtitle: Weather summary + first meeting

### Web Dashboard (`morning.<domain>.com`)

Mobile-first single-page layout. All content in glassmorphism cards. Scrollable, top to bottom:

**1. Header**
- Greeting: "Good Morning, Nathan" (time-appropriate)
- Date, location
- Phosphor icon: `SunHorizon`

**2. Weather Card**
- Current temp, feels-like, condition description
- Hourly forecast ribbon (next 8 hours)
- Precipitation chance highlighted if > 30%
- Icons: `Thermometer`, `Drop`, `Wind`, weather-appropriate condition icons

**3. Commute Card**
- Drive time with current traffic
- "Leave by" time (derived from first meeting minus commute)
- Destination: 305 Taylor St, Wilsonton
- Icons: `Car`, `Clock`

**4. Calendar Card**
- Merged timeline: Outlook (work) + Apple Calendar (personal)
- Color-coded: work vs personal
- Each event: time, title, location or Teams link
- Icons: `CalendarBlank`, `VideoCamera`, `MapPin`

**5. Birthdays Card** (conditional — only renders if birthdays exist today)
- Contact name(s) with birthday today
- Icon: `Gift`

**6. News Section**
- Tabbed interface: Headlines | AI | Movies | Tesla
- Each tab: 5-6 article cards with source name, title, brief excerpt
- Tap article to open in browser
- Icons per tab: `Newspaper`, `Robot`, `FilmSlate`, `Lightning`

**7. Reminders & Flagged Emails Card**
- Two sub-sections within one card
- Reminders: today's due items from Apple Reminders
- Flagged: flagged Outlook emails with subject line
- Icons: `CheckSquare`, `Flag`

**8. Admin Section (bottom)**
- Update button: pulls latest Docker image and restarts (behind Face ID confirmation)
- Last updated timestamp

---

## Security

### Network Layer — Cloudflare Tunnel + Access

- `cloudflared` runs as a sidecar Docker container
- Exposes the dashboard on `morning.<domain>.com` without opening router ports
- Cloudflare Access policy: restricted to user's email address
- Free tier

### Application Layer — WebAuthn / Face ID

- Dashboard requires biometric authentication via Web Authentication API
- On Safari/iOS, this triggers Face ID natively
- Credential stored on-device, tied to the domain
- No passwords
- **Registration flow:** On first visit (protected by Cloudflare Access), the dashboard presents a one-time setup page to register a WebAuthn credential. Only one credential is allowed. Re-registration requires clearing via the Pi CLI (`./manage.sh reset-webauthn`).

### API Authentication

- Scriptable widget uses a bearer token to call the API
- Token generated during install, stored in Scriptable script
- Token can be regenerated by re-running the install script

### Secrets Management

- All API keys, OAuth tokens, credentials stored in `.env` file on Pi
- `.env` created interactively during install — never committed to git
- OAuth refresh tokens (Microsoft) stored in local SQLite database
- `.env` and SQLite database excluded from version control via `.gitignore`

---

## Deployment

### Install Script

Single command:
```bash
curl -sSL https://raw.githubusercontent.com/<user>/morning-briefing/main/install.sh | bash
```

The script:
1. Checks for Docker & Docker Compose — installs if missing
2. Clones the repository to `~/morning-briefing`
3. Walks through credential setup interactively:
   - OpenWeatherMap API key
   - Microsoft 365 OAuth via device code flow (displays a code, you authenticate on your phone/laptop at microsoft.com/devicelogin)
   - iCloud app-specific password (for calendar, contacts, reminders)
   - Google Maps API key
   - Cloudflare Tunnel token
4. Generates `.env` file and bearer token
5. Runs `docker compose up -d`
6. Verifies container health
7. Prints summary: local API URL, public dashboard URL, bearer token for Scriptable

### Docker Compose Stack

Three containers:
- `morning-briefing` — Python app (FastAPI + APScheduler + dashboard static files)
- `cloudflared` — Cloudflare Tunnel sidecar
- `updater` — Lightweight sidecar with Docker socket access. Listens for update requests from the app container via a shared Unix socket. Pulls latest image, recreates the app container, and prunes old images. This solves the problem of a container not being able to restart itself.

### Updates

Dashboard button (under Admin section):
- Triggers `POST /admin/update` endpoint
- Requires Face ID confirmation
- Pulls latest Docker image, restarts the container
- Cleans up old images to save SD card space

### iOS Setup (post-install)

1. Install Scriptable from App Store
2. Create new script, paste provided widget code
3. Add Scriptable widget to home screen (medium size)
4. Configure bearer token and API URL in the script
5. Create iOS Shortcut automation: "When phone is disconnected from charger" → Run Scriptable script (refreshes widget + sends notification)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.11+, FastAPI, APScheduler |
| Database | SQLite (OAuth tokens, WebAuthn credentials) |
| Dashboard | HTML, CSS, vanilla JS (no framework — keeps it light) |
| Icons | Phosphor Icons (CDN) |
| Container | Docker, Docker Compose |
| Tunnel | Cloudflare Tunnel (cloudflared) |
| Auth | Cloudflare Access + WebAuthn |
| Widget | Scriptable (iOS) |
| Automation | iOS Shortcuts |

---

## Configuration

### Environment Variables (`.env`)

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
DASHBOARD_DOMAIN=morning.<yourdomain>.com

# Cloudflare
CLOUDFLARE_TUNNEL_TOKEN=
```

---

## Error Handling

- If a data source fails during the 4am cache, the system logs the error and serves stale data with a "last updated" indicator on the affected card
- If the Pi is unreachable, the Scriptable widget shows a "Could not connect" state
- OAuth token refresh failures trigger a notification (push via Scriptable) prompting re-authentication
- Dashboard shows per-card staleness indicators when data is older than expected

---

## Operational

### Logging
- Docker log driver configured with `max-size: 10m` and `max-file: 3` to prevent SD card fill
- Application logs structured as JSON for easy parsing

### Scriptable Widget Template
- Provided as `scriptable/morning-widget.js` in the repo
- Install script prints the file path and instructions for copying to Scriptable
- Widget code handles: API calls with bearer token, GPS location, error states, tap-to-open URL
