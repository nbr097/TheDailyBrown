from __future__ import annotations

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import src.config

security = HTTPBearer()


async def verify_bearer(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials
    if token == src.config.settings.api_bearer_token:
        return token
    raise HTTPException(status_code=401, detail="Invalid token")
