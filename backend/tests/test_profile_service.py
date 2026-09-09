from datetime import UTC, datetime

import pytest

from app.profile.schemas import HealthFactCreate, ProfileUpdate
from app.profile.service import (
    ConsentRequiredError,
    HealthProfileService,
    MemoryDisabledError,
    ResourceNotFoundError,
)


class FakeRepository:
    def __init__(self) -> None:
        self.profiles = {}
        self.facts = {}
        self.consents = []
        self.counter = 0

    async def get_profile(self, user_id):
        return self.profiles.get(user_id)

    async def upsert_profile(self, user_id, profile_data):
        profile = self.profiles.get(user_id)
        if profile is None:
            profile = type("Profile", (), {
                "id": "profile-1",
                "user_id": user_id,
                "profile_data": {},
                "memory_enabled": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            })()
            self.profiles[user_id] = profile
        profile.profile_data = profile_data
        return profile

    async def disable_memory(self, user_id):
        profile = await self.upsert_profile(user_id, {})
        profile.memory_enabled = False
        return profile

    async def list_facts(self, user_id):
        return [fact for fact in self.facts.values() if fact.user_id == user_id]

    async def get_fact(self, user_id, fact_id):
        fact = self.facts.get(fact_id)
        return fact if fact and fact.user_id == user_id else None

    async def create_consent(self, user_id, consent_type, policy_version):
        consent = type("Consent", (), {
            "id": f"consent-{len(self.consents) + 1}",
            "user_id": user_id,
            "consent_type": consent_type,
            "policy_version": policy_version,
            "granted": True,
            "granted_at": datetime.now(UTC),
            "withdrawn_at": None,
            "created_at": datetime.now(UTC),
        })()
        self.consents.append(consent)
        return consent

    async def create_fact(self, user_id, consent_id, fact_type, value):
        self.counter += 1
        fact = type("Fact", (), {
            "id": f"fact-{self.counter}",
            "user_id": user_id,
            "fact_type": fact_type,
            "value": value,
            "source_type": "user",
            "source_message_id": None,
            "status": "pending",
            "consent_id": consent_id,
            "valid_until": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        })()
        self.facts[fact.id] = fact
        return fact

    async def update_fact(self, fact, value):
        fact.value = value
        fact.status = "corrected"
        return fact

    async def confirm_fact(self, fact):
        fact.status = "confirmed"
        return fact

    async def delete_fact(self, fact):
        fact.status = "expired"

    async def commit(self):
        return None


@pytest.fixture
def profile_service() -> HealthProfileService:
    return HealthProfileService(FakeRepository())


@pytest.mark.asyncio
async def test_profile_update_is_scoped_to_current_user(profile_service):
    profile = await profile_service.update_profile(
        "user-1", ProfileUpdate(age=30, allergies=["花生"])
    )

    assert profile.user_id == "user-1"
    assert profile.profile_data["age"] == 30
    assert profile.profile_data["allergies"] == ["花生"]


@pytest.mark.asyncio
async def test_health_fact_requires_consent_and_starts_pending(profile_service):
    request = HealthFactCreate(
        fact_type="allergy",
        value={"name": "花生"},
        consent_type="health_fact_storage",
        policy_version="v1",
        consent_granted=True,
    )

    fact = await profile_service.create_fact("user-1", request)

    assert fact.status == "pending"
    assert fact.consent_id == "consent-1"


@pytest.mark.asyncio
async def test_health_fact_without_consent_is_rejected(profile_service):
    request = HealthFactCreate(
        fact_type="allergy",
        value={"name": "花生"},
        consent_type="health_fact_storage",
        policy_version="v1",
        consent_granted=False,
    )

    with pytest.raises(ConsentRequiredError):
        await profile_service.create_fact("user-1", request)


@pytest.mark.asyncio
async def test_disabled_memory_blocks_new_health_fact(profile_service):
    await profile_service.disable_memory("user-1")
    request = HealthFactCreate(
        fact_type="allergy",
        value={"name": "花生"},
        consent_type="health_fact_storage",
        policy_version="v1",
        consent_granted=True,
    )

    with pytest.raises(MemoryDisabledError):
        await profile_service.create_fact("user-1", request)


@pytest.mark.asyncio
async def test_fact_from_another_user_is_not_found(profile_service):
    with pytest.raises(ResourceNotFoundError):
        await profile_service.confirm_fact("user-1", "fact-from-other-user")
