"""前置和后置安全规则的结构化审计事件。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation, Message
    from app.models.user import User


class SafetyEvent(UUIDPrimaryKeyMixin, Base):
    """保存规则判定结果，不保存用户原始消息或完整健康文本。

    事件同时关联用户、会话和触发判定的用户消息，便于按用户审计及排查一次
    安全拦截的来源。规则结果拆成固定字段，后续可以按风险级别和规则版本统计。
    """

    __tablename__ = "safety_events"
    __table_args__ = (
        Index("ix_safety_events_conversation_created", "conversation_id", "created_at"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_category: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped["User"] = relationship()
    conversation: Mapped["Conversation"] = relationship()
    message: Mapped["Message"] = relationship()
