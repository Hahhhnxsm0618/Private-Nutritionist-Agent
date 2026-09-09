"""健康档案和健康事实的 SQLAlchemy 数据访问。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Consent, HealthFact, HealthProfile


class SqlAlchemyProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_profile(self, user_id: str) -> HealthProfile | None:
        result = await self.session.execute(
            select(HealthProfile).where(HealthProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_profile(self, user_id: str, profile_data: dict) -> HealthProfile:
        profile = await self.get_profile(user_id)
        if profile is None:
            profile = HealthProfile(user_id=user_id, profile_data=profile_data)
            self.session.add(profile)
        else:
            profile.profile_data = {**(profile.profile_data or {}), **profile_data}
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def disable_memory(self, user_id: str) -> HealthProfile:
        profile = await self.upsert_profile(user_id, {})
        profile.memory_enabled = False
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def list_facts(self, user_id: str) -> list[HealthFact]:
        result = await self.session.execute(
            select(HealthFact)
            .where(HealthFact.user_id == user_id)
            .order_by(HealthFact.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_fact(self, user_id: str, fact_id: str) -> HealthFact | None:
        result = await self.session.execute(
            select(HealthFact).where(HealthFact.id == fact_id, HealthFact.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_consent(
        self, user_id: str, consent_type: str, policy_version: str
    ) -> Consent:
        consent = Consent(
            user_id=user_id,
            consent_type=consent_type,
            policy_version=policy_version,
            granted=True,
            granted_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        self.session.add(consent)
        await self.session.flush()
        await self.session.refresh(consent)
        return consent

    async def create_fact(
        self, user_id: str, consent_id: str, fact_type: str, value: dict
    ) -> HealthFact:
        fact = HealthFact(
            user_id=user_id,
            consent_id=consent_id,
            fact_type=fact_type,
            value=value,
            source_type="user",
            status="pending",
        )
        self.session.add(fact)
        await self.session.flush()
        await self.session.refresh(fact)
        return fact

    async def update_fact(self, fact: HealthFact, value: dict) -> HealthFact:
        fact.value = value
        fact.status = "corrected"
        await self.session.flush()
        await self.session.refresh(fact)
        return fact

    async def confirm_fact(self, fact: HealthFact) -> HealthFact:
        fact.status = "confirmed"
        await self.session.flush()
        await self.session.refresh(fact)
        return fact

    async def delete_fact(self, fact: HealthFact) -> None:
        fact.status = "expired"
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
