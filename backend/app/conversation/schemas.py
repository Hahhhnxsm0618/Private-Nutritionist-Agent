"""对话会话和消息的请求、响应 Schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.safety.rules import SafetyDecision


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str | None
    status: str
    last_active_at: datetime
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message content cannot be blank")
        return value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    conversation_id: str
    role: str
    content: str
    status: str
    risk_level: str | None
    request_id: str | None
    trace_id: str | None
    citations: list[dict[str, Any]] | None
    created_at: datetime


class MessageTurnResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse | None
    safety: SafetyDecision
