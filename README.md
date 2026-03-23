# TheDailyBrown

A personal morning briefing system that runs on a Raspberry Pi. Aggregates weather, calendars, commute, news, birthdays, reminders, and flagged emails into a glassmorphism web dashboard and an iOS home screen widget.

Built to replace an iOS Shortcut that spoke a morning summary to a HomePod -- because waking your partner at 5am is not ideal.

## What It Does

- Pulls data from 7 sources at 4am daily (configurable)
- Serves a JSON API that your phone calls with GPS coordinates
- Returns location-aware weather and commute (works from home, partner's, anywhere)
- Displays a compact summary on an iOS Scriptable widget
- Full detail via a web dashboard secured with Face ID

## Dashboard

Glassmorphism UI with Phosphor Icons. Mobile-first. No emojis.

**Cards:** Weather (current + 8hr forecast) | Commute (drive time + leave-by) | Calendar (Outlook + iCloud merged) | Birthdays | News (Headlines, AI, Movies, Tesla, Stremio) | Reminders & Flagged Emails | System Health

## Data Sources

| Source | Integration |
|---|---|
| Weather | OpenWeatherMap One Call API 3.0 |
| Work Calendar | Microsoft Graph API (Outlook 365) |
| Personal Calendar | iCloud CalDAV |
| Birthdays | iCloud CardDAV |
| Commute | Google Maps Directions API |
| News | RSS (ABC AU, TechCrunch, Collider, Electrek, Stremio) |
| Reminders | iOS Shortcut pushes to API |
| Flagged Emails | Microsoft Graph API |

## Architecture

```
Phone (Scriptable Widget)
    │
    ├── sends GPS coords ──→ Raspberry Pi (Docker)
    │                            ├── morning-briefing  (FastAPI)
    │                            ├── morning-updater   (self-update sidecar)
    │                            └── morning-cloudflared (tunnel)
    │
    └── taps widget ──→ Safari ──→ Face ID ──→ Dashboard
```

- **4am pre-cache:** Calendars, news, birthdays, flagged emails
- **Per-request:** Weather + commute (with 10-min TTL cache, keyed by location)
- **9-system health tracking:** Live status of every integration

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, APScheduler |
| Database | SQLite |
| Dashboard | HTML/CSS/JS, Tailwind CSS (CDN), Phosphor Icons (CDN) |
| Auth | Cloudflare Access + WebAuthn (Face ID) |
| Containers | Docker Compose (3 containers) |
| Tunnel | Cloudflare Tunnel |
| Widget | Scriptable (iOS) |
| Automation | iOS Shortcuts |

## Quick Start

### On your Raspberry Pi

```bash
git clone https://github.com/nbr097/TheDailyBrown.git
cd TheDailyBrown
cp .env.example .env
# Edit .env with your API keys
docker compose up -d --build
```

### Full guided setup

If you have Claude Code installed:
```bash
cd TheDailyBrown
claude
# Say: "set everything up"
# Claude reads CLAUDE.md and walks you through each step
```

Or follow the detailed phases in `CLAUDE.md`.

## Secure Credentials (Cloudflare KV)

Credentials are stored in Cloudflare Workers KV and pulled to the Pi during install via a one-time-use token. No API keys are pasted in terminals or stored in plain text during setup.

See `cloudflare/SETUP.md` for setup instructions.

### On your iPhone

1. Install **Scriptable** from the App Store
2. Copy `scriptable/morning-widget.js` into a new script
3. Add the Scriptable widget to your home screen
4. Create iOS Shortcut automations per `shortcuts/SETUP.md`
5. Open your dashboard URL in Safari to register Face ID

## API

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health` | - | System health (all 9 integrations) |
| `GET /summary?lat=X&lon=Y` | Bearer | Full briefing JSON |
| `POST /data/reminders` | Bearer | Reminders push from iOS |
| `POST /admin/update` | Bearer | Trigger self-update |
| `GET /dashboard/` | WebAuthn | Web dashboard |

## Management

```bash
./manage.sh status          # Health check
./manage.sh logs            # Tail logs
./manage.sh restart         # Restart app
./manage.sh reset-webauthn  # Clear Face ID
```

## Security

- **Network:** Cloudflare Tunnel (no open ports) + Cloudflare Access (email policy)
- **Application:** WebAuthn / Face ID (no passwords)
- **API:** Bearer token authentication
- **Secrets:** `.env` file (never committed), OAuth tokens in SQLite

## Docs

- `CLAUDE.md` — Full deployment guide for Claude Code
- `shortcuts/SETUP.md` — iOS Shortcuts setup
- `shortcuts/CLOUDFLARE-SETUP.md` — Cloudflare Tunnel + Access setup
- `docs/superpowers/specs/` — Design spec
- `docs/superpowers/plans/` — Implementation plan

## License

Personal project. Not licensed for redistribution.
