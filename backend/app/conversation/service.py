"""对话会话和消息的用户隔离业务规则。"""

import json
from datetime import UTC, datetime
from typing import Protocol

from app.conversation.schemas import ConversationCreate, MessageCreate, MessageTurnResponse
from app.safety.rules import SafetyRuleEngine


class MockAgent:
    async def generate(self, content: str, user_id: str, conversation_id: str) -> str:
        return f"这是 Mock Agent 对“{content}”的日常饮食建议。"

    async def stream(self, content: str, user_id: str, conversation_id: str):
        yield await self.generate(content, user_id, conversation_id)


class ConversationNotFoundError(Exception):
    pass


class ConversationArchivedError(Exception):
    pass


class ConversationRepository(Protocol):
    async def create_conversation(self, user_id: str, title: str | None, now: datetime): ...
    async def list_conversations(self, user_id: str, include_archived: bool): ...
    async def get_conversation(self, user_id: str, conversation_id: str): ...
    async def get_message(self, user_id: str, conversation_id: str, message_id: str): ...
    async def list_messages_by_request_id(self, user_id: str, conversation_id: str, request_id: str): ...
    async def update_message_content(self, message, content: str, status: str | None = None): ...
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
        agent=None,
    ) -> None:
        self.repository = repository
        self.safety_engine = safety_engine or SafetyRuleEngine()
        self.agent = agent or MockAgent()

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
        existing = await self.repository.list_messages_by_request_id(
            user_id, conversation_id, request_id
        )
        if existing:
            user_message = next(message for message in existing if message.role == "user")
            assistant_message = next(
                (message for message in existing if message.role == "assistant"), None
            )
            return MessageTurnResponse(
                user_message=user_message,
                assistant_message=assistant_message,
                safety=self.safety_engine.evaluate(user_message.content),
            )
        now = datetime.now(UTC)
        safety = self.safety_engine.evaluate(request.content)
        message = await self.repository.create_message(
            user_id,
            conversation_id,
            "user",
            request.content,
            "succeeded",
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
        else:
            try:
                content = await self.agent.generate(request.content, user_id, conversation_id)
                assistant_message = await self.repository.create_message(
                    user_id, conversation_id, "assistant", content, "succeeded", request_id, now
                )
                assistant_message.risk_level = safety.risk_level.value
            except RuntimeError:
                assistant_message = await self.repository.create_message(
                    user_id,
                    conversation_id,
                    "assistant",
                    "本次回答暂时无法完成，请稍后重试。",
                    "failed",
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

    async def retry_user_message(
        self, user_id: str, conversation_id: str, message_id: str, request_id: str
    ) -> MessageTurnResponse:
        conversation = await self.get_conversation(user_id, conversation_id)
        if conversation.status == "archived":
            raise ConversationArchivedError
        user_message = await self.repository.get_message(user_id, conversation_id, message_id)
        if user_message is None or user_message.role != "user":
            raise ConversationNotFoundError
        existing = await self.repository.list_messages_by_request_id(
            user_id, conversation_id, request_id
        )
        if existing:
            assistant_message = next(
                (message for message in existing if message.role == "assistant"), None
            )
            return MessageTurnResponse(
                user_message=user_message,
                assistant_message=assistant_message,
                safety=self.safety_engine.evaluate(user_message.content),
            )
        safety = self.safety_engine.evaluate(user_message.content)
        now = datetime.now(UTC)
        if safety.fixed_response:
            content, message_status = safety.fixed_response, "succeeded"
        else:
            try:
                content, message_status = await self.agent.generate(
                    user_message.content, user_id, conversation_id
                ), "succeeded"
            except RuntimeError:
                content, message_status = "本次回答暂时无法完成，请稍后重试。", "failed"
        assistant_message = await self.repository.create_message(
            user_id, conversation_id, "assistant", content, message_status, request_id, now
        )
        await self.repository.commit()
        return MessageTurnResponse(
            user_message=user_message,
            assistant_message=assistant_message,
            safety=safety,
        )

    async def stream_user_message(self, user_id: str, conversation_id: str, request: MessageCreate, request_id: str):
        conversation = await self.get_conversation(user_id, conversation_id)
        if conversation.status == "archived":
            raise ConversationArchivedError
        existing = await self.repository.list_messages_by_request_id(
            user_id, conversation_id, request_id
        )
        if existing:
            yield self._sse("replay", {"message_ids": [message.id for message in existing]})
            yield self._sse("done", {"replayed": True})
            return

        now = datetime.now(UTC)
        safety = self.safety_engine.evaluate(request.content)
        user_status = "succeeded" if safety.fixed_response else "streaming"
        user_message = await self.repository.create_message(
            user_id, conversation_id, "user", request.content, user_status, request_id, now
        )
        user_message.risk_level = safety.risk_level.value
        assistant_content = safety.fixed_response or ""
        assistant_status = "succeeded" if safety.fixed_response else "streaming"
        assistant_message = await self.repository.create_message(
            user_id,
            conversation_id,
            "assistant",
            assistant_content,
            assistant_status,
            request_id,
            now,
        )
        assistant_message.risk_level = safety.risk_level.value
        await self.repository.create_safety_event(
            user_id, conversation_id, user_message.id, safety, request_id, None, now
        )
        yield self._sse(
            "start",
            {"user_message_id": user_message.id, "assistant_message_id": assistant_message.id},
        )

        if safety.fixed_response:
            await self.repository.touch_conversation(conversation, now)
            await self.repository.commit()
            yield self._sse("delta", {"message_id": assistant_message.id, "delta": assistant_content})
            yield self._sse("done", {"message_id": assistant_message.id, "status": "succeeded"})
            return

        accumulated = ""
        try:
            async for chunk in self.agent.stream(request.content, user_id, conversation_id):
                accumulated += chunk
                await self.repository.update_message_content(
                    assistant_message, accumulated, "streaming"
                )
                yield self._sse("delta", {"message_id": assistant_message.id, "delta": chunk})
            await self.repository.update_message_content(
                assistant_message, accumulated, "succeeded"
            )
            await self.repository.update_message_status(user_message, "succeeded")
            await self.repository.touch_conversation(conversation, datetime.now(UTC))
            await self.repository.commit()
            yield self._sse("done", {"message_id": assistant_message.id, "status": "succeeded"})
        except RuntimeError:
            await self.repository.update_message_content(
                assistant_message, "本次回答暂时无法完成，请稍后重试。", "failed"
            )
            await self.repository.update_message_status(user_message, "succeeded")
            await self.repository.commit()
            yield self._sse(
                "error",
                {"message_id": assistant_message.id, "code": "MODEL_UNAVAILABLE", "retryable": True},
            )

    @staticmethod
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
