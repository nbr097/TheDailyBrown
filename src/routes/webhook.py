from __future__ import annotations

import hashlib
import hmac
import json
import time
import logging
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException

import src.config

router = APIRouter()
logger = logging.getLogger(__name__)

TRIGGER_FILE = Path("/app/data/deploy-trigger.json")


@router.post("/webhook/github")
async def github_webhook(request: Request):
    """Handle GitHub push webhook — write a trigger file for the host deploy watcher."""
    secret = src.config.settings.github_webhook_secret
    if secret:
        signature = request.headers.get("X-Hub-Signature-256", "")
        body = await request.body()
        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise HTTPException(status_code=401, detail="Invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    if event == "ping":
        return {"status": "pong"}
    if event != "push":
        return {"status": "ignored", "event": event}

    payload = await request.json()
    ref = payload.get("ref", "")

    logger.info(f"GitHub push webhook received on {ref}")

    TRIGGER_FILE.write_text(json.dumps({
        "ref": ref,
        "timestamp": time.time(),
        "pusher": payload.get("pusher", {}).get("name", "unknown"),
    }))

    return {"status": "deploy_triggered", "ref": ref}
