import pytest
from pydantic import ValidationError

from app.profile.schemas import HealthFactCreate, ProfileUpdate


def test_profile_update_accepts_adult_health_fields() -> None:
    request = ProfileUpdate(age=30, height_cm=175, weight_kg=70, allergies=["花生"])

    assert request.age == 30
    assert request.allergies == ["花生"]


def test_profile_update_rejects_child_age_for_v0_adult_scope() -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate(age=12)


def test_health_fact_defaults_to_not_granted_consent() -> None:
    request = HealthFactCreate(
        fact_type="allergy",
        value={"name": "花生"},
        consent_type="health_fact_storage",
        policy_version="v1",
    )

    assert request.consent_granted is False
