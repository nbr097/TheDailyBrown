# Work Email Integration via EWS

## Goal

Connect to Nic's work Microsoft 365 email without Azure App Registration, fetching calendar events, flagged emails, and unread email summaries for the morning briefing system.

## Constraints

- No admin access to create Azure AD App Registrations
- Can sign into M365 via browser and phone
- Organization is Microsoft 365 / Exchange

## Approach

**Primary: EWS (Exchange Web Services) via `exchangelib`**

Authenticate with email + password directly against Exchange. No App Registration, no OAuth flow, no admin consent needed. If the org has disabled Basic Auth or legacy auth, fall back to iOS Shortcut push.

**Fallback: iOS Shortcut Push**

An iOS Shortcut reads Outlook calendar and email via native iOS APIs, then POSTs the data to the briefing API -- identical pattern to the existing reminders push.

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

### EWS Path (Primary)

```
4am scheduler -> outlook_ews.py -> EWS API (email + password)
                                -> calendar events
                                -> flagged emails
                                -> unread emails (last 24hrs)
                               -> cached in memory
```

### iOS Shortcut Path (Fallback)

```
Phone wakes -> iOS Shortcut reads Outlook
            -> POST /data/outlook (bearer auth)
            -> stored in memory (same cache shape)
```

The rest of the system (summary route, dashboard, widget) consumes the same data shape regardless of which path provides it.

## Files Changed

| File | Change |
|---|---|
| `src/collectors/outlook_ews.py` | **New.** EWS collector with three functions: `fetch_ews_calendar()`, `fetch_ews_flagged_emails()`, `fetch_ews_unread_emails()` |
| `src/collectors/outlook.py` | Kept as-is. Not deleted in case EWS fails and we need to revert. |
| `src/scheduler.py` | Import from `outlook_ews` instead of `outlook`. Add `unread_emails` to `_cache`. |
| `src/routes/summary.py` | Add `unread_emails` field to the response dict. |
| `src/routes/data.py` | Add `POST /data/outlook` endpoint for iOS Shortcut fallback. Accepts calendar, flagged_emails, and unread_emails arrays. |
| `src/config.py` | Add `ms_email: str` and `ms_password: str` settings (optional, for EWS). |
| `.env.example` | Add `MS_EMAIL` and `MS_PASSWORD` entries. |
| `dashboard/index.html` | Add unread emails card below flagged emails card. |
| `dashboard/js/app.js` | Add `renderUnreadEmails()` function, call it from `loadDashboard()`. |
| `scriptable/morning-widget.js` | Add unread emails section to large widget (count + top 2-3 subjects). |

## New File: `src/collectors/outlook_ews.py`

Uses `exchangelib` library. Key design decisions:

- **Auth:** `exchangelib.Credentials(email, password)` with autodiscover
- **Calendar:** Query today's events from all calendars, return same shape as current `outlook.py`
- **Flagged emails:** Filter inbox by `is_flagged`, return subject + sender + date
- **Unread emails (24hrs):** Filter inbox by `is_read=False` and `datetime_received > now - 24hrs`, return subject + sender + date
- **Error handling:** If EWS connection fails (auth blocked, network), log error and update health status. Don't crash the cache job.

## New Endpoint: `POST /data/outlook`

Fallback for iOS Shortcut push. Same pattern as `/data/reminders`.

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

Stores data in the same in-memory cache the scheduler uses.

## Dashboard: Unread Emails Section

New card below "Flagged Emails" in `index.html`:
- Header: "Unread Emails (24h)" with envelope icon
- Each item: sender name + subject, one line per email
- Shows count badge in the header (e.g., "12")
- Truncate at 10 items with "and X more..." text

## Widget: Unread Emails

In the large widget, add an unread count below flagged emails:
- Show as a compact line: envelope icon + "12 unread" or "No new mail"
- Only show if count > 0 to save space

## Configuration

New `.env` variables:

```
MS_EMAIL=nic.brown@company.com
MS_PASSWORD=your-password-or-app-password
```

Both optional. If not set, the EWS collector is skipped and the system relies on the iOS Shortcut fallback (or the existing Graph API if configured).

## Testing Strategy

1. **Quick validation:** Try EWS connection with Nic's credentials on the Pi. If it connects, proceed. If blocked, pivot to iOS Shortcut.
2. **Unit tests:** Mock `exchangelib` responses for calendar, flagged, and unread queries.
3. **Integration:** Verify the summary endpoint includes `unread_emails` and the dashboard renders it.

## Rollback

If EWS doesn't work:
- The existing `outlook.py` (Graph API) is untouched
- Switch scheduler imports back
- Use iOS Shortcut fallback for calendar + email data
