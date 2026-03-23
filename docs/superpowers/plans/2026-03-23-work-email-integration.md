# Work Email Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add work email integration (calendar, flagged emails, unread summary) via iOS Shortcut push, with optional EWS fallback.

**Architecture:** New `/data/outlook` endpoint receives data pushed from an iOS Shortcut (same pattern as `/data/reminders`). Data stored in scheduler's in-memory cache, exposed via `/summary` response. Optional EWS collector for server-side fetching if org allows Basic Auth.

**Tech Stack:** FastAPI, Pydantic, exchangelib (optional), pytest

**Spec:** `docs/superpowers/specs/2026-03-23-work-email-ews-design.md`

---

### Task 1: Add unread_emails to scheduler cache

**Files:**
- Modify: `src/scheduler.py`
- Test: `tests/test_scheduler_cache.py`

- [ ] **Step 1: Write failing test for get_cached_unread**

```python
# tests/test_scheduler_cache.py
from src.scheduler import get_cached_unread, _cache

def test_get_cached_unread_returns_empty_by_default():
    _cache["unread_emails"] = []
    assert get_cached_unread() == []

def test_get_cached_unread_returns_stored_data():
    _cache["unread_emails"] = [{"subject": "Test", "from_name": "Foo"}]
    result = get_cached_unread()
    assert len(result) == 1
    assert result[0]["subject"] == "Test"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scheduler_cache.py -v`
Expected: FAIL — `ImportError` or `KeyError` for `unread_emails`

- [ ] **Step 3: Implement cache changes**

In `src/scheduler.py`, add `"unread_emails": []` to the `_cache` dict (after `"flagged_emails"`):

```python
_cache: dict[str, Any] = {
    "calendar": [],
    "birthdays": [],
    "news": {},
    "flagged_emails": [],
    "unread_emails": [],      # <-- add this
    "last_run": None,
    "errors": [],
}
```

Add accessor function after `get_cached_reminders()`:

```python
def get_cached_unread() -> list[dict]:
    return _cache["unread_emails"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scheduler_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduler.py tests/test_scheduler_cache.py
git commit -m "feat: add unread_emails to scheduler cache with accessor"
```

---

### Task 2: Add set_cached_outlook_data setter

**Files:**
- Modify: `src/scheduler.py`
- Modify: `tests/test_scheduler_cache.py`

- [ ] **Step 1: Write failing test for setter**

```python
# append to tests/test_scheduler_cache.py
from src.scheduler import set_cached_outlook_data, _cache

def test_set_cached_outlook_data_stores_all_fields():
    # Pre-populate with personal calendar events
    _cache["calendar"] = [{"subject": "Personal Event", "source": "personal"}]

    set_cached_outlook_data(
        calendar=[{"subject": "Work Meeting", "source": "work"}],
        flagged_emails=[{"subject": "Flag1", "from_name": "Boss"}],
        unread_emails=[{"subject": "Unread1", "from_name": "IT"}],
    )

    # Personal events preserved, work events added
    assert len(_cache["calendar"]) == 2
    assert any(e["source"] == "personal" for e in _cache["calendar"])
    assert any(e["source"] == "work" for e in _cache["calendar"])
    assert _cache["flagged_emails"] == [{"subject": "Flag1", "from_name": "Boss"}]
    assert _cache["unread_emails"] == [{"subject": "Unread1", "from_name": "IT"}]

def test_set_cached_outlook_data_replaces_old_work_events():
    _cache["calendar"] = [
        {"subject": "Personal", "source": "personal"},
        {"subject": "Old Work", "source": "work"},
    ]

    set_cached_outlook_data(
        calendar=[{"subject": "New Work", "source": "work"}],
        flagged_emails=[],
        unread_emails=[],
    )

    subjects = [e["subject"] for e in _cache["calendar"]]
    assert "Personal" in subjects
    assert "New Work" in subjects
    assert "Old Work" not in subjects
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scheduler_cache.py::test_set_cached_outlook_data_stores_all_fields -v`
Expected: FAIL — `ImportError` for `set_cached_outlook_data`

- [ ] **Step 3: Implement setter**

Add to `src/scheduler.py` after the accessor functions:

```python
def set_cached_outlook_data(
    calendar: list[dict],
    flagged_emails: list[dict],
    unread_emails: list[dict],
) -> None:
    """Store Outlook data pushed from iOS Shortcut. Preserves personal calendar events."""
    personal = [e for e in _cache["calendar"] if e.get("source") != "work"]
    _cache["calendar"] = personal + calendar
    _cache["flagged_emails"] = flagged_emails
    _cache["unread_emails"] = unread_emails
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scheduler_cache.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/scheduler.py tests/test_scheduler_cache.py
git commit -m "feat: add set_cached_outlook_data setter for iOS Shortcut push"
```

---

### Task 3: Add POST /data/outlook endpoint

**Files:**
- Modify: `src/routes/data.py`
- Modify: `tests/test_routes/test_data.py`

- [ ] **Step 1: Write failing tests**

```python
# append to tests/test_routes/test_data.py

def test_post_outlook_stores_data(client):
    payload = {
        "calendar": [
            {"subject": "Standup", "start": "2026-03-24T09:00:00+10:00",
             "end": "2026-03-24T09:30:00+10:00", "location": "Room 3B",
             "teams_link": "", "source": "work"}
        ],
        "flagged_emails": [
            {"subject": "Budget", "from_name": "Jane", "from_address": "jane@co.com",
             "received": "2026-03-23T14:00:00+10:00", "source": "work"}
        ],
        "unread_emails": [
            {"subject": "Reset", "from_name": "IT", "from_address": "it@co.com",
             "received": "2026-03-23T16:00:00+10:00", "source": "work"}
        ],
    }
    resp = client.post(
        "/data/outlook",
        json=payload,
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stored_calendar"] == 1
    assert data["stored_flagged"] == 1
    assert data["stored_unread"] == 1

def test_post_outlook_rejects_bad_token(client):
    resp = client.post(
        "/data/outlook",
        json={"calendar": [], "flagged_emails": [], "unread_emails": []},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_routes/test_data.py::test_post_outlook_stores_data -v`
Expected: FAIL — 404 (endpoint doesn't exist)

- [ ] **Step 3: Implement endpoint**

Update `src/routes/data.py`:

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional

from src.auth.bearer import verify_bearer
from src.collectors.reminders import RemindersPayload, store_reminders
from src.scheduler import set_cached_outlook_data, _update_system_status

router = APIRouter()


class OutlookCalendarEvent(BaseModel):
    subject: str = ""
    start: str = ""
    end: str = ""
    location: str = ""
    teams_link: str = ""
    source: str = "work"


class OutlookEmail(BaseModel):
    subject: str = ""
    from_name: str = ""
    from_address: str = ""
    received: str = ""
    source: str = "work"


class OutlookPayload(BaseModel):
    calendar: List[OutlookCalendarEvent] = []
    flagged_emails: List[OutlookEmail] = []
    unread_emails: List[OutlookEmail] = []


@router.post("/data/reminders")
async def post_reminders(payload: RemindersPayload, _=Depends(verify_bearer)):
    count = store_reminders(payload.reminders)
    return {"stored": count}


@router.post("/data/outlook")
async def post_outlook(payload: OutlookPayload, _=Depends(verify_bearer)):
    set_cached_outlook_data(
        calendar=[e.model_dump() for e in payload.calendar],
        flagged_emails=[e.model_dump() for e in payload.flagged_emails],
        unread_emails=[e.model_dump() for e in payload.unread_emails],
    )
    _update_system_status("microsoft_graph", True)
    return {
        "stored_calendar": len(payload.calendar),
        "stored_flagged": len(payload.flagged_emails),
        "stored_unread": len(payload.unread_emails),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_routes/test_data.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/routes/data.py tests/test_routes/test_data.py
git commit -m "feat: add POST /data/outlook endpoint for iOS Shortcut push"
```

---

### Task 4: Add unread_emails to summary response

**Files:**
- Modify: `src/routes/summary.py`
- Modify: `tests/test_routes/test_summary.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_routes/test_summary.py (or create if doesn't exist)
# This test verifies unread_emails is present in the summary response

def test_summary_includes_unread_emails(client, monkeypatch):
    """Verify the summary endpoint returns unread_emails field."""
    import src.scheduler
    monkeypatch.setattr(src.scheduler, "_cache", {
        "calendar": [],
        "birthdays": [],
        "news": {},
        "flagged_emails": [],
        "unread_emails": [{"subject": "Test", "from_name": "IT"}],
        "last_run": None,
        "errors": [],
    })

    resp = client.get(
        "/summary?lat=-27.5&lon=151.9",
        headers={"Authorization": "Bearer test-bearer-token"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_emails" in data
    assert len(data["unread_emails"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_routes/test_summary.py::test_summary_includes_unread_emails -v`
Expected: FAIL — `unread_emails` not in response

- [ ] **Step 3: Add unread_emails to summary response**

In `src/routes/summary.py`, add the import and field:

```python
from src.scheduler import (
    get_cached_calendar,
    get_cached_birthdays,
    get_cached_news,
    get_cached_reminders,
    get_cached_flagged,
    get_cached_unread,      # <-- add
    get_cache_status,
    _update_system_status,
)
```

In the return dict of the `summary()` function, add:

```python
    return {
        "weather": weather,
        "commute": commute,
        "calendar": get_cached_calendar(),
        "birthdays": get_cached_birthdays(),
        "news": get_cached_news(),
        "reminders": get_cached_reminders(),
        "flagged_emails": get_cached_flagged(),
        "unread_emails": get_cached_unread(),     # <-- add
        "cache_status": get_cache_status(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_routes/test_summary.py::test_summary_includes_unread_emails -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/routes/summary.py tests/test_routes/test_summary.py
git commit -m "feat: add unread_emails to summary API response"
```

---

### Task 5: Dashboard — unread emails card and flagged emails bug fix

**Files:**
- Modify: `dashboard/index.html`
- Modify: `dashboard/js/app.js`

- [ ] **Step 1: Add unread emails card to HTML**

In `dashboard/index.html`, add a new card after the flagged emails section (after the closing `</div>` of `reminders-emails-card`, around line 147):

```html
        <!-- Unread Emails Card -->
        <div id="unread-emails-card" class="glass-card p-4 space-y-2 fade-in hidden">
            <div class="flex items-center gap-2 text-slate-300 text-sm font-medium">
                <i class="ph ph-envelope text-indigo-400"></i>
                <span>Unread Emails (24h)</span>
                <span id="unread-count-badge" class="ml-auto text-xs bg-indigo-500/30 text-indigo-300 px-2 py-0.5 rounded-full"></span>
            </div>
            <div id="unread-emails-content" class="space-y-1">
                <!-- Filled by JS -->
            </div>
        </div>
```

- [ ] **Step 2: Add renderUnreadEmails function to app.js**

Add after `renderFlaggedEmails()`:

```javascript
// ---------- Render: Unread Emails ----------

function renderUnreadEmails(emails) {
    const card = document.getElementById('unread-emails-card');
    const el = document.getElementById('unread-emails-content');
    const badge = document.getElementById('unread-count-badge');

    if (!emails || !emails.length) {
        card.classList.add('hidden');
        return;
    }

    card.classList.remove('hidden');
    badge.textContent = emails.length;

    const maxShow = 10;
    const shown = emails.slice(0, maxShow);
    el.innerHTML = shown.map(e => `
        <div class="flex items-start gap-2 text-sm">
            <i class="ph ph-envelope-simple text-indigo-400 mt-0.5"></i>
            <div class="min-w-0">
                <span class="text-slate-200 font-medium">${e.from_name || ''}</span>
                <span class="text-slate-400 mx-1">—</span>
                <span class="text-slate-300">${e.subject || ''}</span>
            </div>
        </div>
    `).join('');

    if (emails.length > maxShow) {
        el.innerHTML += `<p class="text-xs text-slate-500 mt-1">and ${emails.length - maxShow} more...</p>`;
    }
}
```

- [ ] **Step 3: Fix renderFlaggedEmails bug**

In the existing `renderFlaggedEmails()` function, change the sender line from:

```javascript
<p class="text-xs text-slate-500">${e.from || e.sender || ''}</p>
```

to:

```javascript
<p class="text-xs text-slate-500">${e.from_name || ''}</p>
```

- [ ] **Step 4: Wire up in loadDashboard**

In the `loadDashboard()` function, add after `renderFlaggedEmails(data.flagged_emails)`:

```javascript
        renderUnreadEmails(data.unread_emails);
```

- [ ] **Step 5: Verify in browser**

Open `dashboard.nicholasbrown.me/dashboard/` and confirm the unread emails card renders (will show "hidden" until data is pushed).

- [ ] **Step 6: Commit**

```bash
git add dashboard/index.html dashboard/js/app.js
git commit -m "feat: add unread emails card to dashboard, fix flagged emails sender bug"
```

---

### Task 6: Widget — add unread emails count

**Files:**
- Modify: `scriptable/morning-widget.js`

- [ ] **Step 1: Add unread emails section to large widget**

In `buildLargeWidget()`, add a new section builder function before `buildLargeWidget`:

```javascript
function addUnreadCount(parent, data) {
    if (!data.unread_emails || data.unread_emails.length === 0) return null;

    const card = makeCard(parent, { pt: 6, pb: 6, bg: CARD_BG_ALT });
    const row = card.addStack();
    row.centerAlignContent();

    sfImg("envelope.fill", 12, TEAL, row);
    row.addSpacer(6);

    const count = data.unread_emails.length;
    const t = row.addText(`${count} unread email${count === 1 ? '' : 's'}`);
    t.font = Font.semiboldSystemFont(12);
    t.textColor = WHITE;

    row.addSpacer();

    // Show first sender if available
    if (data.unread_emails[0] && data.unread_emails[0].from_name) {
        const preview = row.addText(data.unread_emails[0].from_name);
        preview.font = Font.regularSystemFont(10);
        preview.textColor = TEXT_MUTED;
        preview.lineLimit = 1;
    }

    return card;
}
```

- [ ] **Step 2: Call it in buildLargeWidget**

In `buildLargeWidget()`, add after the flagged emails section (before `w.addSpacer()`):

```javascript
    // ── Unread emails count ──
    addUnreadCount(w, data);
```

- [ ] **Step 3: Commit**

```bash
git add scriptable/morning-widget.js
git commit -m "feat: add unread emails count to large widget"
```

---

### Task 7: Optional EWS collector

**Files:**
- Create: `src/collectors/outlook_ews.py`
- Modify: `src/config.py`
- Modify: `src/scheduler.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Add config fields**

In `src/config.py`, add after `ms_tenant_id`:

```python
    ms_email: str = ""
    ms_password: str = ""
```

- [ ] **Step 2: Add exchangelib to requirements.txt**

```
exchangelib>=5.0.0
```

- [ ] **Step 3: Create EWS collector**

Create `src/collectors/outlook_ews.py`:

```python
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from src.config import settings

logger = logging.getLogger(__name__)


async def fetch_ews_calendar() -> list[dict]:
    """Fetch today's calendar events via EWS."""
    from exchangelib import Credentials, Account, EWSDateTime, EWSTimeZone

    creds = Credentials(settings.ms_email, settings.ms_password)
    account = Account(settings.ms_email, credentials=creds, autodiscover=True)

    tz = EWSTimeZone.from_pytz(account.default_timezone)
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    events = []
    for item in account.calendar.view(start=start, end=end):
        events.append({
            "subject": item.subject or "",
            "start": item.start.isoformat() if item.start else "",
            "end": item.end.isoformat() if item.end else "",
            "location": str(item.location) if item.location else "",
            "teams_link": "",
            "source": "work",
        })

    return events


async def fetch_ews_flagged_emails() -> list[dict]:
    """Fetch flagged emails via EWS."""
    from exchangelib import Credentials, Account

    creds = Credentials(settings.ms_email, settings.ms_password)
    account = Account(settings.ms_email, credentials=creds, autodiscover=True)

    emails = []
    flagged = account.inbox.filter(is_flagged=True).order_by("-datetime_received")[:20]
    for item in flagged:
        emails.append({
            "subject": item.subject or "",
            "from_name": item.sender.name if item.sender else "",
            "from_address": item.sender.email_address if item.sender else "",
            "received": item.datetime_received.isoformat() if item.datetime_received else "",
            "source": "work",
        })

    return emails


async def fetch_ews_unread_emails() -> list[dict]:
    """Fetch unread emails from the last 24 hours via EWS."""
    from exchangelib import Credentials, Account

    creds = Credentials(settings.ms_email, settings.ms_password)
    account = Account(settings.ms_email, credentials=creds, autodiscover=True)

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    emails = []
    unread = (
        account.inbox
        .filter(is_read=False, datetime_received__gte=cutoff)
        .order_by("-datetime_received")[:50]
    )
    for item in unread:
        emails.append({
            "subject": item.subject or "",
            "from_name": item.sender.name if item.sender else "",
            "from_address": item.sender.email_address if item.sender else "",
            "received": item.datetime_received.isoformat() if item.datetime_received else "",
            "source": "work",
        })

    return emails
```

- [ ] **Step 4: Update scheduler to conditionally use EWS**

In `src/scheduler.py`, in the `run_cache_job()` function, add a new section after the flagged emails block. Only runs if `ms_email` and `ms_password` are configured:

```python
    # --- EWS: Work calendar + emails (optional, if credentials configured) ---
    if settings.ms_email and settings.ms_password:
        try:
            from src.collectors.outlook_ews import (
                fetch_ews_calendar,
                fetch_ews_flagged_emails,
                fetch_ews_unread_emails,
            )
            ews_calendar = await fetch_ews_calendar()
            ews_flagged = await fetch_ews_flagged_emails()
            ews_unread = await fetch_ews_unread_emails()

            # Merge EWS calendar with existing
            personal = [e for e in _cache["calendar"] if e.get("source") != "work"]
            _cache["calendar"] = personal + ews_calendar
            _cache["flagged_emails"] = ews_flagged
            _cache["unread_emails"] = ews_unread
            _update_system_status("microsoft_graph", True)
        except Exception as exc:
            logger.error("EWS fetch failed: %s", exc)
            errors.append(f"ews: {exc}")
            _update_system_status("microsoft_graph", False, str(exc))
```

Add `import src.config` at the top if not already present, and use `settings = src.config.settings` inside the function.

- [ ] **Step 5: Commit**

```bash
git add src/collectors/outlook_ews.py src/config.py src/scheduler.py requirements.txt
git commit -m "feat: add optional EWS collector for work email (test before using)"
```

---

### Task 8: Update .env.example and conftest

**Files:**
- Modify: `.env.example`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add new env vars to .env.example**

```
# Optional: EWS auth (likely blocked by M365 Basic Auth deprecation -- test first)
MS_EMAIL=
MS_PASSWORD=
```

- [ ] **Step 2: Add to test conftest**

In `tests/conftest.py`, add to the `env` dict:

```python
        "MS_EMAIL": "",
        "MS_PASSWORD": "",
```

- [ ] **Step 3: Commit**

```bash
git add .env.example tests/conftest.py
git commit -m "chore: add MS_EMAIL/MS_PASSWORD to env example and test config"
```

---

### Task 9: Push and test on Pi

- [ ] **Step 1: Push all changes**

```bash
git push origin main
```

- [ ] **Step 2: Rebuild on Pi**

```bash
cd ~/TheDailyBrown && git pull && docker compose up -d --build morning-briefing
```

- [ ] **Step 3: Test the /data/outlook endpoint**

```bash
curl -s -X POST http://localhost:8000/data/outlook \
  -H "Authorization: Bearer 76cbca42da3b3c6fa90a09397c96deaa8f91e1ea856eca33e93b6b052855bd14" \
  -H "Content-Type: application/json" \
  -d '{
    "calendar": [{"subject": "Test Meeting", "start": "2026-03-24T09:00:00+10:00", "end": "2026-03-24T09:30:00+10:00", "location": "Room 1", "teams_link": "", "source": "work"}],
    "flagged_emails": [{"subject": "Review doc", "from_name": "Boss", "from_address": "boss@co.com", "received": "2026-03-23T14:00:00+10:00", "source": "work"}],
    "unread_emails": [{"subject": "Lunch?", "from_name": "Colleague", "from_address": "col@co.com", "received": "2026-03-23T16:00:00+10:00", "source": "work"}]
  }'
```

Expected: `{"stored_calendar": 1, "stored_flagged": 1, "stored_unread": 1}`

- [ ] **Step 4: Verify summary includes the data**

```bash
curl -s -H "Authorization: Bearer 76cbca42da3b3c6fa90a09397c96deaa8f91e1ea856eca33e93b6b052855bd14" \
  "http://localhost:8000/summary?lat=-27.5&lon=151.9" | python3 -m json.tool | grep -A3 unread
```

Expected: `unread_emails` array with the test data

- [ ] **Step 5: Check dashboard**

Open `dashboard.nicholasbrown.me/dashboard/` — should see unread emails card with test data.
