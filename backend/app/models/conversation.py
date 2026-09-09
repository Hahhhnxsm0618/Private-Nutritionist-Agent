"""对话、消息及消息检索所需的追踪信息。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """用户的一条对话线程。

    Conversation 保存会话级信息，例如标题、状态和最后活跃时间；具体的用户问题
    与助手回答放在 Message 表中，通过 conversation_id 关联回来。
    """

    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")


class Message(UUIDPrimaryKeyMixin, Base):
    """对话中的单条消息，兼容失败状态、风险标记和知识库引用。

    user_id 与 conversation_id 同时保存，看起来有重复，但这样可以直接按用户
    隔离查询，也可以在业务层校验“消息所属用户”和“会话所属用户”是否一致。
    """

    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # role 区分 user、assistant 等消息发送方；content 保存消息正文。
    # status 用于区分生成中、成功、失败等状态，避免把失败消息误当成答案。
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(64), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), index=True)
    # risk_level 保存前置风险判断结果；citations 保存知识库引用信息。
    # 引用以 JSON 保存，便于保留文档版本、标题和原文片段等扩展信息。
    citations: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
