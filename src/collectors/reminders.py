from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List

class Reminder(BaseModel):
    title: str
    due: Optional[str] = None

class RemindersPayload(BaseModel):
    reminders: List[Reminder]

_stored_reminders: List[dict] = []
_last_push: Optional[str] = None

def store_reminders(reminders: List[Reminder]) -> int:
    global _stored_reminders, _last_push
    from datetime import datetime
    _stored_reminders = [r.model_dump() for r in reminders]
    _last_push = datetime.now().isoformat()
    return len(_stored_reminders)

def get_reminders() -> List[dict]:
    return _stored_reminders

def get_reminders_last_push() -> Optional[str]:
    return _last_push
