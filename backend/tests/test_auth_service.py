from datetime import datetime

import pytest

from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest
from app.auth.service import (
    AuthenticationError,
    AuthService,
    DuplicateEmailError,
)


class FakeRepository:
    def __init__(self) -> None:
        self.users: dict[str, object] = {}
        self.sessions: dict[str, object] = {}
        self.session_counter = 0

    async def find_user_by_email(self, email: str):
        return self.users.get(email)

    async def find_user(self, user_id: str):
        return next((user for user in self.users.values() if user.id == user_id), None)

    async def create_user(self, email: str, password_hash: str):
        user = type("User", (), {
            "id": f"user-{len(self.users) + 1}",
            "email": email,
            "password_hash": password_hash,
            "role": "user",
            "status": "active",
        })()
        self.users[email] = user
        return user

    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ):
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

    async def find_session_by_hash(self, token_hash: str):
        return self.sessions.get(token_hash)

    async def revoke_session(self, session, now: datetime) -> None:
        session.revoked_at = now

    async def commit(self) -> None:
        return None


@pytest.fixture
def auth_service() -> AuthService:
    return AuthService(FakeRepository(), jwt_secret_key="test-secret-key-with-enough-entropy")


@pytest.mark.asyncio
async def test_register_normalizes_email_and_returns_tokens(auth_service: AuthService) -> None:
    result = await auth_service.register(
        RegisterRequest(email=" User@Example.COM ", password="Strong-password-123!")
    )

    assert result.user.email == "user@example.com"
    assert result.access_token
    assert result.refresh_token


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(auth_service: AuthService) -> None:
    request = RegisterRequest(email="user@example.com", password="Strong-password-123!")
    await auth_service.register(request)

    with pytest.raises(DuplicateEmailError):
        await auth_service.register(request)


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_without_account_detail(
    auth_service: AuthService,
) -> None:
    await auth_service.register(
        RegisterRequest(email="user@example.com", password="Strong-password-123!")
    )

    with pytest.raises(AuthenticationError):
        await auth_service.login(
            LoginRequest(email="user@example.com", password="wrong-password")
        )


@pytest.mark.asyncio
async def test_refresh_rotates_session_and_rejects_old_token(auth_service: AuthService) -> None:
    registered = await auth_service.register(
        RegisterRequest(email="user@example.com", password="Strong-password-123!")
    )

    refreshed = await auth_service.refresh(RefreshRequest(refresh_token=registered.refresh_token))
    assert refreshed.refresh_token != registered.refresh_token

    with pytest.raises(AuthenticationError):
        await auth_service.refresh(RefreshRequest(refresh_token=registered.refresh_token))


@pytest.mark.asyncio
async def test_logout_is_idempotent(auth_service: AuthService) -> None:
    registered = await auth_service.register(
        RegisterRequest(email="user@example.com", password="Strong-password-123!")
    )

    await auth_service.logout(RefreshRequest(refresh_token=registered.refresh_token))
    await auth_service.logout(RefreshRequest(refresh_token=registered.refresh_token))
