import pytest

from app.conversation.schemas import ConversationCreate, MessageCreate
from app.conversation.service import ConversationService
from app.safety.rules import RiskLevel


class FakeRepository:
    def __init__(self) -> None:
        self.conversations = {}
        self.messages = {}
        self.events = []
        self.counter = 0

    async def create_conversation(self, user_id, title, now):
        self.counter += 1
        conversation = type("Conversation", (), {
            "id": f"conversation-{self.counter}",
            "user_id": user_id,
            "title": title,
            "status": "active",
            "last_active_at": now,
            "created_at": now,
            "updated_at": now,
        })()
        self.conversations[conversation.id] = conversation
        return conversation

    async def get_conversation(self, user_id, conversation_id):
        conversation = self.conversations.get(conversation_id)
        return conversation if conversation and conversation.user_id == user_id else None

    async def create_message(
        self, user_id, conversation_id, role, content, status, request_id, now
    ):
        self.counter += 1
        message = type("Message", (), {
            "id": f"message-{self.counter}",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "status": status,
            "risk_level": None,
            "request_id": request_id,
            "trace_id": None,
            "citations": None,
            "created_at": now,
        })()
        self.messages[message.id] = message
        return message

    async def touch_conversation(self, conversation, now):
        conversation.last_active_at = now

    async def create_safety_event(
        self, user_id, conversation_id, message_id, decision, request_id, trace_id, now
    ):
        self.events.append({
            "user_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "risk_level": decision.risk_level.value,
            "trigger_category": decision.trigger_category,
            "request_id": request_id,
            "trace_id": trace_id,
            "created_at": now,
        })

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_high_risk_message_persists_fixed_safe_reply_and_event() -> None:
    repository = FakeRepository()
    service = ConversationService(repository)
    conversation = await service.create_conversation("user-1", ConversationCreate())

    result = await service.create_user_message(
        "user-1",
        conversation.id,
        MessageCreate(content="我现在胸痛并且呼吸困难怎么办？"),
        "request-high",
    )

    assert result.safety.risk_level is RiskLevel.HIGH
    assert result.user_message.status == "succeeded"
    assert result.assistant_message.role == "assistant"
    assert result.assistant_message.status == "succeeded"
    assert "就医" in result.assistant_message.content
    assert repository.events[0]["message_id"] == result.user_message.id


@pytest.mark.asyncio
async def test_low_risk_message_remains_pending_without_assistant_reply() -> None:
    repository = FakeRepository()
    service = ConversationService(repository)
    conversation = await service.create_conversation("user-1", ConversationCreate())

    result = await service.create_user_message(
        "user-1",
        conversation.id,
        MessageCreate(content="番茄和鸡蛋可以一起吃吗？"),
        "request-low",
    )

    assert result.safety.risk_level is RiskLevel.LOW
    assert result.user_message.status == "pending"
    assert result.assistant_message is None
    assert repository.events[0]["risk_level"] == "low"
