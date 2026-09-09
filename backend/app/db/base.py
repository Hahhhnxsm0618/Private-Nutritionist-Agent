"""SQLAlchemy 模型共享的基类、命名规则和通用字段。

SQLAlchemy ORM 的作用是把 Python 类映射成数据库表：类通常对应表，类属性
对应列，``relationship`` 对应表之间的导航关系。这里集中放共享定义，模型文件
只需要继承这些基类即可保持一致。
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import MetaData, String, func
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# 固定约束和索引命名，确保 Alembic 生成的迁移在不同环境中保持稳定。
# 例如一个 users.id 的外键会按 fk_表名_字段名_被引用表名 的规则命名，后续
# 查数据库报错或编写迁移时更容易定位具体约束。
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有 ORM 模型的根基类。

    继承 Base 的模型会自动注册到 ``Base.metadata``。Alembic 正是读取这个
    metadata 来知道项目中有哪些表和字段。
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """为模型提供应用层生成的字符串 UUID 主键。

    Mixin 不是一张表，而是一段可复用的字段定义。继承它的模型都会得到 id 列。
    ``default`` 表示创建 Python 对象时如果没有手动传 id，就调用 uuid4 生成一个
    新 UUID；数据库中保存的是长度为 36 的字符串。
    """

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), nullable=False
    )


class TimestampMixin:
    """为需要追踪生命周期的模型提供创建和更新时间。

    ``server_default`` 让数据库在插入时填写创建时间，``onupdate`` 让 SQLAlchemy
    在更新记录时写入更新时间。这样业务代码不需要每次手动维护这两个字段。
    """

    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=6), server_default=func.now(), onupdate=func.now(), nullable=False
    )
