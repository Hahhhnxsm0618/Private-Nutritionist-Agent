"""敏感操作和关键业务动作的审计记录。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """记录谁对哪类资源执行了什么动作及其结果。

    审计日志用于回答“谁在什么时候对什么资源做了什么操作”。它不是普通业务
    日志，不能只记录一段自由文本，否则后续很难查询和审计。
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36))
    result: Mapped[str] = mapped_column(String(32), nullable=False)
    # actor_user_id 表示实际执行操作的人，user_id 表示被操作数据所属用户。
    # 两者在管理员代用户操作时可能不同。
    # 只存脱敏后的补充信息；不要把完整健康文本直接写入审计日志。
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped["User"] = relationship(back_populates="audit_logs")
