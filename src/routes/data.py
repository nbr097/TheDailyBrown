from fastapi import APIRouter, Depends
from src.auth.bearer import verify_bearer
from src.collectors.reminders import RemindersPayload, store_reminders

router = APIRouter()

@router.post("/data/reminders")
async def post_reminders(payload: RemindersPayload, _=Depends(verify_bearer)):
    count = store_reminders(payload.reminders)
    return {"stored": count}
