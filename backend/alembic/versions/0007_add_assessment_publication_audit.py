"""record the administrator who publishes an assessment template

Revision ID: 0007_publish_audit
Revises: 0006_assessment_reviews
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_publish_audit"
down_revision: str | Sequence[str] | None = "0006_assessment_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessment_templates",
        sa.Column("published_by_user_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_assessment_templates_published_by_user_id"),
        "assessment_templates",
        ["published_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_assessment_templates_published_by_user_id_users"),
        "assessment_templates",
        "users",
        ["published_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_assessment_templates_published_by_user_id_users"),
        "assessment_templates",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_templates_published_by_user_id"),
        table_name="assessment_templates",
    )
    op.drop_column("assessment_templates", "published_by_user_id")
