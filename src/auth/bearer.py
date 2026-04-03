from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config
from src.auth.jwt import verify_jwt

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials

    # Fast path: exact bearer token match (widget, shortcuts)
    if token == src.config.settings.api_bearer_token:
        return token

    # Slow path: try JWT decode (dashboard after Face ID)
    try:
        verify_jwt(token)
        return token
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token")


async def verify_bearer_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_optional),
) -> Optional[str]:
    """Allow unauthenticated access (dashboard behind Cloudflare Access).
    If a token is provided, it must be valid."""
    if credentials is None:
        return None
    token = credentials.credentials

    if token == src.config.settings.api_bearer_token:
        return token

    try:
        verify_jwt(token)
        return token
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token")
