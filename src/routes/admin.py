from __future__ import annotations

import socket

from fastapi import APIRouter, Depends, HTTPException

from src.auth.bearer import verify_bearer_optional

router = APIRouter()

UPDATER_SOCKET = "/run/updater/updater.sock"


def signal_updater() -> bool:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(UPDATER_SOCKET)
        sock.sendall(b"update")
        sock.close()
        return True
    except Exception:
        return False


@router.post("/admin/update")
async def trigger_update(_=Depends(verify_bearer_optional)):
    if signal_updater():
        return {"message": "Update initiated"}
    raise HTTPException(status_code=503, detail="Updater sidecar not available")
