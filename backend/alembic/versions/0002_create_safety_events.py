"""create safety events

Revision ID: 0002_safety_events
Revises: 0001_foundation
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0002_safety_events"
down_revision: str | Sequence[str] | None = "0001_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "safety_events",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("trigger_category", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], name=op.f("fk_safety_events_conversation_id")
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], name=op.f("fk_safety_events_message_id")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_safety_events_user_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_safety_events")),
    )
    op.create_index(op.f("ix_safety_events_user_id"), "safety_events", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_safety_events_conversation_id"), "safety_events", ["conversation_id"], unique=False
    )
    op.create_index(
        op.f("ix_safety_events_message_id"), "safety_events", ["message_id"], unique=False
    )
    op.create_index(op.f("ix_safety_events_request_id"), "safety_events", ["request_id"], unique=False)
    op.create_index(op.f("ix_safety_events_trace_id"), "safety_events", ["trace_id"], unique=False)
    op.create_index(
        "ix_safety_events_conversation_created",
        "safety_events",
        ["conversation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # MySQL 使用外键列上的索引支撑约束，不能先单独删除这些索引；删除表时
    # MySQL 会同时移除本迁移创建的外键和索引。
    op.drop_table("safety_events")
