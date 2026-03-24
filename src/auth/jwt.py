from __future__ import annotations

import time

import jwt as pyjwt

import src.config


def _secret() -> str:
    return src.config.settings.api_bearer_token


def create_jwt(subject: str, expires_hours: float = 12) -> str:
    now = time.time()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_hours * 3600,
    }
    return pyjwt.encode(payload, _secret(), algorithm="HS256")


def verify_jwt(token: str) -> dict:
    return pyjwt.decode(token, _secret(), algorithms=["HS256"])
