import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.config import get_settings

settings = get_settings()
_hasher = PasswordHasher()

JWT_ALGORITHM = "HS256"


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (plaintext_token, token_hash, expires_at)."""
    plaintext = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(plaintext)
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    return plaintext, token_hash, expires_at


def hash_refresh_token(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()
