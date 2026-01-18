"""Tests for API dependencies."""
import pytest
from unittest.mock import MagicMock, Mock, patch
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import get_current_user
from app.models.user import User
from app.exceptions.auth_exceptions import TokenInvalidError, TokenExpiredError


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def mock_credentials():
    """Create mock HTTP credentials."""
    credentials = MagicMock(spec=HTTPAuthorizationCredentials)
    credentials.credentials = "test-token"
    return credentials


def test_get_current_user_success(mock_credentials, mock_db):
    """Test get_current_user returns user when token is valid."""
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "user@example.com"

    # Mock decode_access_token to return valid payload
    with patch('app.api.dependencies.decode_access_token', return_value={"sub": "1"}):
        # Mock UserRepository
        with patch('app.api.dependencies.UserRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo_class.return_value = mock_repo

            result = get_current_user(credentials=mock_credentials, db=mock_db)

            assert result == mock_user
            mock_repo.get_by_id.assert_called_once_with(1)


def test_get_current_user_invalid_token(mock_credentials, mock_db):
    """Test get_current_user raises HTTPException when token is invalid."""
    # Mock decode_access_token to return None (invalid token)
    with patch('app.api.dependencies.decode_access_token', return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=mock_credentials, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication credentials" in exc_info.value.detail
        assert "WWW-Authenticate" in exc_info.value.headers


def test_get_current_user_missing_user_id(mock_credentials, mock_db):
    """Test get_current_user raises HTTPException when user_id is missing from token."""
    # Mock decode_access_token to return payload without 'sub'
    with patch('app.api.dependencies.decode_access_token', return_value={}):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials=mock_credentials, db=mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication credentials" in exc_info.value.detail


def test_get_current_user_not_found(mock_credentials, mock_db):
    """Test get_current_user raises HTTPException when user not found in database."""
    # Mock decode_access_token to return valid payload
    with patch('app.api.dependencies.decode_access_token', return_value={"sub": "999"}):
        # Mock UserRepository to return None (user not found)
        with patch('app.api.dependencies.UserRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.get_by_id.return_value = None
            mock_repo_class.return_value = mock_repo

            with pytest.raises(HTTPException) as exc_info:
                get_current_user(credentials=mock_credentials, db=mock_db)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "User not found" in exc_info.value.detail
            mock_repo.get_by_id.assert_called_once_with(999)
