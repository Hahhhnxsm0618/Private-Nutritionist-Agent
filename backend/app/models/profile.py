"""用户健康档案、授权记录和可追溯的健康事实。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class HealthProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """用户的结构化档案摘要；一个用户最多对应一份档案。

    ``user_id`` 的 unique=True 同时表达了“一人一档”的业务规则和数据库约束。
    ``profile_data`` 暂时使用 JSON，是因为 V0 的档案字段还会演进；稳定字段未来
    可以再拆成独立列，以便检索和校验。
    """

    __tablename__ = "health_profiles"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    # JSON 列保存字典结构，例如饮食偏好、活动水平等可扩展资料。
    profile_data: Mapped[dict | None] = mapped_column(JSON)
    # 关闭后，业务层不得读取或新增长期健康事实；这个字段本身只是开关，
    # 具体的读取限制仍需要在服务层实现。
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="health_profile")


class Consent(UUIDPrimaryKeyMixin, Base):
    """记录用户对某类数据用途和具体政策版本的授权状态。

    同一个用户可以针对不同 consent_type 或不同 policy_version 留下多条记录，
    因此用三列联合唯一约束，而不是简单地限制 user_id 唯一。
    """

    __tablename__ = "consents"
    __table_args__ = (UniqueConstraint("user_id", "consent_type", "policy_version"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped["User"] = relationship(back_populates="consents")


class HealthFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """带来源、状态和授权关系的单条健康事实。

    例如“对花生过敏”可以作为一条事实保存。它不仅保存内容，还保存来源和确认
    状态，便于后续判断这条信息是否可以参与个性化推荐。
    """

    __tablename__ = "health_facts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # value 保存结构化字典，而不是把所有信息拼成一段不可解析的文本。
    # source_type/source_message_id 用来追溯事实来自用户档案、对话消息还是其他来源。
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(String(36))
    # pending 表示尚未被用户确认，confirmed 表示用户确认，corrected 表示用户修正。
    # 业务层应根据状态决定是否允许它参与方案生成，不能把所有记录一律当事实。
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    consent_id: Mapped[str | None] = mapped_column(ForeignKey("consents.id"))
    valid_until: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))

    user: Mapped["User"] = relationship(back_populates="health_facts")
    consent: Mapped["Consent | None"] = relationship()
