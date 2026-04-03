# Platform WebAuthn with Admin Page — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-implement WebAuthn authentication using platform authenticators (bypassing NordPass), with multi-device support and a dedicated admin page for device/health management.

**Architecture:** Server-side WebAuthn with `authenticatorAttachment: "platform"` forces iCloud Keychain / Secure Enclave. JWT sessions (12h) avoid repeated biometric prompts. New admin page houses device management and system health (moved from main dashboard). Avatar popover in header provides navigation.

**Tech Stack:** Python/FastAPI, py-webauthn 2.5.0, PyJWT, vanilla JS, Tailwind CSS, Phosphor Icons

## File Structure

**Create:**
- `src/auth/webauthn.py` — WebAuthn registration, authentication, credential management endpoints
- `src/auth/jwt.py` — JWT creation and verification
- `dashboard/js/auth.js` — Client-side WebAuthn flows + JWT session management
- `dashboard/js/devices.js` — Admin page device management UI
- `dashboard/admin.html` — Admin page (devices + system health)
- `tests/test_auth/test_webauthn.py` — WebAuthn endpoint tests

**Modify:**
- `requirements.txt` — Re-add webauthn, PyJWT
- `src/database.py` — Re-add webauthn_credentials table with device_name
- `src/main.py` — Register webauthn router
- `src/auth/bearer.py` — Add JWT fallback path
- `dashboard/index.html` — Add auth screen, avatar popover, remove admin section
- `dashboard/js/app.js` — Restore auth token headers, 401 handling, remove auto-load
- `dashboard/js/admin.js` — No changes needed (already standalone, will be loaded on admin page)
- `dashboard/css/glass.css` — Add popover and avatar styles
- `manage.sh` — Re-add reset-webauthn command
- `tests/test_auth/test_bearer.py` — Add JWT acceptance test
- `tests/test_database.py` — Assert webauthn_credentials table exists
- `CLAUDE.md` — Update architecture, endpoints, commands

---

### Task 1: Re-add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add webauthn and PyJWT to requirements.txt**

Add these two lines after `pydantic-settings==2.8.1`:
```
webauthn==2.5.0
PyJWT==2.9.0
```

The full `requirements.txt` should be:
```
fastapi==0.115.12
uvicorn[standard]==0.34.2
apscheduler==3.11.0
httpx==0.28.1
feedparser==6.0.11
caldav==1.4.0
vobject==0.9.8
msal==1.32.0
python-dotenv==1.1.0
pydantic-settings==2.8.1
webauthn==2.5.0
PyJWT==2.9.0
pytest==8.3.5
pytest-asyncio==0.25.3
```

- [ ] **Step 2: Commit**

```bash
git add requirements.txt
git commit -m "feat: re-add webauthn and PyJWT dependencies"
```

---

### Task 2: Re-add webauthn_credentials table with device_name

**Files:**
- Modify: `src/database.py:14-32`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Update test to assert webauthn_credentials table exists**

In `tests/test_database.py`, add the assertion after `assert "cache_status" in table_names`:
```python
            assert "webauthn_credentials" in table_names
```

The full test file should be:
```python
import os
import tempfile
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
            assert "cache_status" in table_names
            assert "webauthn_credentials" in table_names
            conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_database.py -v`
Expected: FAIL — `webauthn_credentials` not in table list.

- [ ] **Step 3: Add webauthn_credentials table to init_db**

In `src/database.py`, add the table creation inside the `executescript` call, after the `outlook_cache` table:
```sql
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            public_key BLOB,
            sign_count INTEGER DEFAULT 0,
            device_name TEXT,
            created_at REAL
        );
```

The full `init_db` function should be:
```python
def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS oauth_tokens (
            provider TEXT PRIMARY KEY,
            access_token TEXT,
            refresh_token TEXT,
            expires_at REAL
        );
        CREATE TABLE IF NOT EXISTS cache_status (
            source TEXT PRIMARY KEY,
            last_success REAL,
            last_error TEXT,
            data TEXT
        );
        CREATE TABLE IF NOT EXISTS outlook_cache (
            key TEXT PRIMARY KEY,
            data TEXT,
            updated_at REAL
        );
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            public_key BLOB,
            sign_count INTEGER DEFAULT 0,
            device_name TEXT,
            created_at REAL
        );
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_database.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: re-add webauthn_credentials table with device_name column"
```

---

### Task 3: Create JWT module

**Files:**
- Create: `src/auth/jwt.py`

- [ ] **Step 1: Create src/auth/jwt.py**

```python
from __future__ import annotations

import time

import jwt as pyjwt

import src.config


def _secret() -> str:
    return src.config.settings.api_bearer_token


def create_jwt(subject: str, expires_hours: float = 12) -> str:
    now = time.time()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_hours * 3600,
    }
    return pyjwt.encode(payload, _secret(), algorithm="HS256")


def verify_jwt(token: str) -> dict:
    return pyjwt.decode(token, _secret(), algorithms=["HS256"])
```

- [ ] **Step 2: Commit**

```bash
git add src/auth/jwt.py
git commit -m "feat: re-add JWT creation and verification module"
```

---

### Task 4: Add JWT fallback to bearer auth

**Files:**
- Modify: `src/auth/bearer.py`
- Modify: `tests/test_auth/test_bearer.py`

- [ ] **Step 1: Add JWT test cases to test_bearer.py**

Add these two tests to `tests/test_auth/test_bearer.py`:
```python
def test_jwt_accepted(client):
    """JWT from Face ID auth should work."""
    from src.auth.jwt import create_jwt
    token = create_jwt("nic")
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code not in (401, 403)


def test_expired_jwt_rejected(client):
    from src.auth.jwt import create_jwt
    token = create_jwt("nic", expires_hours=-1)
    resp = client.get(
        "/summary?lat=-27.57&lon=151.95",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_auth/test_bearer.py -v`
Expected: `test_jwt_accepted` FAILS (JWT not accepted), `test_expired_jwt_rejected` may pass or fail.

- [ ] **Step 3: Add JWT fallback to bearer.py**

Replace `src/auth/bearer.py` with:
```python
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config
from src.auth.jwt import verify_jwt

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials

    # Fast path: exact bearer token match (widget, shortcuts)
    if token == src.config.settings.api_bearer_token:
        return token

    # Slow path: try JWT decode (dashboard after Face ID)
    try:
        verify_jwt(token)
        return token
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token")


async def verify_bearer_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional),
) -> Optional[str]:
    """Allow unauthenticated access (dashboard behind Cloudflare Access).
    If a token is provided, it must be valid."""
    if credentials is None:
        return None
    token = credentials.credentials

    if token == src.config.settings.api_bearer_token:
        return token

    try:
        verify_jwt(token)
        return token
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_auth/test_bearer.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/auth/bearer.py tests/test_auth/test_bearer.py
git commit -m "feat: add JWT fallback to bearer auth for dashboard sessions"
```

---

### Task 5: Create WebAuthn server endpoints

**Files:**
- Create: `src/auth/webauthn.py`
- Modify: `src/main.py:30-34,68-71`
- Create: `tests/test_auth/test_webauthn.py`

- [ ] **Step 1: Write WebAuthn tests**

Create `tests/test_auth/test_webauthn.py`:
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


def test_register_options_returns_platform(client):
    resp = client.get("/auth/webauthn/register-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data
    assert "rp" in data
    assert data["authenticatorSelection"]["authenticatorAttachment"] == "platform"
    assert data["authenticatorSelection"]["userVerification"] == "required"


def test_authenticate_options(client):
    resp = client.get("/auth/webauthn/authenticate-options")
    assert resp.status_code == 200
    data = resp.json()
    assert "challenge" in data


def test_list_credentials_empty(client):
    resp = client.get("/auth/webauthn/credentials")
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_credential_not_found(client):
    resp = client.delete("/auth/webauthn/credentials/nonexistent")
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_auth/test_webauthn.py -v`
Expected: Collection error — `src.auth.webauthn` doesn't exist yet.

- [ ] **Step 3: Create src/auth/webauthn.py**

```python
from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Request
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

import src.config
from src.auth.jwt import create_jwt
from src.database import get_db

router = APIRouter()


def _rp_id() -> str:
    return src.config.settings.dashboard_domain


def _origin() -> str:
    return f"https://{_rp_id()}"


# In-memory challenge store — keeps recent challenges valid (single-user app)
_valid_challenges: set[bytes] = set()


def _get_stored_credentials() -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, public_key, sign_count, device_name, created_at FROM webauthn_credentials"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _parse_device_name(user_agent: str) -> str:
    if not user_agent:
        return "Unknown"
    if "iPhone" in user_agent:
        return "iPhone"
    if "iPad" in user_agent:
        return "iPad"
    if "Macintosh" in user_agent:
        match = re.search(r"(Safari|Chrome|Firefox|Edge)", user_agent)
        return f"Mac {match.group(1)}" if match else "Mac"
    return "Unknown"


@router.get("/auth/webauthn/register-options")
async def register_options():
    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name="Morning Briefing",
        user_name="nic",
        user_display_name="Nic",
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c["id"] + "=="))
            for c in _get_stored_credentials()
        ],
    )

    _valid_challenges.add(options.challenge)
    return json.loads(options_to_json(options))


@router.post("/auth/webauthn/register")
async def register(request: Request):
    body = await request.json()
    user_agent = request.headers.get("user-agent", "")

    import json as _json
    client_data = _json.loads(base64.urlsafe_b64decode(body["response"]["clientDataJSON"] + "=="))
    challenge_bytes = base64.urlsafe_b64decode(client_data["challenge"] + "==")

    if challenge_bytes not in _valid_challenges:
        raise HTTPException(status_code=400, detail="No registration in progress")
    _valid_challenges.discard(challenge_bytes)

    try:
        verification = verify_registration_response(
            credential=body,
            expected_challenge=challenge_bytes,
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    device_name = _parse_device_name(user_agent)

    conn = get_db()
    conn.execute(
        "INSERT INTO webauthn_credentials (id, public_key, sign_count, device_name, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            base64.urlsafe_b64encode(verification.credential_id).rstrip(b"=").decode(),
            verification.credential_public_key,
            verification.sign_count,
            device_name,
            time.time(),
        ),
    )
    conn.commit()
    conn.close()

    return {"verified": True, "token": create_jwt("nic")}


@router.get("/auth/webauthn/authenticate-options")
async def authenticate_options():
    creds = _get_stored_credentials()

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64.urlsafe_b64decode(c["id"] + "==")) for c in creds
    ]

    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    _valid_challenges.add(options.challenge)
    return json.loads(options_to_json(options))


@router.post("/auth/webauthn/authenticate")
async def authenticate(request: Request):
    body = await request.json()

    import json as _json
    client_data = _json.loads(base64.urlsafe_b64decode(body["response"]["clientDataJSON"] + "=="))
    challenge_bytes = base64.urlsafe_b64decode(client_data["challenge"] + "==")

    if challenge_bytes not in _valid_challenges:
        raise HTTPException(status_code=400, detail="No authentication in progress")
    _valid_challenges.discard(challenge_bytes)

    credential_id = body.get("id", "")

    creds = _get_stored_credentials()
    stored = next((c for c in creds if c["id"] == credential_id), None)
    if not stored:
        logger.error(f"Unknown credential. Browser sent: {credential_id}")
        raise HTTPException(status_code=400, detail="Unknown credential")

    try:
        verification = verify_authentication_response(
            credential=body,
            expected_challenge=challenge_bytes,
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            credential_public_key=stored["public_key"],
            credential_current_sign_count=stored["sign_count"],
        )
    except Exception as exc:
        logger.error(f"WebAuthn auth failed: {exc}")
        raise HTTPException(status_code=400, detail=str(exc))

    conn = get_db()
    conn.execute(
        "UPDATE webauthn_credentials SET sign_count = ? WHERE id = ?",
        (verification.new_sign_count, credential_id),
    )
    conn.commit()
    conn.close()

    return {"verified": True, "token": create_jwt("nic")}


@router.get("/auth/webauthn/credentials")
async def list_credentials():
    creds = _get_stored_credentials()
    return [
        {"id": c["id"], "device_name": c["device_name"], "created_at": c["created_at"]}
        for c in creds
    ]


@router.delete("/auth/webauthn/credentials/{credential_id}")
async def delete_credential(credential_id: str):
    conn = get_db()
    cursor = conn.execute("DELETE FROM webauthn_credentials WHERE id = ?", (credential_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"deleted": True}
```

- [ ] **Step 4: Register webauthn router in main.py**

In `src/main.py`, add the import after line 30 (`from src.database import init_db`):
```python
from src.auth.webauthn import router as webauthn_router
```

And add the router registration after `app.include_router(webhook_router)` (line 71):
```python
app.include_router(webauthn_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_auth/test_webauthn.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/auth/webauthn.py src/main.py tests/test_auth/test_webauthn.py
git commit -m "feat: WebAuthn endpoints with platform authenticator enforcement"
```

---

### Task 6: Create client-side auth.js

**Files:**
- Create: `dashboard/js/auth.js`

- [ ] **Step 1: Create dashboard/js/auth.js**

```javascript
/* ============================================================
   auth.js — WebAuthn authentication / registration client
   ============================================================ */

// ---------- helpers: base64url <-> ArrayBuffer ----------

function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4));
    const binary = atob(base64 + pad);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
}

function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const b of bytes) binary += String.fromCharCode(b);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------- JWT helpers ----------

function getStoredJwt() {
    const token = localStorage.getItem('jwt');
    if (!token) return null;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 > Date.now()) return token;
        localStorage.removeItem('jwt');
    } catch {
        localStorage.removeItem('jwt');
    }
    return null;
}

function storeJwt(token) {
    localStorage.setItem('jwt', token);
}

// ---------- DOM refs ----------

const authScreen    = document.getElementById('auth-screen');
const dashboard     = document.getElementById('dashboard-screen');
const authStatus    = document.getElementById('auth-status');
const authError     = document.getElementById('auth-error');
const registerSec   = document.getElementById('register-section');
const authBtn       = document.getElementById('auth-btn');

// ---------- state ----------

let authToken = null;

// ---------- page load: check JWT or prompt Face ID ----------

window.addEventListener('DOMContentLoaded', async () => {
    const jwt = getStoredJwt();
    if (jwt) {
        authToken = jwt;
        onAuthSuccess();
        return;
    }

    try {
        const res = await fetch('/auth/webauthn/authenticate-options');
        if (res.ok) {
            const opts = await res.json();
            if (opts.allowCredentials && opts.allowCredentials.length > 0) {
                return;
            }
        }
    } catch { /* ignore */ }

    registerSec.classList.remove('hidden');
});

// ---------- public entry points (called from HTML buttons) ----------

async function startAuth() {
    authError.classList.add('hidden');
    authBtn.disabled = true;
    authBtn.innerHTML = '<div class="spinner"></div><span>Authenticating...</span>';
    try {
        await authenticate();
    } catch (err) {
        showAuthError(err.message || 'Authentication failed');
    } finally {
        authBtn.disabled = false;
        authBtn.innerHTML = '<i class="ph ph-fingerprint text-xl"></i><span>Authenticate with Face ID</span>';
    }
}

async function startRegister() {
    const btn = document.getElementById('register-btn');
    authError.classList.add('hidden');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div><span>Registering...</span>';
    try {
        await register();
    } catch (err) {
        showAuthError(err.message || 'Registration failed');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-user-plus text-xl"></i><span>Register Device</span>';
    }
}

// ---------- WebAuthn authenticate ----------

async function authenticate() {
    const optRes = await fetch('/auth/webauthn/authenticate-options');
    if (!optRes.ok) throw new Error('Could not get authentication options');
    const options = await optRes.json();

    options.challenge = base64urlToBuffer(options.challenge);
    if (options.allowCredentials) {
        options.allowCredentials = options.allowCredentials.map(cred => ({
            ...cred,
            id: base64urlToBuffer(cred.id),
        }));
    }

    const credential = await navigator.credentials.get({ publicKey: options });

    const body = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        response: {
            authenticatorData: bufferToBase64url(credential.response.authenticatorData),
            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
            signature: bufferToBase64url(credential.response.signature),
            userHandle: credential.response.userHandle
                ? bufferToBase64url(credential.response.userHandle)
                : null,
        },
        type: credential.type,
    };

    const verifyRes = await fetch('/auth/webauthn/authenticate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (!verifyRes.ok) throw new Error('Authentication verification failed');

    const result = await verifyRes.json();
    if (result.token) {
        storeJwt(result.token);
        authToken = result.token;
    }

    onAuthSuccess();
}

// ---------- WebAuthn register ----------

async function register() {
    const optRes = await fetch('/auth/webauthn/register-options');
    if (!optRes.ok) throw new Error('Could not get registration options');
    const options = await optRes.json();

    options.challenge = base64urlToBuffer(options.challenge);
    options.user.id = base64urlToBuffer(options.user.id);
    if (options.excludeCredentials) {
        options.excludeCredentials = options.excludeCredentials.map(cred => ({
            ...cred,
            id: base64urlToBuffer(cred.id),
        }));
    }

    const credential = await navigator.credentials.create({ publicKey: options });

    const body = {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        response: {
            attestationObject: bufferToBase64url(credential.response.attestationObject),
            clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
        },
        type: credential.type,
    };

    const regRes = await fetch('/auth/webauthn/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });

    if (!regRes.ok) throw new Error('Registration verification failed');

    const result = await regRes.json();
    if (result.token) {
        storeJwt(result.token);
        authToken = result.token;
    }

    onAuthSuccess();
}

// ---------- post-auth transition ----------

function onAuthSuccess() {
    authScreen.classList.add('hidden');
    dashboard.classList.remove('hidden');
    loadDashboard();
}

// ---------- helpers ----------

function showAuthError(msg) {
    authError.textContent = msg;
    authError.classList.remove('hidden');
}

function onSessionExpired() {
    localStorage.removeItem('jwt');
    authToken = null;
    dashboard.classList.add('hidden');
    authScreen.classList.remove('hidden');
    showAuthError('Session expired. Please authenticate again.');
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/js/auth.js
git commit -m "feat: client-side WebAuthn auth with JWT session management"
```

---

### Task 7: Update dashboard index.html — auth screen, avatar popover, move admin

**Files:**
- Modify: `dashboard/index.html`
- Modify: `dashboard/css/glass.css`

- [ ] **Step 1: Add popover and avatar styles to glass.css**

Append to `dashboard/css/glass.css`:
```css

/* Avatar */
.avatar {
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    user-select: none;
}

/* Popover */
.popover {
    position: absolute;
    right: 0;
    top: calc(100% + 0.5rem);
    min-width: 10rem;
    background: rgba(30, 41, 59, 0.95);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    z-index: 50;
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
    transition: opacity 0.15s, transform 0.15s;
    pointer-events: none;
}

.popover.open {
    opacity: 1;
    transform: scale(1) translateY(0);
    pointer-events: auto;
}

.popover-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.625rem 0.875rem;
    font-size: 0.8125rem;
    color: #cbd5e1;
    cursor: pointer;
    transition: background 0.15s;
    text-decoration: none;
}

.popover-item:first-child {
    border-radius: 0.75rem 0.75rem 0 0;
}

.popover-item:last-child {
    border-radius: 0 0 0.75rem 0.75rem;
}

.popover-item:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #f1f5f9;
}

.popover-divider {
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}
```

- [ ] **Step 2: Replace dashboard/index.html**

Replace the entire file with:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Briefing</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <link rel="stylesheet" href="/dashboard/css/glass.css">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
    </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">

    <!-- Auth Screen -->
    <div id="auth-screen" class="min-h-screen flex items-center justify-center px-4">
        <div class="glass-card p-8 w-full max-w-sm text-center space-y-6">
            <div>
                <i class="ph ph-sun-horizon text-5xl text-amber-400"></i>
                <h1 class="text-2xl font-bold mt-3">Morning Briefing</h1>
                <p class="text-slate-400 text-sm mt-1">Authenticate to continue</p>
            </div>

            <div id="auth-status" class="text-sm text-slate-400"></div>

            <button id="auth-btn" onclick="startAuth()" class="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition font-medium flex items-center justify-center gap-2">
                <i class="ph ph-fingerprint text-xl"></i>
                <span>Authenticate with Face ID</span>
            </button>

            <div id="register-section" class="hidden space-y-3">
                <p class="text-sm text-slate-400">No credentials found. Register first:</p>
                <button id="register-btn" onclick="startRegister()" class="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 transition font-medium flex items-center justify-center gap-2">
                    <i class="ph ph-user-plus text-xl"></i>
                    <span>Register Device</span>
                </button>
            </div>

            <div id="auth-error" class="hidden text-red-400 text-sm"></div>
        </div>
    </div>

    <!-- Dashboard Screen -->
    <div id="dashboard-screen" class="hidden max-w-lg lg:max-w-5xl mx-auto px-4 py-6 space-y-4 lg:grid lg:grid-cols-2 lg:gap-4 lg:space-y-0">

        <!-- Header -->
        <div class="fade-in lg:col-span-2">
            <div class="flex items-center gap-3">
                <i class="ph ph-sun-horizon text-3xl text-amber-400" id="greeting-icon"></i>
                <div class="flex-1">
                    <h1 class="text-xl font-bold" id="greeting-text">Good Morning, Nic</h1>
                    <p class="text-sm text-slate-400" id="header-date"></p>
                </div>
                <!-- Avatar + Popover -->
                <div class="relative">
                    <div id="avatar-btn" class="avatar bg-indigo-600 hover:bg-indigo-500 text-white" onclick="togglePopover()">NB</div>
                    <div id="avatar-popover" class="popover">
                        <a href="/dashboard/admin.html" class="popover-item">
                            <i class="ph ph-devices"></i>
                            <span>Manage Devices</span>
                        </a>
                        <a href="/dashboard/admin.html#health" class="popover-item">
                            <i class="ph ph-heartbeat"></i>
                            <span>System Health</span>
                        </a>
                        <div class="popover-divider"></div>
                        <div class="popover-item text-slate-500 cursor-default text-xs">v0.3.0</div>
                    </div>
                </div>
            </div>
            <p class="text-xs text-slate-500 mt-1" id="header-location"></p>
        </div>

        <!-- Weather Card -->
        <div id="weather-card" class="glass-card p-4 space-y-3 fade-in lg:col-span-2">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-thermometer"></i>
                <span>Weather</span>
            </div>
            <div id="weather-current" class="flex items-center justify-between"></div>
            <div id="weather-details" class="flex gap-4 text-xs text-slate-400"></div>
            <div id="weather-hourly" class="hourly-scroll mt-2"></div>
        </div>

        <!-- Commute Card -->
        <div id="commute-card" class="glass-card p-4 space-y-2 fade-in">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-car"></i>
                <span>Commute</span>
            </div>
            <div id="commute-content"></div>
        </div>

        <!-- Calendar Card -->
        <div id="calendar-card" class="glass-card p-4 space-y-3 fade-in">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-calendar-blank"></i>
                <span>Today's Schedule</span>
                <span id="outlook-last-push" class="ml-auto text-xs text-slate-500"></span>
            </div>
            <div id="calendar-events" class="space-y-2"></div>
        </div>

        <!-- Birthdays Card (conditional) -->
        <div id="birthdays-card" class="glass-card p-4 space-y-2 fade-in hidden">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-gift text-pink-400"></i>
                <span>Birthdays Today</span>
            </div>
            <div id="birthdays-content"></div>
        </div>

        <!-- News Section -->
        <div id="news-section" class="glass-card p-4 space-y-3 fade-in lg:col-span-2">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-newspaper"></i>
                <span>News</span>
            </div>
            <div id="news-tabs" class="flex gap-2 overflow-x-auto pb-1"></div>
            <div id="news-content" class="space-y-2"></div>
        </div>

        <!-- Reminders & Flagged Emails -->
        <div id="reminders-emails-card" class="glass-card p-4 space-y-4 fade-in">
            <div>
                <div class="flex items-center gap-2 text-slate-300 text-sm font-medium mb-2">
                    <i class="ph ph-check-square"></i>
                    <span>Reminders</span>
                </div>
                <div id="reminders-content" class="space-y-1"></div>
            </div>
            <div class="border-t border-white/5 pt-3">
                <div class="flex items-center gap-2 text-slate-300 text-sm font-medium mb-2">
                    <i class="ph ph-flag text-red-400"></i>
                    <span>Flagged Emails</span>
                </div>
                <div id="flagged-emails-content" class="space-y-1"></div>
            </div>
        </div>

        <!-- Unread Emails Card -->
        <div id="unread-emails-card" class="glass-card p-4 space-y-2 fade-in hidden">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-envelope text-indigo-400"></i>
                <span>Unread Emails (24h)</span>
                <span id="unread-count-badge" class="ml-auto text-xs bg-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded-full"></span>
            </div>
            <div id="unread-emails-content" class="space-y-1"></div>
        </div>

        <!-- Error State -->
        <div id="error-state" class="hidden glass-card p-8 text-center space-y-3 lg:col-span-2">
            <i class="ph ph-wifi-slash text-4xl text-red-400"></i>
            <p class="text-slate-300">Could not connect</p>
            <p class="text-sm text-slate-500">Check your connection and try again.</p>
            <button onclick="loadDashboard()" class="mt-2 py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition text-sm">
                Retry
            </button>
        </div>

    </div>

    <script src="/dashboard/js/auth.js"></script>
    <script src="/dashboard/js/app.js"></script>
</body>
</html>
```

Key changes from current version:
- Auth screen restored (hidden by default, shown first)
- Dashboard screen is `hidden` again (shown after auth)
- Header has avatar circle ("NB") with popover menu
- Admin section removed (moved to admin.html)
- admin.js script tag removed (not needed on main page)
- auth.js script tag added back (before app.js)

- [ ] **Step 3: Commit**

```bash
git add dashboard/index.html dashboard/css/glass.css
git commit -m "feat: restore auth screen, add avatar popover, move admin to separate page"
```

---

### Task 8: Update app.js — restore auth headers, remove auto-load

**Files:**
- Modify: `dashboard/js/app.js`

- [ ] **Step 1: Update loadDashboard in app.js**

In `dashboard/js/app.js`, make these changes to `loadDashboard()`:

1. Replace the plain fetch (line 95) with auth-header fetch. Change:
```javascript
        const res = await fetch(`${CONFIG.API_URL}/summary?lat=${lat}&lon=${lon}`);
        if (!res.ok) throw new Error(`API returned ${res.status}`);
```

To:
```javascript
        const headers = {};
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        const res = await fetch(`${CONFIG.API_URL}/summary?lat=${lat}&lon=${lon}`, { headers });
        if (res.status === 401) {
            onSessionExpired();
            return;
        }
        if (!res.ok) throw new Error(`API returned ${res.status}`);
```

2. Remove the `loadHealth()` call at line 117 (health is now on admin page):
```javascript
        // Also load admin health
        loadHealth();
```

Delete those two lines.

3. Remove the `admin-section` references from `showError()` and `hideError()`:

In `showError()`, change:
```javascript
    ['weather-card', 'commute-card', 'calendar-card', 'birthdays-card',
     'news-section', 'reminders-emails-card', 'unread-emails-card', 'admin-section'].forEach(id => {
```
To:
```javascript
    ['weather-card', 'commute-card', 'calendar-card', 'birthdays-card',
     'news-section', 'reminders-emails-card', 'unread-emails-card'].forEach(id => {
```

In `hideError()`, change:
```javascript
    ['weather-card', 'commute-card', 'calendar-card',
     'news-section', 'reminders-emails-card', 'unread-emails-card', 'admin-section'].forEach(id => {
```
To:
```javascript
    ['weather-card', 'commute-card', 'calendar-card',
     'news-section', 'reminders-emails-card', 'unread-emails-card'].forEach(id => {
```

4. Remove the auto-load at the bottom of the file. Delete line 413:
```javascript
window.addEventListener('DOMContentLoaded', () => loadDashboard());
```

5. Add the popover toggle function at the bottom of the file:
```javascript

// ---------- Avatar popover ----------

function togglePopover() {
    const popover = document.getElementById('avatar-popover');
    popover.classList.toggle('open');
}

document.addEventListener('click', (e) => {
    const popover = document.getElementById('avatar-popover');
    const avatar = document.getElementById('avatar-btn');
    if (popover && avatar && !avatar.contains(e.target) && !popover.contains(e.target)) {
        popover.classList.remove('open');
    }
});
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/js/app.js
git commit -m "feat: restore auth headers, 401 handling, add popover toggle"
```

---

### Task 9: Create admin.html page

**Files:**
- Create: `dashboard/admin.html`
- Create: `dashboard/js/devices.js`

- [ ] **Step 1: Create dashboard/admin.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin — Morning Briefing</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/@phosphor-icons/web"></script>
    <link rel="stylesheet" href="/dashboard/css/glass.css">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
    </style>
</head>
<body class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">

    <div class="max-w-lg mx-auto px-4 py-6 space-y-4">

        <!-- Header -->
        <div class="fade-in">
            <div class="flex items-center gap-3">
                <a href="/dashboard/" class="text-slate-400 hover:text-white transition">
                    <i class="ph ph-arrow-left text-xl"></i>
                </a>
                <h1 class="text-xl font-bold">Admin</h1>
            </div>
        </div>

        <!-- Registered Devices -->
        <div id="devices-section" class="glass-card p-4 space-y-3 fade-in">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                    <i class="ph ph-devices"></i>
                    <span>Registered Devices</span>
                </div>
            </div>
            <div id="devices-list" class="space-y-2">
                <p class="text-xs text-slate-500">Loading...</p>
            </div>
            <div class="border-t border-white/5 pt-3">
                <button id="register-device-btn" onclick="registerDevice()" class="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 transition text-sm font-medium flex items-center justify-center gap-2">
                    <i class="ph ph-plus"></i>
                    <span>Register This Device</span>
                </button>
            </div>
        </div>

        <!-- System Health -->
        <div id="health-section" class="glass-card p-4 space-y-4 fade-in">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                    <i class="ph ph-heartbeat"></i>
                    <span>System Health</span>
                </div>
                <button onclick="refreshHealth()" class="text-xs text-slate-400 hover:text-white transition flex items-center gap-1">
                    <i class="ph ph-arrow-clockwise"></i>
                    Refresh
                </button>
            </div>
            <div id="health-banner" class="text-sm font-medium"></div>
            <div id="health-grid" class="grid grid-cols-3 gap-2"></div>
            <div class="border-t border-white/5 pt-3 flex items-center justify-between">
                <button id="update-btn" onclick="triggerUpdate()" class="py-2 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition text-sm font-medium flex items-center gap-2">
                    <i class="ph ph-arrow-clockwise"></i>
                    <span>Update System</span>
                </button>
                <span id="last-updated" class="text-xs text-slate-500"></span>
            </div>
            <div id="update-status" class="text-sm hidden"></div>
        </div>

    </div>

    <script>
        const CONFIG = { API_URL: '' };
    </script>
    <script src="/dashboard/js/admin.js"></script>
    <script src="/dashboard/js/devices.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create dashboard/js/devices.js**

```javascript
/* ============================================================
   devices.js — Credential management for admin page
   ============================================================ */

// ---------- helpers: base64url <-> ArrayBuffer ----------

function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4));
    const binary = atob(base64 + pad);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
}

function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (const b of bytes) binary += String.fromCharCode(b);
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

// ---------- Load devices ----------

async function loadDevices() {
    const el = document.getElementById('devices-list');
    try {
        const res = await fetch(`${CONFIG.API_URL}/auth/webauthn/credentials`);
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        const devices = await res.json();

        if (!devices.length) {
            el.innerHTML = '<p class="text-sm text-slate-500">No devices registered</p>';
            return;
        }

        el.innerHTML = devices.map(d => {
            const date = new Date(d.created_at * 1000).toLocaleDateString('en-AU', {
                day: 'numeric', month: 'short', year: 'numeric',
            });
            return `
                <div class="flex items-center justify-between py-2 px-1">
                    <div class="flex items-center gap-2">
                        <i class="ph ph-device-mobile text-indigo-400"></i>
                        <div>
                            <p class="text-sm font-medium">${d.device_name || 'Unknown'}</p>
                            <p class="text-xs text-slate-500">Registered ${date}</p>
                        </div>
                    </div>
                    <button onclick="deleteDevice('${d.id}')" class="text-xs text-red-400 hover:text-red-300 transition flex items-center gap-1">
                        <i class="ph ph-trash"></i>
                        Remove
                    </button>
                </div>
            `;
        }).join('');
    } catch (err) {
        el.innerHTML = `<p class="text-sm text-red-400">Could not load devices: ${err.message}</p>`;
    }
}

// ---------- Delete device ----------

async function deleteDevice(id) {
    try {
        const res = await fetch(`${CONFIG.API_URL}/auth/webauthn/credentials/${encodeURIComponent(id)}`, {
            method: 'DELETE',
        });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        loadDevices();
    } catch (err) {
        alert('Failed to remove device: ' + err.message);
    }
}

// ---------- Register this device ----------

async function registerDevice() {
    const btn = document.getElementById('register-device-btn');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div><span>Registering...</span>';

    try {
        const optRes = await fetch(`${CONFIG.API_URL}/auth/webauthn/register-options`);
        if (!optRes.ok) throw new Error('Could not get registration options');
        const options = await optRes.json();

        options.challenge = base64urlToBuffer(options.challenge);
        options.user.id = base64urlToBuffer(options.user.id);
        if (options.excludeCredentials) {
            options.excludeCredentials = options.excludeCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id),
            }));
        }

        const credential = await navigator.credentials.create({ publicKey: options });

        const body = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            response: {
                attestationObject: bufferToBase64url(credential.response.attestationObject),
                clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
            },
            type: credential.type,
        };

        const regRes = await fetch(`${CONFIG.API_URL}/auth/webauthn/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!regRes.ok) throw new Error('Registration failed');

        loadDevices();
    } catch (err) {
        alert('Registration failed: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-plus"></i><span>Register This Device</span>';
    }
}

// ---------- Auto-load ----------

window.addEventListener('DOMContentLoaded', () => {
    loadDevices();
    loadHealth();

    // Scroll to health section if URL has #health
    if (window.location.hash === '#health') {
        setTimeout(() => {
            document.getElementById('health-section')?.scrollIntoView({ behavior: 'smooth' });
        }, 300);
    }
});
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/admin.html dashboard/js/devices.js
git commit -m "feat: admin page with device management and system health"
```

---

### Task 10: Update manage.sh and CLAUDE.md

**Files:**
- Modify: `manage.sh`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Re-add reset-webauthn to manage.sh**

Replace `manage.sh` with:
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

- [ ] **Step 2: Update CLAUDE.md**

Make these changes to `CLAUDE.md`:

1. In the Project Architecture tree, add back the webauthn.py line under `src/auth/`:
```
│   │   └── webauthn.py       # Face ID registration/authentication
```

2. In the Key API Endpoints table, update the dashboard row and add webauthn:
```
| `GET /dashboard/` | WebAuthn + Cloudflare Access | Glassmorphism web dashboard |
| `GET /auth/webauthn/*` | None | Face ID registration/auth |
| `GET /auth/webauthn/credentials` | Optional | List/delete registered devices |
```

3. In the Data Flow section, update:
```
Tap widget   →  Safari → Cloudflare Access → Face ID → full dashboard
```

4. In the Commands Reference table, add back:
```
| `./manage.sh reset-webauthn` | Clear Face ID credentials |
```

5. In Phase 5 iOS Setup, add back:
```
3. **Face ID Registration:** Open the dashboard URL in Safari, complete platform authenticator registration on first visit
```

- [ ] **Step 3: Commit**

```bash
git add manage.sh CLAUDE.md
git commit -m "docs: update manage.sh and CLAUDE.md for platform WebAuthn"
```

---

### Task 11: Run full test suite and verify

- [ ] **Step 1: Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: All tests pass — bearer tests (5), webauthn tests (4), database test (1), plus existing collector tests.

- [ ] **Step 2: Verify no import errors**

```bash
python3 -c "from src.main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Verify webauthn endpoints respond**

```bash
python3 -c "
from fastapi.testclient import TestClient
from src.database import init_db
from src.main import app
init_db()
c = TestClient(app)
r = c.get('/auth/webauthn/register-options')
print('register-options:', r.status_code)
d = r.json()
print('authenticatorAttachment:', d.get('authenticatorSelection', {}).get('authenticatorAttachment'))
print('userVerification:', d.get('authenticatorSelection', {}).get('userVerification'))
r2 = c.get('/auth/webauthn/credentials')
print('credentials:', r2.status_code, r2.json())
"
```

Expected:
```
register-options: 200
authenticatorAttachment: platform
userVerification: required
credentials: 200 []
```
