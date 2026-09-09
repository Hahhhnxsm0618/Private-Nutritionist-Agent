from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.auth.router import get_current_user
from app.main import app
from app.profile.router import get_profile_service
from app.profile.service import HealthProfileService


class FakeRepository:
    def __init__(self) -> None:
        self.profile = None
        self.facts = {}
        self.consents = []
        self.counter = 0

    async def get_profile(self, user_id):
        return self.profile if self.profile and self.profile.user_id == user_id else None

    async def upsert_profile(self, user_id, profile_data):
        if self.profile is None:
            self.profile = type("Profile", (), {
                "id": "profile-1",
                "user_id": user_id,
                "profile_data": {},
                "memory_enabled": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            })()
        self.profile.profile_data = {**self.profile.profile_data, **profile_data}
        return self.profile

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
        consent = type("Consent", (), {"id": f"consent-{len(self.consents) + 1}"})()
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


def test_profile_and_fact_api_enforces_consent_and_memory() -> None:
    repository = FakeRepository()
    service = HealthProfileService(repository)
    app.dependency_overrides[get_profile_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-1"})()
    client = TestClient(app)

    try:
        profile = client.patch("/api/v1/profile", json={"age": 30, "allergies": ["花生"]})
        assert profile.status_code == 200
        assert profile.json()["profile_data"]["age"] == 30

        denied = client.post(
            "/api/v1/profile/facts",
            json={
                "fact_type": "allergy",
                "value": {"name": "花生"},
                "consent_type": "health_fact_storage",
                "policy_version": "v1",
            },
        )
        assert denied.status_code == 403
        assert denied.json()["detail"]["code"] == "CONSENT_REQUIRED"

        created = client.post(
            "/api/v1/profile/facts",
            json={
                "fact_type": "allergy",
                "value": {"name": "花生"},
                "consent_type": "health_fact_storage",
                "policy_version": "v1",
                "consent_granted": True,
            },
        )
        assert created.status_code == 201
        fact_id = created.json()["id"]
        assert created.json()["status"] == "pending"

        confirmed = client.post(f"/api/v1/profile/facts/{fact_id}/confirm")
        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"

        corrected = client.patch(
            f"/api/v1/profile/facts/{fact_id}",
            json={"value": {"name": "花生", "severity": "severe"}},
        )
        assert corrected.status_code == 200
        assert corrected.json()["status"] == "corrected"

        disabled = client.post("/api/v1/profile/memory/disable")
        assert disabled.status_code == 200
        assert disabled.json()["memory_enabled"] is False

        blocked = client.post(
            "/api/v1/profile/facts",
            json={
                "fact_type": "avoidance",
                "value": {"name": "酒精"},
                "consent_type": "health_fact_storage",
                "policy_version": "v1",
                "consent_granted": True,
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["code"] == "MEMORY_DISABLED"

        deleted = client.delete(f"/api/v1/profile/facts/{fact_id}")
        assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()


def test_profile_api_rejects_cross_user_fact_lookup() -> None:
    service = HealthProfileService(FakeRepository())
    app.dependency_overrides[get_profile_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-1"})()
    client = TestClient(app)

    try:
        response = client.post("/api/v1/profile/facts/fact-from-other-user/confirm")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()
