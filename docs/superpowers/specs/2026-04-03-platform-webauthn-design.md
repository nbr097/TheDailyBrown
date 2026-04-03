# Platform WebAuthn with Admin Page

**Date:** 2026-04-03
**Status:** Approved

## Problem

NordPass (set as default password manager on iPhone) intercepts WebAuthn credential creation and stores passkeys in its own vault. When it serves stale/mismatched credentials back, authentication fails. The previous WebAuthn implementation was removed because of this.

## Solution

Re-implement WebAuthn with `authenticatorAttachment: "platform"` to force the device's built-in authenticator (Secure Enclave / iCloud Keychain), bypassing third-party password managers entirely. Add multi-device support and a dedicated admin page for credential and system management.

## Authentication Flow

1. User visits dashboard (already gated by Cloudflare Access)
2. If no JWT in localStorage (or expired), show auth screen with Face ID button
3. If no credentials registered at all, show registration button instead
4. WebAuthn ceremony uses `authenticatorAttachment: "platform"` + `userVerification: "required"` — forces Secure Enclave, bypasses NordPass
5. Server verifies response, issues JWT (12-hour expiry)
6. Dashboard loads; subsequent visits within 12h skip auth (JWT still valid)

## Multi-Device Support

- No credential limit — each device (iPhone, Mac, iPad) registers its own platform credential
- Server stores all credentials; authentication options include all credential IDs in `allowCredentials`
- The device picks the credential it owns and triggers Face ID / Touch ID
- Device name derived from user agent at registration time (e.g. "iPhone", "Mac Safari")

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    id TEXT PRIMARY KEY,
    public_key BLOB,
    sign_count INTEGER DEFAULT 0,
    device_name TEXT,
    created_at REAL
);
```

Same table name as before, with added `device_name` column.

## API Endpoints

### Restored (with platform fix)

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /auth/webauthn/register-options` | None | Registration options with `authenticatorAttachment: "platform"` |
| `POST /auth/webauthn/register` | None | Verify registration, store credential with device name |
| `GET /auth/webauthn/authenticate-options` | None | Authentication options with all stored credential IDs |
| `POST /auth/webauthn/authenticate` | None | Verify authentication, issue JWT |

### New

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /auth/webauthn/credentials` | Optional bearer | List registered devices (id, device_name, created_at) |
| `DELETE /auth/webauthn/credentials/{id}` | Optional bearer | Delete a specific credential |

## Server Files

### `src/auth/webauthn.py`

Re-created with these changes from the previous implementation:
- `generate_registration_options()` sets `authenticator_selection=AuthenticatorSelectionCriteria(authenticator_attachment=AuthenticatorAttachment.PLATFORM, resident_key=ResidentKeyRequirement.PREFERRED, user_verification=UserVerificationRequirement.REQUIRED)`
- No 1-credential limit — registration always allowed
- Registration stores `device_name` extracted from `User-Agent` header
- Two new endpoints: `GET /auth/webauthn/credentials` and `DELETE /auth/webauthn/credentials/{id}`

### `src/auth/jwt.py`

Re-created — same as before. Creates and verifies JWTs using the bearer token as the signing secret. 12-hour expiry.

### `src/auth/bearer.py`

Updated to accept JWTs again (same as the version before our removal):
- Fast path: exact bearer token match
- Slow path: JWT decode
- `verify_bearer_optional` unchanged — allows unauthenticated access

### `src/database.py`

Re-add `webauthn_credentials` table creation in `init_db()`, now with `device_name TEXT` column.

## Dashboard Files

### `dashboard/index.html`

- Auth screen restored (same structure as before): Face ID button, register section, error display
- Dashboard screen stays `hidden` by default (shown after auth)
- Header gains avatar circle ("NB") on the right side with popover trigger
- System health section **removed** from main dashboard (moved to admin page)
- `auth.js` script tag restored
- New: popover HTML for avatar menu

### `dashboard/admin.html`

New page at `/dashboard/admin.html`:
- Same glassmorphism styling (imports glass.css, Tailwind, Phosphor Icons)
- Back arrow in header linking to `/dashboard/`
- **Registered Devices section:** List of credentials with device name + date, delete button per row, "Register This Device" button at bottom
- **System Health section:** Health grid + update button (moved from index.html)

### `dashboard/js/auth.js`

Re-created — same as before but cleaned up. Handles:
- JWT check on page load
- WebAuthn authenticate flow
- WebAuthn register flow
- `onAuthSuccess()` shows dashboard, calls `loadDashboard()`
- `onSessionExpired()` hides dashboard, shows auth screen

### `dashboard/js/app.js`

- Geolocation fallback stays (our fix)
- Restore auth token header on fetch (`Authorization: Bearer ${authToken}`)
- Restore 401 handling (`onSessionExpired()`)
- Remove `DOMContentLoaded` → `loadDashboard()` auto-call (auth.js handles this)
- Avatar popover: click handler toggles visibility, click-outside closes

### `dashboard/js/admin.js`

Updated:
- Remove dead `reauthenticate()` / `authToken` references (already done)
- Keep health loading and rendering
- Keep update trigger (uses no-auth fetch)

### `dashboard/js/devices.js`

New file for admin page device management:
- `loadDevices()` — fetches `GET /auth/webauthn/credentials`, renders list
- `deleteDevice(id)` — calls `DELETE /auth/webauthn/credentials/{id}`, refreshes list
- `registerDevice()` — triggers WebAuthn registration flow, refreshes list
- Auto-loads on DOMContentLoaded

## Popover Design

The avatar popover is vanilla JS + Tailwind (no React/Radix). Implementation:
- Trigger: circular avatar "NB" in header, `bg-indigo-600`, hover effect
- Popover: absolutely positioned glassmorphism card, appears below-right of avatar
- Animation: fade-in + slight scale (CSS transition)
- Items: "Manage Devices" (links to admin.html), "System Health" (links to admin.html#health), version number
- Click-outside dismisses

## Dependencies

Re-add to `requirements.txt`:
- `webauthn==2.5.0`
- `PyJWT==2.9.0`

## Bearer Auth Summary

| Endpoint | Auth |
|---|---|
| `/summary` | Optional bearer (dashboard + widget both work) |
| `/admin/update` | Optional bearer (dashboard) |
| `/auth/webauthn/*` | None |
| `/auth/webauthn/credentials` | Optional bearer |
| `/auth/webauthn/credentials/{id}` | Optional bearer |
| `/data/reminders` | Mandatory bearer (Shortcuts) |
| `/data/outlook` | Mandatory bearer (Shortcuts) |
| `/health` | None |
| `/dashboard/*` | Static files (Cloudflare Access) |

## What's NOT Changing

- Cloudflare Access as the outer perimeter
- Bearer token auth for programmatic endpoints (widget, Shortcuts)
- All collectors, scheduler, cache logic
- Geolocation fallback in app.js
