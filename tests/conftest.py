import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Ensure required environment variables exist before importing app settings
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("AUTHORIZE_NET_API_LOGIN_ID", "test-login")
os.environ.setdefault("AUTHORIZE_NET_TRANSACTION_KEY", "test-key")

from app.main import app
from app.db.session import get_db
from app.api.dependencies import get_current_user


@pytest.fixture
def test_db():
    """Provide a mocked database session."""
    return MagicMock()


@pytest.fixture
def client(test_db):
    """Create a TestClient with DB dependency overridden."""

    def _override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_user():
    """Provide a simple authenticated user object."""
    return SimpleNamespace(id=1, email="user@example.com")


@pytest.fixture
def auth_override(authenticated_user):
    """Override JWT dependency with a fixed user."""

    def _override_get_current_user():
        return authenticated_user

    app.dependency_overrides[get_current_user] = _override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
