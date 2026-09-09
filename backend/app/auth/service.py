"""邮箱密码认证用例。"""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.db.session import Settings, settings


class AuthRepository(Protocol):
    async def find_user_by_email(self, email: str): ...
    async def find_user(self, user_id: str): ...
    async def create_user(self, email: str, password_hash: str): ...
    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ): ...
    async def find_session_by_hash(self, token_hash: str): ...
    async def revoke_session(self, session, now: datetime) -> None: ...
    async def commit(self) -> None: ...


class AuthenticationError(Exception):
    pass


class DuplicateEmailError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        *,
        auth_settings: Settings | None = None,
        jwt_secret_key: str | None = None,
    ) -> None:
        self.repository = repository
        if jwt_secret_key:
            self.settings = settings.model_copy(update={"jwt_secret_key": jwt_secret_key})
        else:
            self.settings = auth_settings or settings

    async def register(self, request: RegisterRequest) -> TokenResponse:
        email = str(request.email)
        if await self.repository.find_user_by_email(email):
            raise DuplicateEmailError
        user = await self.repository.create_user(email, hash_password(request.password))
        result = await self._issue_tokens(user)
        await self.repository.commit()
        return result

    async def login(self, request: LoginRequest) -> TokenResponse:
        user = await self.repository.find_user_by_email(str(request.email))
        if not user or not verify_password(request.password, user.password_hash):
            raise AuthenticationError
        if user.status != "active":
            raise AuthenticationError
        result = await self._issue_tokens(user)
        await self.repository.commit()
        return result

    async def refresh(self, request: RefreshRequest) -> TokenResponse:
        now = datetime.now(UTC)
        session = await self.repository.find_session_by_hash(
            hash_refresh_token(request.refresh_token)
        )
        if not session or session.revoked_at or self._is_expired(session.expires_at, now):
            raise AuthenticationError
        user = await self.repository.find_user(session.user_id)
        if not user or user.status != "active":
            raise AuthenticationError
        await self.repository.revoke_session(session, now)
        result = await self._issue_tokens(user, now=now)
        await self.repository.commit()
        return result

    async def logout(self, request: RefreshRequest) -> None:
        session = await self.repository.find_session_by_hash(
            hash_refresh_token(request.refresh_token)
        )
        if session and not session.revoked_at:
            await self.repository.revoke_session(session, datetime.now(UTC))
            await self.repository.commit()

    async def get_current_user(self, user_id: str):
        user = await self.repository.find_user(user_id)
        if not user or user.status != "active":
            raise AuthenticationError
        return user

    async def _issue_tokens(self, user, *, now: datetime | None = None) -> TokenResponse:
        issued_at = now or datetime.now(UTC)
        refresh_token = generate_refresh_token()
        await self.repository.create_session(
            user.id,
            hash_refresh_token(refresh_token),
            issued_at + timedelta(days=self.settings.refresh_token_expire_days),
            issued_at,
        )
        return TokenResponse(
            access_token=create_access_token(user.id, self.settings, now=issued_at),
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    def _is_expired(expires_at: datetime, now: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now
