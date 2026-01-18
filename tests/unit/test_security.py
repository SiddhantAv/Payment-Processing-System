"""Tests for security utilities."""
import pytest
from datetime import timedelta
from jose import JWTError, jwt

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.config import settings


def test_hash_password():
    """Test hash_password creates valid bcrypt hash."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert hashed != password
    assert len(hashed) > 0
    # Should be valid bcrypt hash (starts with $2b$)
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$") or hashed.startswith("$2y$")


def test_verify_password_correct():
    """Test verify_password returns True for correct password."""
    password = "testpassword123"
    hashed = hash_password(password)

    result = verify_password(password, hashed)

    assert result is True


def test_verify_password_incorrect():
    """Test verify_password returns False for incorrect password."""
    password = "testpassword123"
    hashed = hash_password(password)

    result = verify_password("wrongpassword", hashed)

    assert result is False


def test_verify_password_invalid_hash():
    """Test verify_password handles invalid hash gracefully."""
    result = verify_password("password", "invalid_hash_format")

    assert result is False


def test_create_access_token():
    """Test create_access_token creates valid JWT."""
    data = {"sub": "1"}
    token = create_access_token(data)

    assert token is not None
    assert isinstance(token, str)
    # Verify token can be decoded
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"


def test_create_access_token_with_custom_expiry():
    """Test create_access_token with custom expiry delta."""
    data = {"sub": "1"}
    custom_delta = timedelta(minutes=60)
    token = create_access_token(data, expires_delta=custom_delta)

    assert token is not None
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "1"


def test_decode_access_token_valid():
    """Test decode_access_token decodes valid token."""
    data = {"sub": "1"}
    token = create_access_token(data)

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "1"


def test_decode_access_token_invalid():
    """Test decode_access_token returns None for invalid token."""
    invalid_token = "invalid.token.here"

    payload = decode_access_token(invalid_token)

    assert payload is None


def test_decode_access_token_expired():
    """Test decode_access_token returns None for expired token."""
    # Create an expired token manually
    data = {"sub": "1"}
    expired_delta = timedelta(minutes=-60)  # Negative delta = expired
    expired_token = create_access_token(data, expires_delta=expired_delta)

    # Wait a bit and decode - should fail
    payload = decode_access_token(expired_token)

    # Should return None for expired token
    assert payload is None
