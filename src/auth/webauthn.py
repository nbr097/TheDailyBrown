from __future__ import annotations

import json
import logging
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
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

import src.config
from src.database import get_db

router = APIRouter()


def _rp_id() -> str:
    return src.config.settings.dashboard_domain


def _origin() -> str:
    return f"https://{_rp_id()}"

# In-memory challenge store — keeps recent challenges valid (single-user app)
# Uses a set of valid challenges instead of a single key to avoid race conditions
_valid_challenges: set[bytes] = set()


def _get_stored_credentials() -> list[dict[str, Any]]:
    """Retrieve all stored WebAuthn credentials from the database."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, public_key, sign_count FROM webauthn_credentials"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/auth/webauthn/register-options")
async def register_options():
    creds = _get_stored_credentials()
    if len(creds) >= 1:
        raise HTTPException(
            status_code=400,
            detail="A credential is already registered. Only 1 allowed.",
        )

    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name="Morning Briefing",
        user_name="nic",
        user_display_name="Nic",
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    _valid_challenges.add(options.challenge)

    return json.loads(options_to_json(options))


@router.post("/auth/webauthn/register")
async def register(request: Request):
    body = await request.json()

    # Find matching challenge from the credential's clientDataJSON
    # The webauthn library handles challenge matching internally
    # We just need to verify the challenge was one we issued
    import base64
    import json as _json
    client_data = _json.loads(base64.urlsafe_b64decode(body["response"]["clientDataJSON"] + "=="))
    challenge_b64 = client_data["challenge"]
    # Decode the challenge from base64url
    challenge_bytes = base64.urlsafe_b64decode(challenge_b64 + "==")

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

    conn = get_db()
    conn.execute(
        "INSERT INTO webauthn_credentials (id, public_key, sign_count, created_at) "
        "VALUES (?, ?, ?, ?)",
        (
            verification.credential_id.hex(),
            verification.credential_public_key,
            verification.sign_count,
            time.time(),
        ),
    )
    conn.commit()
    conn.close()

    return {"verified": True}


@router.get("/auth/webauthn/authenticate-options")
async def authenticate_options():
    creds = _get_stored_credentials()

    allow_credentials = [
        PublicKeyCredentialDescriptor(id=bytes.fromhex(c["id"])) for c in creds
    ]

    options = generate_authentication_options(
        rp_id=_rp_id(),
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    _valid_challenges.add(options.challenge)

    return json.loads(options_to_json(options))


@router.post("/auth/webauthn/authenticate")
async def authenticate(request: Request):
    body = await request.json()

    # Extract challenge from clientDataJSON to match against our valid set
    import base64
    import json as _json
    client_data = _json.loads(base64.urlsafe_b64decode(body["response"]["clientDataJSON"] + "=="))
    challenge_b64 = client_data["challenge"]
    challenge_bytes = base64.urlsafe_b64decode(challenge_b64 + "==")

    if challenge_bytes not in _valid_challenges:
        raise HTTPException(status_code=400, detail="No authentication in progress")
    _valid_challenges.discard(challenge_bytes)

    # Browser sends credential ID as base64url, DB stores as hex
    credential_id_b64 = body.get("id", "")
    try:
        credential_id_hex = base64.urlsafe_b64decode(credential_id_b64 + "==").hex()
    except Exception:
        credential_id_hex = credential_id_b64

    creds = _get_stored_credentials()
    stored = next((c for c in creds if c["id"] == credential_id_hex), None)
    if not stored:
        logger.error(f"Unknown credential. Browser sent: {credential_id_b64}, converted to hex: {credential_id_hex}")
        logger.error(f"Stored cred IDs: {[c['id'] for c in creds]}")
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
        logger.error(f"  credential_id: {credential_id_hex}")
        logger.error(f"  expected_origin: {_origin()}")
        logger.error(f"  expected_rp_id: {_rp_id()}")
        logger.error(f"  client_data origin: {client_data.get('origin', 'N/A')}")
        logger.error(f"  client_data type: {client_data.get('type', 'N/A')}")
        raise HTTPException(status_code=400, detail=str(exc))

    conn = get_db()
    conn.execute(
        "UPDATE webauthn_credentials SET sign_count = ? WHERE id = ?",
        (verification.new_sign_count, credential_id_hex),
    )
    conn.commit()
    conn.close()

    return {"verified": True}
