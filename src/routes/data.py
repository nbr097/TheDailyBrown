from fastapi import APIRouter, Depends, Request
from src.auth.bearer import verify_bearer
from src.collectors.reminders import RemindersPayload, store_reminders
from src.scheduler import set_cached_outlook_data, _update_system_status

router = APIRouter()


def _transform_calendar(raw_events: list) -> list[dict]:
    """Transform raw Outlook calendar events to our format."""
    events = []
    for ev in raw_events:
        if not isinstance(ev, dict):
            continue
        # Use startWithTimeZone if available (has timezone), fallback to start
        start = ev.get("startWithTimeZone") or ev.get("start", "")
        end = ev.get("endWithTimeZone") or ev.get("end", "")
        events.append({
            "subject": ev.get("subject", ""),
            "start": start,
            "end": end,
            "location": ev.get("location", ""),
            "teams_link": "",
            "is_all_day": ev.get("isAllDay", False),
            "source": "work",
        })
    return events


def _transform_emails(raw_emails: list) -> list[dict]:
    """Transform raw Outlook emails to our format."""
    emails = []
    for em in raw_emails:
        if not isinstance(em, dict):
            continue
        # Outlook 'from' is a plain email string like "boss@company.com"
        from_raw = em.get("from", "")
        if isinstance(from_raw, dict):
            # Graph API format: {emailAddress: {name, address}}
            addr_obj = from_raw.get("emailAddress", from_raw)
            from_name = addr_obj.get("name", "")
            from_address = addr_obj.get("address", "")
        else:
            # Power Automate format: plain email string
            from_address = str(from_raw)
            # Extract name part before @ for display
            from_name = from_address.split("@")[0].replace(".", " ").title() if "@" in from_address else from_address

        emails.append({
            "subject": em.get("subject", ""),
            "from_name": em.get("from_name", from_name),
            "from_address": em.get("from_address", from_address),
            "received": em.get("receivedDateTime") or em.get("received", ""),
            "source": "work",
        })
    return emails


@router.post("/data/reminders")
async def post_reminders(payload: RemindersPayload, _=Depends(verify_bearer)):
    count = store_reminders(payload.reminders)
    return {"stored": count}


@router.post("/data/outlook")
async def post_outlook(request: Request, _=Depends(verify_bearer)):
    """Accept raw Outlook data from Power Automate and transform to our format."""
    raw = await request.json()

    calendar = _transform_calendar(raw.get("calendar", []))
    flagged = _transform_emails(raw.get("flagged_emails", []))
    unread = _transform_emails(raw.get("unread_emails", []))

    set_cached_outlook_data(
        calendar=calendar,
        flagged_emails=flagged,
        unread_emails=unread,
    )
    _update_system_status("microsoft_graph", True)

    return {
        "stored_calendar": len(calendar),
        "stored_flagged": len(flagged),
        "stored_unread": len(unread),
    }
