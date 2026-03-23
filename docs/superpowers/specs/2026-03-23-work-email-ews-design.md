# Work Email Integration

## Goal

Connect to Nic's work Microsoft 365 email without Azure App Registration, fetching calendar events, flagged emails, and unread email summaries for the morning briefing system.

## Constraints

- No admin access to create Azure AD App Registrations
- Can sign into M365 via browser and phone
- Organization is Microsoft 365 / Exchange
- Microsoft disabled Basic Auth for EWS across all M365 tenants (October 2023)

## Approach

**Primary: iOS Shortcut Push**

An iOS Shortcut reads Outlook calendar and email via native iOS APIs, then POSTs the data to the briefing API -- identical pattern to the existing reminders push. This is the recommended path because it bypasses all server-side auth issues entirely. If Outlook works on the phone, this works.

**Secondary: EWS (Exchange Web Services) -- test first**

Try EWS with `exchangelib` as a quick test. Microsoft disabled Basic Auth in Oct 2023, so this will likely fail for M365 tenants. However, some orgs have exceptions or run hybrid Exchange. Worth a 5-minute test before committing to the Shortcut path.

**Note on Basic Auth:** If EWS Basic Auth is blocked (expected), `exchangelib` also supports OAuth2 via `OAuth2Credentials`, but this still requires an App Registration -- which we don't have. So if EWS Basic Auth fails, the iOS Shortcut is the only viable path.

## Data Fetched

### Calendar Events (today)
```json
{
  "subject": "Team Standup",
  "start": "2026-03-24T09:00:00+10:00",
  "end": "2026-03-24T09:30:00+10:00",
  "location": "Room 3B",
  "teams_link": "https://teams.microsoft.com/...",
  "source": "work"
}
```

### Flagged Emails
```json
{
  "subject": "Q2 Budget Review",
  "from_name": "Jane Smith",
  "from_address": "jane@company.com",
  "received": "2026-03-23T14:30:00+10:00",
  "source": "work"
}
```

### Unread Emails (last 24hrs)
```json
{
  "subject": "Password reset reminder",
  "from_name": "IT Support",
  "from_address": "it@company.com",
  "received": "2026-03-23T16:00:00+10:00",
  "source": "work"
}
```

## Architecture

### iOS Shortcut Path (Primary)

```
Phone wakes -> iOS Shortcut reads Outlook calendar + mail
            -> POST /data/outlook (bearer auth)
            -> stored in memory via set_cached_outlook_data()
            -> same cache consumed by summary route
```

### EWS Path (Secondary -- test first)

```
4am scheduler -> outlook_ews.py -> EWS API (email + password)
                                -> calendar, flagged, unread
                               -> cached in memory
```

The rest of the system (summary route, dashboard, widget) consumes the same data shape regardless of which path provides it.

## Files Changed

| File | Change |
|---|---|
| `src/collectors/outlook_ews.py` | **New.** EWS collector with three functions: `fetch_ews_calendar()`, `fetch_ews_flagged_emails()`, `fetch_ews_unread_emails()`. Only used if EWS auth works. |
| `src/collectors/outlook.py` | Kept as-is. Not deleted -- existing Graph API code preserved for rollback. |
| `src/scheduler.py` | Add `unread_emails` to `_cache` dict. Add `get_cached_unread()` accessor. Add `set_cached_outlook_data()` setter for iOS Shortcut push. Conditionally import from `outlook_ews` if EWS credentials are configured. |
| `src/routes/summary.py` | Add `unread_emails: get_cached_unread()` to the response dict. |
| `src/routes/data.py` | Add `POST /data/outlook` endpoint for iOS Shortcut push. Accepts `calendar`, `flagged_emails`, and `unread_emails` arrays. Calls `set_cached_outlook_data()` to store in cache. |
| `src/config.py` | Add optional `ms_email: str = ""` and `ms_password: str = ""` settings for EWS. |
| `.env.example` | Add `MS_EMAIL` and `MS_PASSWORD` entries (marked optional). |
| `requirements.txt` | Add `exchangelib` dependency. |
| `Dockerfile` | Add `libxml2-dev libxslt-dev` system deps if needed for `exchangelib` on ARM. |
| `dashboard/index.html` | Add unread emails card below flagged emails card. |
| `dashboard/js/app.js` | Add `renderUnreadEmails()` function using `from_name` field explicitly. Fix existing `renderFlaggedEmails()` to also use `from_name` (currently reads `e.from` which doesn't match the API shape). Call both from `loadDashboard()`. |
| `scriptable/morning-widget.js` | Add unread emails section to large widget (count + top 2-3 subjects). |

## Scheduler Cache Changes

Add to `_cache` dict:
```python
"unread_emails": [],
```

Add accessor:
```python
def get_cached_unread() -> list[dict]:
    return _cache["unread_emails"]
```

Add setter for iOS Shortcut push:
```python
def set_cached_outlook_data(
    calendar: list[dict],
    flagged_emails: list[dict],
    unread_emails: list[dict],
) -> None:
    # Merge work calendar events with existing personal events
    personal = [e for e in _cache["calendar"] if e.get("source") != "work"]
    _cache["calendar"] = personal + calendar
    _cache["flagged_emails"] = flagged_emails
    _cache["unread_emails"] = unread_emails
```

## Health System

Add new health entry `exchange_ews` (separate from `microsoft_graph` since they are different auth paths). Only tracked if EWS credentials are configured. If using iOS Shortcut path only, the health status is tracked via the push endpoint (similar to `ios_reminders_push` -- shows "waiting" until first push, then "ok").

## New Endpoint: `POST /data/outlook`

Same pattern as existing `/data/reminders`.

```
POST /data/outlook
Authorization: Bearer <token>
Content-Type: application/json

{
  "calendar": [...],
  "flagged_emails": [...],
  "unread_emails": [...]
}
```

Calls `set_cached_outlook_data()` from `scheduler.py` to store data. Updates health status for `microsoft_graph` to "ok" on successful push.

## Dashboard: Unread Emails Section

New card below "Flagged Emails" in `index.html`:
- Header: "Unread Emails (24h)" with envelope icon and count badge (e.g., "12")
- Each item: sender name (bold) + subject, one line per email
- Truncate at 10 items with "and X more..." text

**Bug fix:** Existing `renderFlaggedEmails()` reads `e.from || e.sender` but the API returns `from_name` and `from_address`. Fix to use `e.from_name` explicitly.

## Widget: Unread Emails

In the large widget, add an unread count below flagged emails:
- Compact line: envelope icon + "12 unread" or "No new mail"
- Only show if count > 0 to save space

## Configuration

New `.env` variables (both optional):

```
# Optional: EWS auth (test first -- likely blocked by M365 Basic Auth deprecation)
MS_EMAIL=nic.brown@company.com
MS_PASSWORD=your-password-or-app-password
```

**Security note:** If using EWS, prefer an app-specific password over the main account password. The password is stored in `.env` which is not committed to git and has `chmod 600` on the Pi.

If neither `MS_EMAIL` nor `MS_PASSWORD` is set, the EWS collector is skipped entirely. The system relies on the iOS Shortcut push or the existing Graph API (if configured).

## Testing Strategy

1. **Quick EWS validation (5 min):** Try `exchangelib` connection with credentials on the Pi. If it connects, use EWS. If blocked (expected), proceed with iOS Shortcut only.
2. **Unit tests:** Mock EWS responses for calendar, flagged, and unread queries. Test the `/data/outlook` endpoint with sample payloads. Test `set_cached_outlook_data()` merges work/personal calendar correctly.
3. **Integration:** Verify the summary endpoint includes `unread_emails` and the dashboard renders it correctly.

## Rollback

- Existing `outlook.py` (Graph API) is untouched
- Remove `outlook_ews.py` imports from scheduler
- iOS Shortcut continues to work independently
- Remove `unread_emails` from summary response if unwanted
