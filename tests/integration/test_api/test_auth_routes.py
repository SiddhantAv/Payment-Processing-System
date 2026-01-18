from types import SimpleNamespace

from app.services.auth_service import AuthService


def test_register_success(client, monkeypatch):
    user = SimpleNamespace(id=1, email="new@example.com", created_at="2024-01-01T00:00:00Z")

    def fake_register(self, email, password):
        return user

    monkeypatch.setattr(AuthService, "register_user", fake_register)

    response = client.post("/api/v1/auth/register", json={"email": "new@example.com", "password": "password123"})

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["email"] == "new@example.com"


def test_login_success(client, monkeypatch):
    def fake_login(self, email, password):
        return {"access_token": "test-token", "token_type": "bearer"}

    monkeypatch.setattr(AuthService, "login", fake_login)

    response = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "password123"})

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "test-token"
    assert data["token_type"] == "bearer"
