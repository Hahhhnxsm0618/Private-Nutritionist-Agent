"""认证相关的 SQLAlchemy 数据访问。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.models.user import AuthSession, User


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_user_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def find_user(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def create_user(self, email: str, password_hash: str) -> User:
        user = User(email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_session(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        created_at: datetime,
    ) -> AuthSession:
        session = AuthSession(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=created_at,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def find_session_by_hash(self, token_hash: str) -> AuthSession | None:
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_session(self, session: AuthSession, now: datetime) -> None:
        session.revoked_at = now
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()


def prepare_password_hash(password: str) -> str:
    """保留一个单一入口，避免仓储调用层绕过密码原语。"""
    return hash_password(password)
