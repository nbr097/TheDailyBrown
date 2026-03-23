# Cloudflare Workers KV Secrets Delivery

Store all TheDailyBrown credentials in Cloudflare Workers KV. During install, the Raspberry Pi fetches them in one command using a single-use token. No API keys are pasted in terminals.

All credentials in KV are **encrypted at rest** by Cloudflare.

---

## Prerequisites

- A Cloudflare account with `nicholasbrown.me` (or your domain) added
- Node.js installed on your dev machine

---

## Step 1: Install Wrangler CLI

```bash
npm install -g wrangler
```

## Step 2: Login to Cloudflare

```bash
wrangler login
```

## Step 3: Create KV Namespace

```bash
wrangler kv:namespace create SECRETS
```

This outputs a namespace ID. Copy it.

## Step 4: Update wrangler.toml

Open `cloudflare/wrangler.toml` and paste the namespace ID into the `id` field:

```toml
[[kv_namespaces]]
binding = "SECRETS"
id = "your-namespace-id-here"
```

## Step 5: Populate KV with Credentials

Replace placeholder values with your actual credentials:

```bash
NAMESPACE_ID="your-namespace-id-here"

wrangler kv:key put --namespace-id=$NAMESPACE_ID "OPENWEATHERMAP_API_KEY" "your-openweathermap-key"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "MS_CLIENT_ID" "your-azure-client-id"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "MS_CLIENT_SECRET" "your-azure-client-secret"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "MS_TENANT_ID" "your-azure-tenant-id"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "ICLOUD_USERNAME" "nicho.brown2@gmail.com"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "ICLOUD_APP_PASSWORD" "your-icloud-app-password"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "GOOGLE_MAPS_API_KEY" "your-google-maps-key"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "WORK_ADDRESS" "your-work-address"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "DASHBOARD_DOMAIN" "dashboard.nicholasbrown.me"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "CLOUDFLARE_TUNNEL_TOKEN" "your-tunnel-token"

# Optional (defaults exist):
wrangler kv:key put --namespace-id=$NAMESPACE_ID "CACHE_SCHEDULE_HOUR" "4"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "CACHE_SCHEDULE_MINUTE" "0"
wrangler kv:key put --namespace-id=$NAMESPACE_ID "TIMEZONE" "Australia/Brisbane"
```

`API_BEARER_TOKEN` is auto-generated on first fetch if not set. To set it manually:

```bash
wrangler kv:key put --namespace-id=$NAMESPACE_ID "API_BEARER_TOKEN" "your-token-here"
```

## Step 6: Generate a One-Time Install Token

```bash
INSTALL_TOKEN=$(openssl rand -hex 32)
wrangler kv:key put --namespace-id=$NAMESPACE_ID "INSTALL_TOKEN" "$INSTALL_TOKEN"
echo "Your install token: $INSTALL_TOKEN"
```

Save this token -- you will need it during install on the Pi.

## Step 7: DNS Record

Add a DNS record for the secrets subdomain. Either:

**Option A (Workers Route):** The `wrangler.toml` already has a route for `secrets.nicholasbrown.me/*`. Make sure a DNS record exists (AAAA `secrets` -> `100::` proxied, or CNAME to your workers.dev subdomain).

**Option B (Custom Domain):** In the Cloudflare dashboard, go to Workers & Pages > `thedailybrown-secrets` > Settings > Domains & Routes, and add `secrets.nicholasbrown.me`.

## Step 8: Deploy the Worker

```bash
cd cloudflare/
wrangler deploy
```

## Step 9: Test

```bash
curl -H "Authorization: Bearer $INSTALL_TOKEN" https://secrets.nicholasbrown.me/
```

You should see all credentials in `.env` format.

## Step 10: Install on the Pi

During install (via `install.sh` or manually):

```bash
curl -s -H "Authorization: Bearer $INSTALL_TOKEN" https://secrets.nicholasbrown.me/ > .env
chmod 600 .env
```

The token is single-use. After install, invalidate it:

```bash
curl -s -X DELETE -H "Authorization: Bearer $INSTALL_TOKEN" https://secrets.nicholasbrown.me/
```

(The installer does this automatically.)

## Step 11: Re-deploy or Add a New Pi

Generate a new install token each time:

```bash
INSTALL_TOKEN=$(openssl rand -hex 32)
wrangler kv:key put --namespace-id=$NAMESPACE_ID "INSTALL_TOKEN" "$INSTALL_TOKEN"
echo "New install token: $INSTALL_TOKEN"
```

---

## Security Notes

- All KV values are encrypted at rest by Cloudflare
- Install tokens are single-use and invalidated after the first fetch
- The Worker only responds to requests with a valid Bearer token
- No credentials are stored in git, logs, or terminal history (if using the installer)
- To rotate a credential, update it in KV and re-deploy to the Pi with a new token
