from datetime import datetime

from fastapi.testclient import TestClient

from app.auth.router import get_auth_service
from app.auth.service import AuthService
from app.main import app


class FakeRepository:
    def __init__(self) -> None:
        self.users = {}
        self.sessions = {}
        self.session_counter = 0

    async def find_user_by_email(self, email):
        return self.users.get(email)

    async def find_user(self, user_id):
        return next((user for user in self.users.values() if user.id == user_id), None)

    async def create_user(self, email, password_hash):
        user = type("User", (), {
            "id": f"user-{len(self.users) + 1}",
            "email": email,
            "password_hash": password_hash,
            "role": "user",
            "status": "active",
        })()
        self.users[email] = user
        return user

    async def create_session(self, user_id, token_hash, expires_at, created_at):
        self.session_counter += 1
        session = type("Session", (), {
            "id": f"session-{self.session_counter}",
            "user_id": user_id,
            "token_hash": token_hash,
            "expires_at": expires_at,
            "revoked_at": None,
        })()
        self.sessions[token_hash] = session
        return session

    async def find_session_by_hash(self, token_hash):
        return self.sessions.get(token_hash)

    async def revoke_session(self, session, now: datetime):
        session.revoked_at = now

    async def commit(self):
        return None


def test_auth_api_register_login_me_refresh_and_logout() -> None:
    service = AuthService(FakeRepository(), jwt_secret_key="test-secret-key-with-enough-entropy")
    app.dependency_overrides[get_auth_service] = lambda: service
    client = TestClient(app)

    try:
        credentials = {"email": "user@example.com", "password": "Strong-password-123!"}
        registered = client.post("/api/v1/auth/register", json=credentials)
        assert registered.status_code == 201
        tokens = registered.json()
        assert tokens["token_type"] == "bearer"

        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == "user@example.com"

        refreshed = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refreshed.status_code == 200
        assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

        logout = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refreshed.json()["refresh_token"]},
        )
        assert logout.status_code == 204

        login = client.post("/api/v1/auth/login", json=credentials)
        assert login.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_auth_api_hides_login_failure_reason() -> None:
    service = AuthService(FakeRepository(), jwt_secret_key="test-secret-key-with-enough-entropy")
    app.dependency_overrides[get_auth_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "Strong-password-123!"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "AUTHENTICATION_FAILED"
    finally:
        app.dependency_overrides.clear()


def test_auth_api_requires_bearer_token_for_me() -> None:
    response = TestClient(app).get("/api/v1/auth/me")

    assert response.status_code == 401
