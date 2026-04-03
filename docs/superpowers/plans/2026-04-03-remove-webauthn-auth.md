# Remove WebAuthn/FaceID Authentication — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove WebAuthn/passkey/FaceID authentication entirely. Dashboard loads directly behind Cloudflare Access.

**Architecture:** Delete all WebAuthn and JWT code. Simplify bearer auth to raw token only. Strip auth screen from dashboard HTML, show dashboard content immediately. Remove related dependencies.

**Tech Stack:** Python/FastAPI, vanilla JS, SQLite

---

### Task 1: Delete WebAuthn + JWT server code

**Files:**
- Delete: `src/auth/webauthn.py`
- Delete: `src/auth/jwt.py`
- Delete: `tests/test_auth/test_webauthn.py`
- Delete: `tests/test_auth/test_jwt.py` (if exists)
- Modify: `src/main.py:31,72`

- [ ] **Step 1: Remove webauthn router from main.py**

In `src/main.py`, remove the import on line 31:
```python
from src.auth.webauthn import router as webauthn_router
```

And remove the router registration on line 72:
```python
app.include_router(webauthn_router)
```

- [ ] **Step 2: Delete WebAuthn and JWT files**

```bash
rm src/auth/webauthn.py
rm src/auth/jwt.py
rm tests/test_auth/test_webauthn.py
```

If `tests/test_auth/test_jwt.py` exists, delete it too:
```bash
rm -f tests/test_auth/test_jwt.py
```

- [ ] **Step 3: Commit**

```bash
git add -u src/auth/webauthn.py src/auth/jwt.py src/main.py tests/test_auth/test_webauthn.py
git add -u tests/test_auth/test_jwt.py 2>/dev/null || true
git commit -m "feat: remove WebAuthn and JWT server code"
```

---

### Task 2: Simplify bearer auth (remove JWT path)

**Files:**
- Modify: `src/auth/bearer.py`
- Modify: `tests/test_auth/test_bearer.py`

- [ ] **Step 1: Simplify bearer.py to raw token only**

Replace `src/auth/bearer.py` with:
```python
from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config

security = HTTPBearer()


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials
    if token == src.config.settings.api_bearer_token:
        return token
    raise HTTPException(status_code=401, detail="Invalid token")
```

- [ ] **Step 2: Update bearer tests — remove JWT tests**

Replace `tests/test_auth/test_bearer.py` with:
```python
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.database import init_db
from src.main import app


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def test_bearer_token_accepted(client):
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code not in (401, 403)


def test_invalid_token_rejected(client):
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": "Bearer garbage-token"},
    )
    assert resp.status_code == 401


def test_no_auth_header_rejected(client):
    resp = client.get("/summary?lat=-27.57&lon=151.95")
    assert resp.status_code == 403
```

- [ ] **Step 3: Run tests to verify**

```bash
python3 -m pytest tests/test_auth/test_bearer.py -v
```

Expected: 3 tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/auth/bearer.py tests/test_auth/test_bearer.py
git commit -m "feat: simplify bearer auth to raw token only, remove JWT path"
```

---

### Task 3: Remove webauthn_credentials table from database

**Files:**
- Modify: `src/database.py:21-26`

- [ ] **Step 1: Remove webauthn_credentials table creation**

In `src/database.py`, remove these lines from the `init_db` executescript:
```sql
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    id TEXT PRIMARY KEY,
    public_key BLOB,
    sign_count INTEGER DEFAULT 0,
    created_at REAL
);
```

The resulting `init_db` should have only `oauth_tokens`, `cache_status`, and `outlook_cache` tables.

- [ ] **Step 2: Commit**

```bash
git add src/database.py
git commit -m "feat: remove webauthn_credentials table from schema"
```

---

### Task 4: Strip auth screen from dashboard, show content directly

**Files:**
- Delete: `dashboard/js/auth.js`
- Modify: `dashboard/index.html`
- Modify: `dashboard/js/app.js`

- [ ] **Step 1: Delete auth.js**

```bash
rm dashboard/js/auth.js
```

- [ ] **Step 2: Remove auth screen HTML from index.html**

In `dashboard/index.html`:

1. Delete the entire auth screen div (lines 19-46):
```html
<!-- Auth Screen -->
<div id="auth-screen" class="min-h-screen flex items-center justify-center px-4">
    ...
</div>
```

2. On the dashboard-screen div (line 49), remove `hidden` class so it shows immediately:
```html
<div id="dashboard-screen" class="max-w-lg lg:max-w-5xl mx-auto px-4 py-6 space-y-4 lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0">
```

3. Remove the auth.js script tag (line 200):
```html
<script src="/dashboard/js/auth.js"></script>
```

- [ ] **Step 3: Update app.js — remove auth dependencies**

In `dashboard/js/app.js`:

1. In `loadDashboard()` (line 88-91), remove the auth token header logic. Replace:
```javascript
const headers = {};
if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
}

const res = await fetch(`${CONFIG.API_URL}/summary?lat=${lat}&lon=${lon}`, { headers });
```

With:
```javascript
const res = await fetch(`${CONFIG.API_URL}/summary?lat=${lat}&lon=${lon}`);
```

2. Remove the 401 session expired handling (lines 94-97). Replace:
```javascript
if (res.status === 401) {
    onSessionExpired();
    return;
}
```

With nothing (delete these lines).

3. Add auto-load on DOMContentLoaded. At the bottom of app.js, add:
```javascript
// ---------- Auto-load on page ready ----------

window.addEventListener('DOMContentLoaded', () => loadDashboard());
```

- [ ] **Step 4: Verify dashboard loads**

Open http://localhost:8000/dashboard/ — it should show the dashboard immediately with no auth screen.

- [ ] **Step 5: Commit**

```bash
git add -u dashboard/js/auth.js dashboard/index.html dashboard/js/app.js
git commit -m "feat: remove auth screen, dashboard loads directly"
```

---

### Task 5: Remove dependencies from requirements.txt

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Remove webauthn, PyJWT, and cbor2**

Remove these lines from `requirements.txt`:
```
webauthn==2.5.0
PyJWT==2.9.0
cbor2==5.6.5
```

(`cbor2` is a transitive dependency of webauthn, not used directly.)

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "feat: remove webauthn, PyJWT, cbor2 dependencies"
```

---

### Task 6: Clean up manage.sh

**Files:**
- Modify: `manage.sh`

- [ ] **Step 1: Remove reset-webauthn command**

Replace `manage.sh` with:
```bash
#!/bin/bash
case "$1" in
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
        echo "Usage: ./manage.sh {logs|restart|status}"
        ;;
esac
```

- [ ] **Step 2: Commit**

```bash
git add manage.sh
git commit -m "feat: remove reset-webauthn from manage.sh"
```

---

### Task 7: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update architecture tree**

Remove this line from the Project Architecture tree:
```
│   │   └── webauthn.py       # Face ID registration/authentication
```

- [ ] **Step 2: Update API Endpoints table**

Remove this row:
```
| `GET /auth/webauthn/*` | None | Face ID registration/auth |
```

Change the dashboard row from:
```
| `GET /dashboard/` | WebAuthn | Glassmorphism web dashboard |
```
To:
```
| `GET /dashboard/` | Cloudflare Access | Glassmorphism web dashboard |
```

- [ ] **Step 3: Update Data Flow**

Change:
```
Tap widget   →  Safari → Face ID → full dashboard
```
To:
```
Tap widget   →  Safari → Cloudflare Access → full dashboard
```

- [ ] **Step 4: Update Commands Reference**

Remove this row from the Commands Reference table:
```
| `./manage.sh reset-webauthn` | Clear Face ID credentials |
```

- [ ] **Step 5: Remove Face ID registration from Phase 5 iOS Setup**

Remove this line:
```
3. **Face ID Registration:** Open the dashboard URL in Safari, complete WebAuthn registration on first visit
```

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md to reflect WebAuthn removal"
```

---

### Task 8: Delete old WebAuthn design/plan docs

**Files:**
- Delete: `docs/superpowers/plans/2026-03-24-faceid-passkey-auth.md`
- Delete: `docs/superpowers/specs/2026-03-24-faceid-passkey-auth-design.md`

- [ ] **Step 1: Delete old docs (preserved in git history)**

```bash
rm docs/superpowers/plans/2026-03-24-faceid-passkey-auth.md
rm docs/superpowers/specs/2026-03-24-faceid-passkey-auth-design.md
```

- [ ] **Step 2: Commit**

```bash
git add -u docs/superpowers/plans/2026-03-24-faceid-passkey-auth.md docs/superpowers/specs/2026-03-24-faceid-passkey-auth-design.md
git commit -m "docs: remove old FaceID/passkey design docs"
```

---

### Task 9: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: All remaining tests pass. WebAuthn tests are gone. Bearer tests pass with simplified auth.

- [ ] **Step 2: Verify no dangling imports**

```bash
grep -r "webauthn\|from src.auth.jwt" src/ tests/ --include="*.py"
```

Expected: No results.
