from types import SimpleNamespace

import pytest

from app.services.auth_service import AuthService
from app.core.security import hash_password
from app.exceptions.auth_exceptions import InvalidCredentialsError


class FakeUserRepo:
    def __init__(self):
        self.users = {}
        self._id = 1

    def get_by_email(self, email: str):
        return self.users.get(email)

    def create(self, email: str, hashed_password: str):
        user = SimpleNamespace(
            id=self._id,
            email=email,
            hashed_password=hashed_password,
            created_at="2024-01-01T00:00:00Z",
        )
        self.users[email] = user
        self._id += 1
        return user


def test_register_user_success():
    auth_service = AuthService(db=None)
    auth_service.user_repository = FakeUserRepo()

    user = auth_service.register_user("new@example.com", "password123")

    assert user.id == 1
    assert user.email == "new@example.com"
    assert user.hashed_password != "password123"


def test_register_user_email_exists():
    auth_service = AuthService(db=None)
    repo = FakeUserRepo()
    repo.create("exists@example.com", hash_password("password123"))
    auth_service.user_repository = repo

    with pytest.raises(ValueError, match="Email already exists"):
        auth_service.register_user("exists@example.com", "password123")


def test_login_success():
    auth_service = AuthService(db=None)
    repo = FakeUserRepo()
    repo.create("user@example.com", hash_password("password123"))
    auth_service.user_repository = repo

    token_data = auth_service.login("user@example.com", "password123")

    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


def test_login_invalid_credentials():
    auth_service = AuthService(db=None)
    repo = FakeUserRepo()
    repo.create("user@example.com", hash_password("password123"))
    auth_service.user_repository = repo

    with pytest.raises(InvalidCredentialsError):
        auth_service.login("user@example.com", "wrongpassword")
