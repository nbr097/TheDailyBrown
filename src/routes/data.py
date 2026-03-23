from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List

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
