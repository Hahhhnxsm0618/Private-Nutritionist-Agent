"""对话会话和消息的 SQLAlchemy 数据访问。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.safety import SafetyEvent


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_conversation(
        self, user_id: str, title: str | None, now: datetime
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            title=title,
            status="active",
            last_active_at=now,
        )
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def list_conversations(
        self, user_id: str, include_archived: bool
    ) -> list[Conversation]:
        query = select(Conversation).where(Conversation.user_id == user_id)
        if not include_archived:
            query = query.where(Conversation.status != "archived")
        query = query.order_by(Conversation.last_active_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_conversation(
        self, user_id: str, conversation_id: str
    ) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def archive_conversation(self, conversation: Conversation, now: datetime) -> Conversation:
        conversation.status = "archived"
        conversation.updated_at = now
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def list_messages(
        self, user_id: str, conversation_id: str, limit: int
    ) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.user_id == user_id, Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_message(
        self,
        user_id: str,
        conversation_id: str,
        role: str,
        content: str,
        status: str,
        request_id: str | None,
        now: datetime,
    ) -> Message:
        message = Message(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            status=status,
            request_id=request_id,
            created_at=now,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def create_safety_event(
        self,
        user_id: str,
        conversation_id: str,
        message_id: str,
        decision,
        request_id: str | None,
        trace_id: str | None,
        now: datetime,
    ) -> SafetyEvent:
        event = SafetyEvent(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
            risk_level=decision.risk_level.value,
            trigger_category=decision.trigger_category,
            rule_version=decision.rule_version,
            action=decision.action,
            result="blocked" if decision.fixed_response else "allowed",
            request_id=request_id,
            trace_id=trace_id,
            created_at=now,
        )
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def touch_conversation(self, conversation: Conversation, now: datetime) -> None:
        conversation.last_active_at = now
        conversation.updated_at = now
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
