"""link confirmed assessment candidates to health facts

Revision ID: 0005_candidate_fact_link
Revises: 0004_assessment_quick_draft
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_candidate_fact_link"
down_revision: str | Sequence[str] | None = "0004_assessment_quick_draft"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "assessment_fact_candidates",
        sa.Column("health_fact_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_assessment_fact_candidates_health_fact_id"),
        "assessment_fact_candidates",
        ["health_fact_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_assessment_fact_candidates_health_fact_id"),
        "assessment_fact_candidates",
        "health_facts",
        ["health_fact_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_assessment_fact_candidates_health_fact_id"),
        "assessment_fact_candidates",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_assessment_fact_candidates_health_fact_id"),
        table_name="assessment_fact_candidates",
    )
    op.drop_column("assessment_fact_candidates", "health_fact_id")
