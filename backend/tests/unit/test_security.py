from __future__ import annotations

from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.security import (
    ALGORITHM,
    create_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    password = "SecureTestPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_create_access_token():
    subject = "user_123"
    token = create_access_token(subject, expires_delta=timedelta(minutes=15))
    assert isinstance(token, str)

    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == subject
    assert "exp" in payload
