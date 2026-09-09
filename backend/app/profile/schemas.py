"""健康档案和健康事实的请求、响应 Schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProfileUpdate(BaseModel):
    age: int | None = Field(default=None, ge=18, le=120)
    sex: str | None = Field(default=None, max_length=32)
    height_cm: float | None = Field(default=None, ge=50, le=250)
    weight_kg: float | None = Field(default=None, ge=20, le=500)
    activity_level: str | None = Field(default=None, max_length=32)
    dietary_preferences: list[str] | None = None
    allergies: list[str] | None = None
    avoidances: list[str] | None = None
    goals: list[str] | None = None
    cooking_conditions: list[str] | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    profile_data: dict[str, Any]
    memory_enabled: bool
    created_at: datetime
    updated_at: datetime


class HealthFactCreate(BaseModel):
    fact_type: str = Field(min_length=1, max_length=64)
    value: dict[str, Any] = Field(min_length=1)
    consent_type: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=64)
    consent_granted: bool = False


class HealthFactUpdate(BaseModel):
    value: dict[str, Any] = Field(min_length=1)


class HealthFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    fact_type: str
    value: dict[str, Any]
    source_type: str
    source_message_id: str | None
    status: str
    consent_id: str | None
    valid_until: datetime | None
    created_at: datetime
    updated_at: datetime
