"""用户身份、登录会话和幂等请求记录。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.audit import AuditLog
    from app.models.conversation import Conversation
    from app.models.profile import Consent, HealthFact, HealthProfile


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """系统用户及其与健康档案、对话、审计记录的关联入口。

    一个 User 是很多业务数据的“所有者”。其他表通过 user_id 指向这里，业务
    查询时必须结合当前登录用户做归属校验，不能只相信前端传来的 id。
    """

    __tablename__ = "users"

    # Mapped[str] 表示这个 ORM 字段在 Python 中按 str 使用。
    # String(320) 是数据库列的最大长度，unique=True 防止两个用户注册同一邮箱，
    # index=True 创建索引以加快登录时按邮箱查找，nullable=False 表示必填。
    # 邮箱既是登录标识，也是数据库层面的唯一约束；密码只保存哈希值。
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # role 表示权限角色，status 表示账号状态。default 是新对象未传值时的默认值；
    # 这里先使用字符串，后续可在业务层统一收敛为枚举值。
    role: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    # relationship 只描述 ORM 导航关系，方便通过 user.health_profile 或
    # user.conversations 访问关联对象。真正的外键约束由各关联表的 user_id 保证。
    # list 表示一对多，单个对象或 None 表示一对一/可选关系。
    auth_sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")
    health_profile: Mapped["HealthProfile | None"] = relationship(
        back_populates="user", uselist=False
    )
    health_facts: Mapped[list["HealthFact"]] = relationship(back_populates="user")
    consents: Mapped[list["Consent"]] = relationship(back_populates="user")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")
    idempotency_keys: Mapped[list["IdempotencyKey"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")


class AuthSession(UUIDPrimaryKeyMixin, Base):
    """登录会话记录；数据库中不保存可直接使用的原始令牌。

    用户登录成功后可以创建会话。服务端只保存 token_hash，即使数据库内容泄露，
    也不能直接把这一列当作登录令牌使用。revoked_at 用于主动注销或强制失效。
    """

    __tablename__ = "auth_sessions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped[User] = relationship(back_populates="auth_sessions")


class IdempotencyKey(UUIDPrimaryKeyMixin, Base):
    """记录带幂等键的请求，避免网络重试重复创建业务结果。

    移动端或浏览器可能因为网络超时重复发送同一个请求。user_id、route、key
    的联合唯一约束确保同一用户对同一路由使用同一个幂等键时只能有一条记录，
    response_status 和 response_body 则可用于重放第一次请求的结果。
    """

    __tablename__ = "idempotency_keys"
    __table_args__ = (UniqueConstraint("user_id", "route", "key"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    route: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    response_status: Mapped[int | None] = mapped_column()
    response_body: Mapped[dict | None] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    user: Mapped[User] = relationship(back_populates="idempotency_keys")
