import jwt
import pytest

from src.domain.shared.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_roundtrip():
    hashed = hash_password("my-secret-password")
    assert hashed != "my-secret-password"
    assert verify_password("my-secret-password", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("my-secret-password")
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"


def test_decode_access_token_rejects_tampered_token():
    token = create_access_token("user-123")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token + "tampered")


def test_generate_refresh_token_hash_matches():
    plaintext, token_hash, expires_at = generate_refresh_token()
    assert hash_refresh_token(plaintext) == token_hash
    assert expires_at is not None
