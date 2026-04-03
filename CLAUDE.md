# TheDailyBrown - Deployment Guide for Claude Code

## Project Overview

TheDailyBrown is a personal morning briefing system that runs on a Raspberry Pi. It aggregates weather, Outlook calendar, personal calendar, commute time, birthdays, news (headlines, AI, movies, Tesla, Stremio), Apple Reminders, and flagged Outlook emails into a glassmorphism web dashboard and a Scriptable iOS widget.

**Repo:** https://github.com/nbr097/TheDailyBrown
**Owner:** Nic Brown (nbr097)

## Quick Start

If the user says "set everything up", follow all phases below in order. If they ask for a specific phase, run just that one.

---

## Phase 1: Detect & Prepare Environment

Run these checks first and adapt accordingly:

```bash
# Detect OS and architecture
uname -a
cat /etc/os-release 2>/dev/null
dpkg --print-architecture 2>/dev/null

# Check what's already installed
command -v docker && docker --version
command -v docker compose && docker compose version
command -v git && git --version
command -v python3 && python3 --version
command -v node && node --version
command -v npm && npm --version
```

### Install missing dependencies

**Git** (if missing):
```bash
sudo apt-get update && sudo apt-get install -y git curl
```

**Docker** (if missing):
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# User MUST log out and back in after this for group to take effect
# Or run: newgrp docker
```

**Docker Compose** comes with Docker Engine on modern installs. If `docker compose` doesn't work, install the plugin:
```bash
sudo apt-get install -y docker-compose-plugin
```

**Node.js** (for Claude Code, if missing):
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Claude Code** (if missing):
```bash
npm install -g @anthropic-ai/claude-code
```

---

## Phase 2: Clone & Configure

```bash
cd ~
git clone https://github.com/nbr097/TheDailyBrown.git
cd TheDailyBrown
```

### Option A: Pull credentials from Cloudflare (recommended)

If the secrets Worker has been set up (see `cloudflare/SETUP.md`):

```bash
curl -s -H "Authorization: Bearer <INSTALL_TOKEN>" https://secrets.nicholasbrown.me/ > .env
chmod 600 .env
```

This pulls all credentials from Cloudflare KV in one command. The install token is single-use — it self-invalidates after the first pull.

If this isn't set up, create `.env` manually from `.env.example` (see below).

### Fix install.sh before running

The install.sh has env var names that don't match what the app expects. Before running it, apply these fixes:

1. Update `REPO_URL` to `https://github.com/nbr097/TheDailyBrown.git`
2. Update `INSTALL_DIR` default to `$HOME/TheDailyBrown`
3. The `.env` file it generates uses wrong variable names. The correct mapping is:

| install.sh writes | App expects | Fix |
|---|---|---|
| `BEARER_TOKEN` | `API_BEARER_TOKEN` | Rename |
| `OPENWEATHER_API_KEY` | `OPENWEATHERMAP_API_KEY` | Rename |
| `ICLOUD_EMAIL` | `ICLOUD_USERNAME` | Rename |
| `DESTINATION_ADDRESS` | `WORK_ADDRESS` | Rename |
| `TZ=America/New_York` | `TIMEZONE=Australia/Brisbane` | Rename + fix value |
| (missing) | `CACHE_SCHEDULE_HOUR=4` | Add |
| (missing) | `CACHE_SCHEDULE_MINUTE=0` | Add |
| (missing) | `DASHBOARD_DOMAIN` | Add |
| (missing) | `MS_CLIENT_SECRET` | Add (needed for token refresh) |

**Recommended approach:** Fix the install.sh to generate correct env var names, OR skip install.sh and create `.env` manually from `.env.example`:

```bash
cp .env.example .env
# Then edit .env with actual values
```

### Required API Keys & Credentials

The user will need to provide these. Guide them through each:

1. **OpenWeatherMap** - Free account at https://openweathermap.org/api (One Call API 3.0)
2. **Microsoft 365** - Azure App Registration with delegated permissions (Calendars.Read, Mail.Read). Use device code flow for auth. Client ID and Tenant ID needed.
3. **iCloud** - Apple ID email + app-specific password (generated at https://appleid.apple.com/account/manage - Sign-In & Security - App-Specific Passwords)
4. **Google Maps** - Directions API key from Google Cloud Console (needs billing account, $200/month free credit)
5. **Cloudflare** - Tunnel token (see Phase 4)
6. **Dashboard Domain** - The subdomain they'll use (e.g., `morning.example.com`)

### Generate Bearer Token

```bash
openssl rand -hex 32
```

Save this token - it's needed for the Scriptable widget and iOS Shortcuts.

### Microsoft 365 Device Code Flow

After creating the `.env` with Client ID and Tenant ID, run the device code flow to get initial tokens:

```bash
pip3 install msal
python3 -c "
import msal, json, sys
app = msal.PublicClientApplication(
    '<CLIENT_ID>',
    authority='https://login.microsoftonline.com/<TENANT_ID>'
)
flow = app.initiate_device_flow(scopes=['Calendars.Read', 'Mail.Read'])
print(flow['message'])
result = app.acquire_token_by_device_flow(flow)
if 'access_token' in result:
    print('Refresh token:', result.get('refresh_token', 'N/A'))
else:
    print('Error:', result.get('error_description'))
"
```

The refresh token must be inserted into the SQLite database after the app starts:

```bash
sqlite3 data/morning.db "INSERT OR REPLACE INTO oauth_tokens (provider, access_token, refresh_token, expires_at) VALUES ('microsoft', '', '<REFRESH_TOKEN>', 0);"
```

---

## Phase 3: Deploy

```bash
cd ~/TheDailyBrown

# Build and start all containers
docker compose up -d --build

# Watch logs for startup
docker compose logs -f morning-briefing
# (Ctrl+C to exit logs)

# Verify health
curl -s http://localhost:8000/health | python3 -m json.tool
```

**Expected containers:**
- `morning-briefing` — main app (FastAPI on port 8000)
- `morning-updater` — sidecar for self-updates via dashboard
- `morning-cloudflared` — Cloudflare Tunnel (if token provided)

### Verify the API works

```bash
# Health check
curl http://localhost:8000/health

# Summary endpoint (replace with actual bearer token)
curl -H "Authorization: Bearer <TOKEN>" "http://localhost:8000/summary?lat=-27.57&lon=151.95"
```

---

## Phase 4: Cloudflare Tunnel & Access

Follow `shortcuts/CLOUDFLARE-SETUP.md` for detailed instructions. Summary:

1. Create a tunnel in the Cloudflare Zero Trust dashboard
2. Point it to `http://morning-briefing:8000` (or `http://localhost:8000`)
3. Set up a subdomain (e.g., `morning.yourdomain.com`)
4. Create a Cloudflare Access application with email-based allow policy
5. Copy tunnel token into `.env` as `CLOUDFLARE_TUNNEL_TOKEN`
6. Restart: `docker compose up -d cloudflared`

---

## Phase 5: Verify Complete Deployment

```bash
# Check all containers running
docker compose ps

# Check health endpoint for all 9 systems
curl -s http://localhost:8000/health | python3 -m json.tool

# Test dashboard loads
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/dashboard/
# Should return 200
```

### Post-deploy: iOS Setup (done on the phone, not the Pi)

Tell the user these next steps are on their iPhone:

1. **Scriptable Widget:** Install Scriptable app, paste code from `scriptable/morning-widget.js`, set API_URL and BEARER_TOKEN, add widget to home screen
2. **iOS Shortcuts:** Create 3 automations per `shortcuts/SETUP.md`:
   - Charger disconnect trigger (primary)
   - 6:30am fallback trigger
   - 4:00am reminders push to API
---

## Project Architecture

```
TheDailyBrown/
├── src/
│   ├── main.py              # FastAPI app, lifespan, routes
│   ├── config.py             # Pydantic settings from .env
│   ├── database.py           # SQLite (tokens, WebAuthn credentials)
│   ├── cache.py              # 10-min TTL cache for weather/commute
│   ├── scheduler.py          # APScheduler (4am cron) + system health
│   ├── auth/
│   │   ├── bearer.py         # Bearer token auth for API
│   ├── collectors/
│   │   ├── weather.py        # OpenWeatherMap One Call API
│   │   ├── outlook.py        # Microsoft Graph (calendar + flagged emails)
│   │   ├── icloud_cal.py     # iCloud CalDAV (personal calendar)
│   │   ├── icloud_contacts.py # iCloud CardDAV (birthdays)
│   │   ├── commute.py        # Google Maps Directions API
│   │   ├── news.py           # RSS feeds (5 categories)
│   │   └── reminders.py      # iOS Shortcut push ingestion
│   └── routes/
│       ├── summary.py        # GET /summary?lat=X&lon=Y
│       ├── data.py           # POST /data/reminders
│       ├── admin.py          # POST /admin/update
│       └── webhook.py        # POST /webhook/github (auto-deploy)
├── dashboard/                # Glassmorphism web UI (Tailwind + Phosphor Icons)
├── updater/                  # Docker self-update sidecar
├── scriptable/               # iOS Scriptable widget template
├── shortcuts/                # iOS Shortcuts + Cloudflare setup guides
├── deploy-watcher.sh         # Host-level auto-deploy watcher script
├── deploy-watcher.service    # systemd unit for deploy watcher
├── docker-compose.yml        # 3 containers: app, updater, cloudflared
├── Dockerfile
├── install.sh                # Interactive installer (see Phase 2 notes)
└── manage.sh                 # Management CLI
```

### Key API Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | None | System health for all 9 integrations |
| `GET /summary?lat=X&lon=Y` | Bearer | Full morning briefing JSON |
| `POST /data/reminders` | Bearer | iOS Shortcut pushes reminders |
| `POST /admin/update` | Bearer | Trigger Docker self-update |
| `GET /dashboard/` | Cloudflare Access | Glassmorphism web dashboard |
| `POST /webhook/github` | HMAC (optional) | GitHub push auto-deploy trigger |

### Data Flow

```
4:00am AEST  →  Scheduler caches: calendars, news, birthdays, flagged emails
Phone wakes  →  Scriptable widget sends GPS coords to /summary
Pi returns   →  Weather + commute (live), everything else (cached)
Widget       →  Compact view + push notification
Tap widget   →  Safari → Cloudflare Access → full dashboard
```

---

## Phase 6: Auto-Deploy via GitHub Webhook (Optional)

Push to GitHub and the Pi automatically pulls and rebuilds. No SSH needed.

### How it works

1. GitHub sends a POST to `https://dashboard.nicholasbrown.me/webhook/github` on every push
2. The FastAPI webhook endpoint writes a trigger file to `data/deploy-trigger.json`
3. A systemd service on the Pi host (`deploy-watcher.sh`) polls for that file every 10 seconds
4. When found, it runs `git pull && docker compose up -d --build`

### Setup steps

**1. Add the webhook on GitHub:**
- Go to https://github.com/nbr097/TheDailyBrown/settings/hooks
- Click **Add webhook**
- Payload URL: `https://dashboard.nicholasbrown.me/webhook/github`
- Content type: `application/json`
- Secret: *(optional — must match `GITHUB_WEBHOOK_SECRET` in `.env`)*
- Events: **Just the push event**

**2. (Optional) Set the webhook secret in `.env`:**
```bash
# Generate a secret
openssl rand -hex 32
# Add to .env
echo "GITHUB_WEBHOOK_SECRET=<generated-secret>" >> .env
docker compose restart morning-briefing
```

**3. Install the deploy watcher on the Pi host:**
```bash
# Copy the service file
sudo cp ~/TheDailyBrown/deploy-watcher.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable deploy-watcher
sudo systemctl start deploy-watcher

# Verify it's running
sudo systemctl status deploy-watcher
```

**4. Test it:**
```bash
# Simulate a trigger
echo '{"ref":"refs/heads/main","timestamp":0}' > ~/TheDailyBrown/data/deploy-trigger.json
# Watch the log
tail -f ~/TheDailyBrown/data/deploy.log
```

### Key endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /webhook/github` | HMAC (optional) | Receives GitHub push events |

---

## Common Issues & Troubleshooting

### Port 8000 already in use
```bash
sudo lsof -i :8000
# Kill the conflicting process, or change the port in docker-compose.yml
```

### Docker permission denied
```bash
sudo usermod -aG docker $USER
newgrp docker
# Or log out and back in
```

### ARM architecture issues
The Dockerfile uses `python:3.11-slim` which has ARM builds. If any pip package fails to build on ARM, install build tools:
```bash
sudo apt-get install -y build-essential libffi-dev
```

### AdGuard port conflict
AdGuard likely uses ports 53, 80, 443, 3000. Morning Briefing uses 8000 — no conflict expected. If Cloudflare Tunnel needs port 443, it routes through cloudflared container, not the host.

### Microsoft token expired
```bash
# Re-run the device code flow (see Phase 2)
# Then update the database:
sqlite3 data/morning.db "UPDATE oauth_tokens SET refresh_token='<NEW_TOKEN>' WHERE provider='microsoft';"
docker compose restart morning-briefing
```

### Viewing logs
```bash
./manage.sh logs                              # App logs
docker compose logs -f cloudflared            # Tunnel logs
docker compose logs -f morning-updater        # Updater logs
```

### Reset Face ID credential
```bash
./manage.sh reset-webauthn
```

### SQLite database location
```bash
ls -la data/morning.db
# The data/ directory is volume-mounted, persists across container rebuilds
```

---

## Commands Reference

| Command | Purpose |
|---|---|
| `./manage.sh status` | Health check (all 9 systems) |
| `./manage.sh logs` | Tail app container logs |
| `./manage.sh restart` | Restart app container |
| `docker compose up -d --build` | Rebuild and restart everything |
| `docker compose down` | Stop all containers |
| `docker compose ps` | List running containers |
| `python3 -m pytest tests/ -v` | Run test suite (from repo root) |

---

## Environment Variables Reference

See `.env.example` for the full list. All variables and their purposes:

| Variable | Required | Purpose |
|---|---|---|
| `OPENWEATHERMAP_API_KEY` | Yes | Weather data |
| `MS_CLIENT_ID` | Yes | Microsoft Graph OAuth |
| `MS_CLIENT_SECRET` | No | Not used in device code flow |
| `MS_TENANT_ID` | Yes | Microsoft Graph OAuth |
| `ICLOUD_USERNAME` | Yes | iCloud CalDAV/CardDAV |
| `ICLOUD_APP_PASSWORD` | Yes | iCloud app-specific password |
| `GOOGLE_MAPS_API_KEY` | Yes | Commute/directions |
| `WORK_ADDRESS` | Yes | Commute destination |
| `API_BEARER_TOKEN` | Yes | API authentication |
| `DASHBOARD_DOMAIN` | Yes | WebAuthn RP ID + Cloudflare |
| `CLOUDFLARE_TUNNEL_TOKEN` | No | Cloudflare Tunnel (skip if local only) |
| `GITHUB_WEBHOOK_SECRET` | No | HMAC secret for GitHub webhook verification |
| `CACHE_SCHEDULE_HOUR` | No | Default: 4 (4am) |
| `CACHE_SCHEDULE_MINUTE` | No | Default: 0 |
| `TIMEZONE` | No | Default: Australia/Brisbane |
