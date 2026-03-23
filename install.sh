#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/nbr097/TheDailyBrown.git"
INSTALL_DIR="${INSTALL_DIR:-$HOME/TheDailyBrown}"

# ── Colors ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[+]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[x]${NC} $*"; }

# ── 1. Check / install Docker ────────────────────────────────────────
check_docker() {
    if command -v docker &>/dev/null && command -v docker compose &>/dev/null; then
        info "Docker and Docker Compose detected."
        return
    fi
    warn "Docker not found. Attempting install (Debian/Raspberry Pi)..."
    if ! command -v apt-get &>/dev/null; then
        error "apt-get not found. Please install Docker manually and re-run."
        exit 1
    fi
    sudo apt-get update -qq
    sudo apt-get install -y -qq ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    sudo usermod -aG docker "$USER"
    info "Docker installed. You may need to log out/in for group changes."
}

# ── 2. Clone / locate repo ──────────────────────────────────────────
setup_repo() {
    if [ -f "docker-compose.yml" ] && [ -f "src/main.py" ]; then
        INSTALL_DIR="$(pwd)"
        info "Using current directory: $INSTALL_DIR"
    elif [ -d "$INSTALL_DIR" ]; then
        info "Directory exists: $INSTALL_DIR"
        cd "$INSTALL_DIR"
    else
        info "Cloning repo to $INSTALL_DIR..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
}

# ── 3. Prompt for credentials ───────────────────────────────────────
prompt_credentials() {
    echo ""
    echo "=== Credential Setup ==="
    echo ""

    # ── Cloudflare KV fetch (optional) ──
    read -rp "Do you have a Cloudflare secrets install token? [y/N]: " HAS_CF_TOKEN
    if [[ "$HAS_CF_TOKEN" =~ ^[Yy] ]]; then
        read -rp "Install token: " CF_INSTALL_TOKEN
        read -rp "Secrets URL [https://secrets.nicholasbrown.me]: " CF_SECRETS_URL
        CF_SECRETS_URL="${CF_SECRETS_URL:-https://secrets.nicholasbrown.me}"
        info "Fetching credentials from Cloudflare..."
        if curl -sf -H "Authorization: Bearer $CF_INSTALL_TOKEN" "$CF_SECRETS_URL/" > "$INSTALL_DIR/.env"; then
            chmod 600 "$INSTALL_DIR/.env"
            info ".env fetched from Cloudflare KV."
            # Invalidate the token
            curl -sf -X DELETE -H "Authorization: Bearer $CF_INSTALL_TOKEN" "$CF_SECRETS_URL/" > /dev/null 2>&1 || true
            return
        else
            warn "Failed to fetch from Cloudflare. Falling back to manual entry."
        fi
    fi

    # OpenWeatherMap
    read -rp "OpenWeatherMap API key: " OWM_KEY

    # Microsoft 365 — device code flow
    echo ""
    info "Microsoft 365 setup: we will use MSAL device code flow."
    read -rp "Microsoft 365 Client ID (Azure app registration): " MS_CLIENT_ID
    read -rp "Microsoft 365 Tenant ID [common]: " MS_TENANT_ID
    MS_TENANT_ID="${MS_TENANT_ID:-common}"

    if command -v python3 &>/dev/null; then
        info "Starting MSAL device code flow..."
        MS_TOKENS=$(python3 -c "
import json, sys
try:
    import msal
except ImportError:
    print('SKIP', end='')
    sys.exit(0)
app = msal.PublicClientApplication('${MS_CLIENT_ID}', authority='https://login.microsoftonline.com/${MS_TENANT_ID}')
flow = app.initiate_device_flow(scopes=['Calendars.Read', 'Mail.Read'])
if 'user_code' not in flow:
    print('SKIP', end='')
    sys.exit(0)
print(flow['message'], file=sys.stderr)
result = app.acquire_token_by_device_flow(flow)
if 'access_token' in result:
    print(json.dumps({'access_token': result['access_token'], 'refresh_token': result.get('refresh_token', '')}), end='')
else:
    print('SKIP', end='')
" 2>&1 | tee /dev/stderr | tail -1)
        if [ "$MS_TOKENS" != "SKIP" ] && [ -n "$MS_TOKENS" ]; then
            MS_ACCESS_TOKEN=$(echo "$MS_TOKENS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")
            MS_REFRESH_TOKEN=$(echo "$MS_TOKENS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refresh_token',''))")
            info "Microsoft tokens acquired."
        else
            warn "MSAL flow skipped. Set MS_ACCESS_TOKEN and MS_REFRESH_TOKEN in .env later."
            MS_ACCESS_TOKEN=""
            MS_REFRESH_TOKEN=""
        fi
    else
        warn "Python3 not found for MSAL. Set tokens in .env manually."
        MS_ACCESS_TOKEN=""
        MS_REFRESH_TOKEN=""
    fi

    echo ""
    # Microsoft 365 Client Secret
    read -rp "Microsoft 365 Client Secret (leave blank if not needed): " MS_CLIENT_SECRET

    # iCloud
    read -rp "iCloud email (Apple ID): " ICLOUD_USERNAME
    read -rsp "iCloud app-specific password: " ICLOUD_APP_PASSWORD
    echo ""

    # Google Maps
    read -rp "Google Maps API key: " GOOGLE_MAPS_KEY

    # Work address for commute
    read -rp "Work/destination address for commute: " WORK_ADDRESS

    # Dashboard domain
    read -rp "Dashboard domain (e.g., dashboard.nicholasbrown.me): " DASHBOARD_DOMAIN

    # Cloudflare Tunnel
    read -rp "Cloudflare Tunnel token (leave blank to skip): " CF_TUNNEL_TOKEN

    # Cache schedule
    read -rp "Cache schedule hour [4]: " CACHE_SCHEDULE_HOUR
    CACHE_SCHEDULE_HOUR="${CACHE_SCHEDULE_HOUR:-4}"
    read -rp "Cache schedule minute [0]: " CACHE_SCHEDULE_MINUTE
    CACHE_SCHEDULE_MINUTE="${CACHE_SCHEDULE_MINUTE:-0}"

    # Bearer token
    API_BEARER_TOKEN=$(openssl rand -hex 32)
    info "Generated bearer token: $API_BEARER_TOKEN"
}

# ── 4. Write .env ───────────────────────────────────────────────────
write_env() {
    cat > "$INSTALL_DIR/.env" <<ENVEOF
# TheDailyBrown Configuration — generated $(date -Iseconds)

# Auth
API_BEARER_TOKEN=${API_BEARER_TOKEN}

# OpenWeatherMap
OPENWEATHERMAP_API_KEY=${OWM_KEY}

# Microsoft Graph (Outlook)
MS_CLIENT_ID=${MS_CLIENT_ID}
MS_CLIENT_SECRET=${MS_CLIENT_SECRET}
MS_TENANT_ID=${MS_TENANT_ID}

# iCloud (CalDAV / CardDAV)
ICLOUD_USERNAME=${ICLOUD_USERNAME}
ICLOUD_APP_PASSWORD=${ICLOUD_APP_PASSWORD}

# Google Maps
GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_KEY}
WORK_ADDRESS=${WORK_ADDRESS}

# Dashboard
DASHBOARD_DOMAIN=${DASHBOARD_DOMAIN}

# Cloudflare Tunnel
CLOUDFLARE_TUNNEL_TOKEN=${CF_TUNNEL_TOKEN}

# Schedule & Timezone
CACHE_SCHEDULE_HOUR=${CACHE_SCHEDULE_HOUR}
CACHE_SCHEDULE_MINUTE=${CACHE_SCHEDULE_MINUTE}
TIMEZONE=Australia/Brisbane
ENVEOF
    chmod 600 "$INSTALL_DIR/.env"
    info ".env written to $INSTALL_DIR/.env"
}

# ── 5. Start containers ─────────────────────────────────────────────
start_services() {
    info "Starting services with Docker Compose..."
    cd "$INSTALL_DIR"
    docker compose up -d --build
}

# ── 6. Health check ─────────────────────────────────────────────────
wait_for_health() {
    info "Waiting for health check..."
    for i in $(seq 1 30); do
        if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
            info "Service is healthy!"
            return
        fi
        sleep 2
    done
    warn "Health check timed out. Check logs with: docker compose logs -f morning-briefing"
}

# ── 7. Summary ──────────────────────────────────────────────────────
print_summary() {
    echo ""
    echo "=================================================="
    echo "  Morning Briefing — Installation Complete"
    echo "=================================================="
    echo ""
    echo "  Dashboard:    http://localhost:8000/dashboard/"
    echo "  API Health:   http://localhost:8000/health"
    echo "  Bearer Token: ${API_BEARER_TOKEN}"
    echo ""
    echo "  Management commands:"
    echo "    ./manage.sh status      — health check"
    echo "    ./manage.sh logs        — tail app logs"
    echo "    ./manage.sh restart     — restart app"
    echo "    ./manage.sh reset-webauthn — clear Face ID"
    echo ""
    if [ -n "$CF_TUNNEL_TOKEN" ]; then
        echo "  Cloudflare Tunnel is configured."
    else
        echo "  Cloudflare Tunnel not configured. See shortcuts/CLOUDFLARE-SETUP.md"
    fi
    echo ""
    echo "  Store your bearer token securely!"
    echo "=================================================="
}

# ── Main ─────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "=== Morning Briefing Installer ==="
    echo ""
    check_docker
    setup_repo
    prompt_credentials
    write_env
    start_services
    wait_for_health
    print_summary
}

main "$@"
