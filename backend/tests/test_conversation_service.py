
import pytest

from app.conversation.schemas import ConversationCreate, MessageCreate
from app.conversation.service import (
    ConversationArchivedError,
    ConversationNotFoundError,
    ConversationService,
)


class FakeRepository:
    def __init__(self) -> None:
        self.conversations = {}
        self.messages = {}
        self.safety_events = []
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

    async def list_conversations(self, user_id, include_archived):
        return [
            conversation
            for conversation in self.conversations.values()
            if conversation.user_id == user_id
            and (include_archived or conversation.status != "archived")
        ]

    async def get_conversation(self, user_id, conversation_id):
        conversation = self.conversations.get(conversation_id)
        return conversation if conversation and conversation.user_id == user_id else None

    async def get_message(self, user_id, conversation_id, message_id):
        message = self.messages.get(message_id)
        return message if message and message.user_id == user_id and message.conversation_id == conversation_id else None

    async def list_messages_by_request_id(self, user_id, conversation_id, request_id):
        return [
            message
            for message in self.messages.values()
            if message.user_id == user_id
            and message.conversation_id == conversation_id
            and message.request_id == request_id
        ]

    async def archive_conversation(self, conversation, now):
        conversation.status = "archived"
        conversation.updated_at = now
        return conversation

    async def list_messages(self, user_id, conversation_id, limit):
        return [
            message
            for message in self.messages.values()
            if message.user_id == user_id and message.conversation_id == conversation_id
        ][:limit]

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

    async def create_safety_event(
        self, user_id, conversation_id, message_id, decision, request_id, trace_id, now
    ):
        self.safety_events.append(
            {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "decision": decision,
                "request_id": request_id,
                "trace_id": trace_id,
                "created_at": now,
            }
        )

    async def touch_conversation(self, conversation, now):
        conversation.last_active_at = now
        conversation.updated_at = now

    async def update_message_status(self, message, status):
        message.status = status
        return message

    async def update_message_content(self, message, content, status=None):
        message.content = content
        if status is not None:
            message.status = status
        return message

    async def commit(self):
        return None


@pytest.fixture
def service() -> ConversationService:
    return ConversationService(FakeRepository())


@pytest.mark.asyncio
async def test_create_and_list_conversations_are_scoped_to_user(service):
    created = await service.create_conversation("user-1", ConversationCreate(title="早餐"))

    conversations = await service.list_conversations("user-1")
    other_user_conversations = await service.list_conversations("user-2")

    assert conversations[0].id == created.id
    assert other_user_conversations == []


@pytest.mark.asyncio
async def test_user_message_is_persisted_and_touches_conversation(service):
    conversation = await service.create_conversation("user-1", ConversationCreate())

    result = await service.create_user_message(
        "user-1", conversation.id, MessageCreate(content="我早餐吃什么？"), "request-1"
    )

    assert result.user_message.role == "user"
    assert result.user_message.status == "succeeded"
    assert result.user_message.conversation_id == conversation.id
    assert result.assistant_message.status == "succeeded"
    assert "Mock Agent" in result.assistant_message.content
    assert result.safety.risk_level.value == "low"


@pytest.mark.asyncio
async def test_repeated_request_id_reuses_the_existing_turn(service):
    conversation = await service.create_conversation("user-1", ConversationCreate())
    request = MessageCreate(content="我早餐吃什么？")

    first = await service.create_user_message("user-1", conversation.id, request, "request-1")
    repeated = await service.create_user_message("user-1", conversation.id, request, "request-1")

    assert repeated.user_message.id == first.user_message.id
    assert repeated.assistant_message.id == first.assistant_message.id
    assert len(service.repository.messages) == 2


@pytest.mark.asyncio
async def test_agent_failure_persists_failed_assistant_and_retry_reuses_user_message():
    class FailingAgent:
        async def generate(self, content, user_id, conversation_id):
            raise RuntimeError("mock agent unavailable")

    repository = FakeRepository()
    service = ConversationService(repository, agent=FailingAgent())
    conversation = await service.create_conversation("user-1", ConversationCreate())
    first = await service.create_user_message(
        "user-1", conversation.id, MessageCreate(content="给我一个早餐建议"), "request-failed"
    )

    assert first.user_message.status == "succeeded"
    assert first.assistant_message.status == "failed"

    class WorkingAgent:
        async def generate(self, content, user_id, conversation_id):
            return "重试后的 Mock Agent 回复"

    service.agent = WorkingAgent()
    retried = await service.retry_user_message(
        "user-1", conversation.id, first.user_message.id, "request-retry"
    )

    assert retried.user_message.id == first.user_message.id
    assert retried.assistant_message.status == "succeeded"
    assert retried.assistant_message.content == "重试后的 Mock Agent 回复"
    assert len([m for m in repository.messages.values() if m.role == "user"]) == 1


@pytest.mark.asyncio
async def test_streaming_message_persists_chunks_and_completes() -> None:
    class StreamingAgent:
        async def stream(self, content, user_id, conversation_id):
            yield "第一段"
            yield "第二段"

    repository = FakeRepository()
    service = ConversationService(repository, agent=StreamingAgent())
    conversation = await service.create_conversation("user-1", ConversationCreate())

    events = [
        event
        async for event in service.stream_user_message(
            "user-1",
            conversation.id,
            MessageCreate(content="帮我安排早餐"),
            "stream-1",
        )
    ]

    assistant = next(message for message in repository.messages.values() if message.role == "assistant")
    user_message = next(message for message in repository.messages.values() if message.role == "user")
    assert any("event: delta" in event and "第一段" in event for event in events)
    assert any("event: delta" in event and "第二段" in event for event in events)
    assert assistant.content == "第一段第二段"
    assert assistant.status == "succeeded"
    assert user_message.status == "succeeded"
    assert events[-1].startswith("event: done")


@pytest.mark.asyncio
async def test_other_user_cannot_read_conversation_or_messages(service):
    conversation = await service.create_conversation("user-1", ConversationCreate())

    with pytest.raises(ConversationNotFoundError):
        await service.get_conversation("user-2", conversation.id)

    with pytest.raises(ConversationNotFoundError):
        await service.list_messages("user-2", conversation.id, 50)


@pytest.mark.asyncio
async def test_archived_conversation_rejects_new_messages(service):
    conversation = await service.create_conversation("user-1", ConversationCreate())
    await service.archive_conversation("user-1", conversation.id)

    with pytest.raises(ConversationArchivedError):
        await service.create_user_message(
            "user-1", conversation.id, MessageCreate(content="继续"), "request-2"
        )
