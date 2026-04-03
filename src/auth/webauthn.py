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
