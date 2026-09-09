"""对话会话和消息的用户隔离业务规则。"""

from datetime import UTC, datetime
from typing import Protocol

from app.conversation.schemas import ConversationCreate, MessageCreate, MessageTurnResponse
from app.safety.rules import SafetyRuleEngine


class ConversationNotFoundError(Exception):
    pass


class ConversationArchivedError(Exception):
    pass


class ConversationRepository(Protocol):
    async def create_conversation(self, user_id: str, title: str | None, now: datetime): ...
    async def list_conversations(self, user_id: str, include_archived: bool): ...
    async def get_conversation(self, user_id: str, conversation_id: str): ...
    async def archive_conversation(self, conversation, now: datetime): ...
    async def list_messages(self, user_id: str, conversation_id: str, limit: int): ...
    async def create_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        status: str,
        request_id: str | None,
        now: datetime,
    ): ...
    async def create_safety_event(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        decision,
        request_id: str | None,
        trace_id: str | None,
        now: datetime,
    ): ...
    async def touch_conversation(self, conversation, now: datetime) -> None: ...
    async def commit(self) -> None: ...


class ConversationService:
    def __init__(
        self,
        repository: ConversationRepository,
        safety_engine: SafetyRuleEngine | None = None,
    ) -> None:
        self.repository = repository
        self.safety_engine = safety_engine or SafetyRuleEngine()

    async def create_conversation(self, user_id: str, request: ConversationCreate):
        conversation = await self.repository.create_conversation(
            user_id, request.title, datetime.now(UTC)
        )
        await self.repository.commit()
        return conversation

    async def list_conversations(self, user_id: str, include_archived: bool = False):
        return await self.repository.list_conversations(user_id, include_archived)

    async def get_conversation(self, user_id: str, conversation_id: str):
        conversation = await self.repository.get_conversation(user_id, conversation_id)
        if not conversation:
            raise ConversationNotFoundError
        return conversation

    async def archive_conversation(self, user_id: str, conversation_id: str):
        conversation = await self.get_conversation(user_id, conversation_id)
        archived = await self.repository.archive_conversation(conversation, datetime.now(UTC))
        await self.repository.commit()
        return archived

    async def list_messages(self, user_id: str, conversation_id: str, limit: int):
        await self.get_conversation(user_id, conversation_id)
        return await self.repository.list_messages(user_id, conversation_id, limit)

    async def create_user_message(
        self,
        user_id: str,
        conversation_id: str,
        request: MessageCreate,
        request_id: str | None,
    ) -> MessageTurnResponse:
        conversation = await self.get_conversation(user_id, conversation_id)
        if conversation.status == "archived":
            raise ConversationArchivedError
        now = datetime.now(UTC)
        safety = self.safety_engine.evaluate(request.content)
        message_status = "pending" if safety.fixed_response is None else "succeeded"
        message = await self.repository.create_message(
            user_id,
            conversation_id,
            "user",
            request.content,
            message_status,
            request_id,
            now,
        )
        message.risk_level = safety.risk_level.value
        assistant_message = None
        if safety.fixed_response:
            assistant_message = await self.repository.create_message(
                user_id,
                conversation_id,
                "assistant",
                safety.fixed_response,
                "succeeded",
                request_id,
                now,
            )
            assistant_message.risk_level = safety.risk_level.value
        await self.repository.create_safety_event(
            user_id,
            conversation_id,
            message.id,
            safety,
            request_id,
            None,
            now,
        )
        await self.repository.touch_conversation(conversation, now)
        await self.repository.commit()
        return MessageTurnResponse(
            user_message=message,
            assistant_message=assistant_message,
            safety=safety,
        )
