"""健康档案和健康事实的业务规则。"""

from typing import Protocol

from app.profile.schemas import HealthFactCreate, HealthFactUpdate, ProfileUpdate


class ResourceNotFoundError(Exception):
    pass


class ConsentRequiredError(Exception):
    pass


class MemoryDisabledError(Exception):
    pass


class ProfileRepository(Protocol):
    async def get_profile(self, user_id: str): ...
    async def upsert_profile(self, user_id: str, profile_data: dict): ...
    async def disable_memory(self, user_id: str): ...
    async def list_facts(self, user_id: str): ...
    async def get_fact(self, user_id: str, fact_id: str): ...
    async def create_consent(self, user_id: str, consent_type: str, policy_version: str): ...
    async def create_fact(self, user_id: str, consent_id: str, fact_type: str, value: dict): ...
    async def update_fact(self, fact, value: dict): ...
    async def confirm_fact(self, fact): ...
    async def delete_fact(self, fact): ...
    async def commit(self) -> None: ...


class HealthProfileService:
    def __init__(self, repository: ProfileRepository) -> None:
        self.repository = repository

    async def get_profile(self, user_id: str):
        profile = await self.repository.get_profile(user_id)
        if not profile:
            raise ResourceNotFoundError
        return profile

    async def update_profile(self, user_id: str, request: ProfileUpdate):
        profile = await self.repository.upsert_profile(
            user_id,
            request.model_dump(exclude_unset=True, mode="json"),
        )
        await self.repository.commit()
        return profile

    async def disable_memory(self, user_id: str):
        profile = await self.repository.disable_memory(user_id)
        await self.repository.commit()
        return profile

    async def list_facts(self, user_id: str):
        return await self.repository.list_facts(user_id)

    async def create_fact(self, user_id: str, request: HealthFactCreate):
        if not request.consent_granted:
            raise ConsentRequiredError
        profile = await self.repository.get_profile(user_id)
        if profile and not profile.memory_enabled:
            raise MemoryDisabledError
        consent = await self.repository.create_consent(
            user_id, request.consent_type, request.policy_version
        )
        fact = await self.repository.create_fact(
            user_id, consent.id, request.fact_type, request.value
        )
        await self.repository.commit()
        return fact

    async def update_fact(self, user_id: str, fact_id: str, request: HealthFactUpdate):
        fact = await self._get_fact(user_id, fact_id)
        updated = await self.repository.update_fact(fact, request.value)
        await self.repository.commit()
        return updated

    async def confirm_fact(self, user_id: str, fact_id: str):
        fact = await self._get_fact(user_id, fact_id)
        confirmed = await self.repository.confirm_fact(fact)
        await self.repository.commit()
        return confirmed

    async def delete_fact(self, user_id: str, fact_id: str) -> None:
        fact = await self._get_fact(user_id, fact_id)
        await self.repository.delete_fact(fact)
        await self.repository.commit()

    async def _get_fact(self, user_id: str, fact_id: str):
        fact = await self.repository.get_fact(user_id, fact_id)
        if not fact:
            raise ResourceNotFoundError
        return fact
