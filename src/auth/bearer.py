from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config
from src.auth.jwt import verify_jwt

security = HTTPBearer()


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials

    # Fast path: exact bearer token match (widget, shortcuts, Power Automate)
    if token == src.config.settings.api_bearer_token:
        return token

    # Slow path: try JWT decode (dashboard after Face ID)
    try:
        verify_jwt(token)
        return token
    except Exception:
        pass

    raise HTTPException(status_code=401, detail="Invalid token")
