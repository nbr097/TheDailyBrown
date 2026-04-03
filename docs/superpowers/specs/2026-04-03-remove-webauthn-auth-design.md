# Remove WebAuthn/FaceID Authentication

**Date:** 2026-04-03
**Status:** Approved

## Summary

Remove WebAuthn/passkey/FaceID authentication from the dashboard. Rely on Cloudflare Access as the sole authentication gate for the dashboard. Bearer token auth for API endpoints remains unchanged.

## Motivation

WebAuthn/passkey authentication doesn't work reliably at this stage. Cloudflare Access already gates the dashboard domain with email-based allow policy, making the WebAuthn layer redundant.

## What to Remove

### Files to delete
- `src/auth/webauthn.py` — WebAuthn registration/authentication endpoints
- `tests/test_auth/test_webauthn.py` — WebAuthn tests
- `dashboard/js/auth.js` — Client-side WebAuthn + JWT session management
- `docs/superpowers/plans/2026-03-24-faceid-passkey-auth.md` — Feature plan (preserved in git history)
- `docs/superpowers/specs/2026-03-24-faceid-passkey-auth-design.md` — Feature spec (preserved in git history)

### Files to modify
- `src/main.py` — Remove webauthn router import and registration
- `src/database.py` — Remove `webauthn_credentials` table creation
- `dashboard/index.html` — Remove auth screen, register section, auth error divs; show dashboard content directly; remove auth.js script tag
- `manage.sh` — Remove `reset-webauthn` command
- `requirements.txt` — Remove `py-webauthn==2.5.0` and `PyJWT` (only used for WebAuthn sessions)
- `CLAUDE.md` — Update architecture diagram, API endpoints table, commands reference, data flow description

### Dependencies to remove
- `py-webauthn==2.5.0`
- `PyJWT` (if only used for WebAuthn sessions — verify first)

## What stays unchanged
- Bearer token auth for all API endpoints (`/summary`, `/data/reminders`, `/admin/update`, etc.)
- Cloudflare Access as external authentication gate
- All collectors, scheduler, cache, and data logic
- Cloudflare Tunnel configuration

## Dashboard behavior after
Visiting the dashboard URL loads the briefing content directly. Cloudflare Access controls who can reach the URL.
