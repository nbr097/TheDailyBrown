from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import src.config

security = HTTPBearer()

async def verify_bearer(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    if credentials.credentials != src.config.settings.api_bearer_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials
