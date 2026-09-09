"""create onboarding assessment tables

Revision ID: 0003_assessment
Revises: 0002_safety_events
Create Date: 2026-09-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

revision: str = "0003_assessment"
down_revision: str | Sequence[str] | None = "0002_safety_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assessment_templates",
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("target_population", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.String(length=64), nullable=False),
        sa.Column("published_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_templates")),
        sa.UniqueConstraint("code", "version", name=op.f("uq_assessment_templates_code_version")),
    )
    op.create_table(
        "assessment_questions",
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False),
        sa.Column("answer_type", sa.String(length=32), nullable=False),
        sa.Column("dimension", sa.String(length=64), nullable=True),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("scoring_rule_json", sa.JSON(), nullable=True),
        sa.Column("safety_rule_json", sa.JSON(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["assessment_templates.id"], name=op.f("fk_assessment_questions_template_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_questions")),
        sa.UniqueConstraint("template_id", "code", name=op.f("uq_assessment_questions_template_code")),
    )
    op.create_index(op.f("ix_assessment_questions_template_id"), "assessment_questions", ["template_id"], unique=False)
    op.create_table(
        "assessment_submissions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("highest_tier_completed", sa.String(length=32), nullable=True),
        sa.Column("coverage", sa.Float(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("submitted_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["assessment_templates.id"], name=op.f("fk_assessment_submissions_template_id")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_assessment_submissions_user_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_submissions")),
    )
    op.create_index(op.f("ix_assessment_submissions_template_id"), "assessment_submissions", ["template_id"], unique=False)
    op.create_index(op.f("ix_assessment_submissions_user_id"), "assessment_submissions", ["user_id"], unique=False)
    op.create_table(
        "assessment_answers",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("question_id", sa.String(length=36), nullable=False),
        sa.Column("answer_json", sa.JSON(), nullable=True),
        sa.Column("answer_status", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("answered_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["assessment_questions.id"], name=op.f("fk_assessment_answers_question_id")),
        sa.ForeignKeyConstraint(["submission_id"], ["assessment_submissions.id"], name=op.f("fk_assessment_answers_submission_id")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_assessment_answers_user_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_answers")),
        sa.UniqueConstraint("submission_id", "question_id", name=op.f("uq_assessment_answers_question")),
    )
    op.create_index(op.f("ix_assessment_answers_question_id"), "assessment_answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_assessment_answers_submission_id"), "assessment_answers", ["submission_id"], unique=False)
    op.create_index(op.f("ix_assessment_answers_user_id"), "assessment_answers", ["user_id"], unique=False)
    op.create_table(
        "assessment_fact_candidates",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("fact_type", sa.String(length=64), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("consent_required", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["assessment_submissions.id"], name=op.f("fk_assessment_fact_candidates_submission_id")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_assessment_fact_candidates_user_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_fact_candidates")),
    )
    op.create_index(op.f("ix_assessment_fact_candidates_submission_id"), "assessment_fact_candidates", ["submission_id"], unique=False)
    op.create_index(op.f("ix_assessment_fact_candidates_user_id"), "assessment_fact_candidates", ["user_id"], unique=False)


def downgrade() -> None:
    # MySQL foreign-key columns use their indexes to support constraints; dropping
    # each table directly removes the indexes and constraints together.
    op.drop_table("assessment_fact_candidates")
    op.drop_table("assessment_answers")
    op.drop_table("assessment_submissions")
    op.drop_table("assessment_questions")
    op.drop_table("assessment_templates")
