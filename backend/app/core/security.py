"""Password hashing (argon2) and JWT creation/verification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

_hasher = PasswordHasher()

TokenType = Literal["access", "refresh", "reset"]


# --------------------------------------------------------------------------- #
# Passwords (argon2 — NOT bcrypt)
# --------------------------------------------------------------------------- #
def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _hasher.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001 - malformed hash etc. => not verified
        return False


# --------------------------------------------------------------------------- #
# JWT
# --------------------------------------------------------------------------- #
def _create_token(subject: str, token_type: TokenType, expires: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(
        subject, "access", timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(
        subject, "refresh", timedelta(days=settings.refresh_token_expire_days)
    )


def create_reset_token(subject: str) -> str:
    settings = get_settings()
    return _create_token(
        subject, "reset", timedelta(minutes=settings.reset_token_expire_minutes)
    )


def decode_token(token: str, *, expected_type: TokenType) -> str | None:
    """Return the subject if the token is valid and of the expected type, else None."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) else None
