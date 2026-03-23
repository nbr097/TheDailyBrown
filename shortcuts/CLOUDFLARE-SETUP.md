# Cloudflare Tunnel & Access Setup Guide

This guide walks you through exposing your Morning Briefing instance via Cloudflare Tunnel and protecting it with Cloudflare Access.

---

## Prerequisites

- A Cloudflare account (free tier works)
- A domain added to Cloudflare (DNS managed by Cloudflare)
- Morning Briefing running locally on port 8000

---

## 1. Create a Cloudflare Tunnel

1. Log in to the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com/)
2. Navigate to **Networks** > **Tunnels**
3. Click **Create a tunnel**
4. Select **Cloudflared** as the connector
5. Name your tunnel (e.g., `morning-briefing`)
6. Click **Save tunnel**

---

## 2. Get the Tunnel Token

After creating the tunnel, Cloudflare displays an install command containing your tunnel token:

```
cloudflared service install <YOUR_TUNNEL_TOKEN>
```

Copy the token value (the long string after `install`). You will need this for the `install.sh` script or your `.env` file:

```env
CLOUDFLARE_TUNNEL_TOKEN=<YOUR_TUNNEL_TOKEN>
```

---

## 3. Configure the Tunnel to Point to localhost:8000

1. In the tunnel configuration page, click **Add a public hostname**
2. Configure the route:
   - **Subdomain**: `morning` (or your preferred subdomain)
   - **Domain**: select your domain (e.g., `yourdomain.com`)
   - **Service Type**: `HTTP`
   - **URL**: `localhost:8000`
3. Click **Save hostname**

Your app will be accessible at `https://morning.yourdomain.com`.

---

## 4. Set Up the Subdomain

Cloudflare Tunnel automatically creates CNAME DNS records when you add a public hostname. Verify:

1. Go to the main [Cloudflare dashboard](https://dash.cloudflare.com/)
2. Select your domain > **DNS** > **Records**
3. Confirm a CNAME record exists:
   - **Name**: `morning`
   - **Target**: `<tunnel-id>.cfargotunnel.com`
   - **Proxy status**: Proxied (orange cloud)

If the record was not auto-created, add it manually as a CNAME pointing to your tunnel ID.

---

## 5. Create a Cloudflare Access Application

Protect the dashboard with email-based authentication:

1. Go to [Zero Trust dashboard](https://one.dash.cloudflare.com/) > **Access** > **Applications**
2. Click **Add an application** > **Self-hosted**
3. Configure the application:
   - **Application name**: `Morning Briefing`
   - **Session duration**: `24 hours` (or your preference)
   - **Application domain**: `morning.yourdomain.com`
4. Click **Next**

### Create an Access Policy

5. **Policy name**: `Email Allow List`
6. **Action**: `Allow`
7. **Include rule**:
   - **Selector**: `Emails`
   - **Value**: your email address (e.g., `you@gmail.com`)
8. Optionally add more emails or use **Emails ending in** for a domain
9. Click **Next** > **Add application**

### Bypass for API endpoints

The bearer-token-protected API endpoints need to bypass Access:

10. Go back to the application settings
11. Add a second policy:
    - **Policy name**: `API Bypass`
    - **Action**: `Bypass`
    - **Include rule**:
      - **Selector**: `Path`
      - **Value**: `/summary*`, `/data/*`, `/health`
12. Save

This allows Scriptable widgets and iOS Shortcuts to reach the API with just the bearer token.

---

## 6. Copy the Tunnel Token for install.sh

When running `install.sh`, paste your tunnel token when prompted:

```
Cloudflare Tunnel token (leave blank to skip): <paste token here>
```

Or add it directly to `.env`:

```env
CLOUDFLARE_TUNNEL_TOKEN=eyJhIjoiYWJjZGVmLi4uIiwidCI6Ii4uLiIsInMiOiIuLi4ifQ==
```

The `docker-compose.yml` automatically starts the `cloudflared` container using this token.

---

## Verification

After setup, verify everything works:

```bash
# Check tunnel is connected
docker compose logs cloudflared

# Test external access
curl https://morning.yourdomain.com/health

# Test API with bearer token
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://morning.yourdomain.com/summary?lat=40.7&lon=-74.0"
```

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Tunnel not connecting | Verify `CLOUDFLARE_TUNNEL_TOKEN` in `.env` is correct |
| 502 Bad Gateway | Ensure `morning-briefing` container is running on port 8000 |
| Access login loop | Clear cookies; verify email is in the Access policy |
| API returns 403 | Add Bypass policy for API paths (see step 10-12) |
| DNS not resolving | Wait 1-2 minutes for propagation; check CNAME record exists |
