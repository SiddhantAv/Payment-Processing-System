"""Tests for UserRepository."""
import pytest
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, Mock, patch

from app.repositories.database.user_repository import UserRepository
from app.models.user import User


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock(spec=Session)


@pytest.fixture
def user_repo(mock_db):
    """Create UserRepository instance with mocked DB."""
    return UserRepository(mock_db)


def test_get_by_id_found(user_repo, mock_db):
    """Test get_by_id returns user when found."""
    mock_user = MagicMock(spec=User)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = user_repo.get_by_id(1)

    assert result == mock_user
    mock_db.query.assert_called_once_with(User)


def test_get_by_id_not_found(user_repo, mock_db):
    """Test get_by_id returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = user_repo.get_by_id(999)

    assert result is None


def test_get_by_email_found(user_repo, mock_db):
    """Test get_by_email returns user when found."""
    mock_user = MagicMock(spec=User)
    mock_user.email = "test@example.com"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = user_repo.get_by_email("test@example.com")

    assert result == mock_user
    assert result.email == "test@example.com"
    mock_db.query.assert_called_once_with(User)


def test_get_by_email_not_found(user_repo, mock_db):
    """Test get_by_email returns None when not found."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = user_repo.get_by_email("nonexistent@example.com")

    assert result is None


def test_create(user_repo, mock_db):
    """Test create adds user to database."""
    from unittest.mock import patch
    mock_user = MagicMock(spec=User)
    mock_db.add = Mock()
    mock_db.commit = Mock()
    mock_db.refresh = Mock()

    # Mock the User model constructor
    with patch('app.repositories.database.user_repository.User', return_value=mock_user):
        result = user_repo.create(email="test@example.com", hashed_password="hashed_pw")

    assert result == mock_user
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_user)
