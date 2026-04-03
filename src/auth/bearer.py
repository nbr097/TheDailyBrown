from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config

security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials
    if token == src.config.settings.api_bearer_token:
        return token
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
    raise HTTPException(status_code=401, detail="Invalid token")
