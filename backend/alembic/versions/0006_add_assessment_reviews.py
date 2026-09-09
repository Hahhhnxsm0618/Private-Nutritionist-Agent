"""add professional assessment reviews

Revision ID: 0006_assessment_reviews
Revises: 0005_candidate_fact_link
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0006_assessment_reviews"
down_revision: str | Sequence[str] | None = "0005_candidate_fact_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_reviews",
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("reviewed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_id"], ["assessment_templates.id"],
            name=op.f("fk_assessment_reviews_template_id_assessment_templates"),
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"], ["users.id"],
            name=op.f("fk_assessment_reviews_reviewer_user_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_reviews")),
    )
    op.create_index(
        op.f("ix_assessment_reviews_template_id"),
        "assessment_reviews",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_reviews_reviewer_user_id"),
        "assessment_reviews",
        ["reviewer_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("assessment_reviews")
