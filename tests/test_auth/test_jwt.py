from __future__ import annotations

import time
import pytest


def test_create_jwt_returns_string():
    from src.auth.jwt import create_jwt
    token = create_jwt("nic")
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_jwt_roundtrip():
    from src.auth.jwt import create_jwt, verify_jwt
    token = create_jwt("nic")
    payload = verify_jwt(token)
    assert payload["sub"] == "nic"
    assert "iat" in payload
    assert "exp" in payload


def test_verify_jwt_expired():
    from src.auth.jwt import create_jwt, verify_jwt
    token = create_jwt("nic", expires_hours=-1)
    with pytest.raises(Exception):
        verify_jwt(token)


def test_verify_jwt_invalid_signature():
    import jwt as pyjwt
    token = pyjwt.encode({"sub": "nic", "exp": time.time() + 3600}, "wrong-secret", algorithm="HS256")
    from src.auth.jwt import verify_jwt
    with pytest.raises(Exception):
        verify_jwt(token)


def test_verify_jwt_garbage_input():
    from src.auth.jwt import verify_jwt
    with pytest.raises(Exception):
        verify_jwt("not.a.jwt")


def test_create_jwt_default_expiry_is_12_hours():
    from src.auth.jwt import create_jwt, verify_jwt
    token = create_jwt("nic")
    payload = verify_jwt(token)
    diff = payload["exp"] - payload["iat"]
    assert abs(diff - 12 * 3600) < 5
