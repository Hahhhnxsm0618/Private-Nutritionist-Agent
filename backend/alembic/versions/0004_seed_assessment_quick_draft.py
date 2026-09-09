"""seed a draft quick assessment template

Revision ID: 0004_assessment_quick_draft
Revises: 0003_assessment
Create Date: 2026-09-09
"""

from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0004_assessment_quick_draft"
down_revision: str | Sequence[str] | None = "0003_assessment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


TEMPLATE_ID = "00000000-0000-4000-8000-000000000401"
CREATED_AT = datetime(2026, 9, 9, 0, 0, 0)


def upgrade() -> None:
    templates = sa.table(
        "assessment_templates",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("version", sa.String),
        sa.column("status", sa.String),
        sa.column("target_population", sa.String),
        sa.column("rule_version", sa.String),
        sa.column("published_at", sa.DateTime),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    questions = sa.table(
        "assessment_questions",
        sa.column("id", sa.String),
        sa.column("template_id", sa.String),
        sa.column("code", sa.String),
        sa.column("tier", sa.String),
        sa.column("section", sa.String),
        sa.column("answer_type", sa.String),
        sa.column("dimension", sa.String),
        sa.column("options_json", sa.JSON),
        sa.column("scoring_rule_json", sa.JSON),
        sa.column("safety_rule_json", sa.JSON),
        sa.column("required", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        templates,
        [
            {
                "id": TEMPLATE_ID,
                "code": "onboarding",
                "version": "quick-draft-v1",
                "status": "draft",
                "target_population": "adult_general",
                "rule_version": "assessment-rules-v1",
                "published_at": None,
                "created_at": CREATED_AT,
                "updated_at": CREATED_AT,
            }
        ],
    )
    op.bulk_insert(
        questions,
        [
            {
                "id": "00000000-0000-4000-8000-000000000411",
                "template_id": TEMPLATE_ID,
                "code": "food-variety",
                "tier": "quick",
                "section": "diet_structure",
                "answer_type": "single",
                "dimension": "diet_structure",
                "options_json": [
                    {"value": "often", "label": "多数时候较多样"},
                    {"value": "sometimes", "label": "有时较多样"},
                    {"value": "limited", "label": "目前较单一"},
                ],
                "scoring_rule_json": {"score_by_option": {"often": 4, "sometimes": 2, "limited": 0}},
                "safety_rule_json": None,
                "required": True,
                "sort_order": 1,
                "created_at": CREATED_AT,
            },
            {
                "id": "00000000-0000-4000-8000-000000000412",
                "template_id": TEMPLATE_ID,
                "code": "meal-regularity",
                "tier": "quick",
                "section": "diet_behavior",
                "answer_type": "single",
                "dimension": "diet_behavior",
                "options_json": [
                    {"value": "regular", "label": "大多数时候规律"},
                    {"value": "sometimes", "label": "有时不规律"},
                    {"value": "often_skip", "label": "经常跳过"},
                ],
                "scoring_rule_json": {"score_by_option": {"regular": 4, "sometimes": 2, "often_skip": 0}},
                "safety_rule_json": None,
                "required": True,
                "sort_order": 2,
                "created_at": CREATED_AT,
            },
            {
                "id": "00000000-0000-4000-8000-000000000413",
                "template_id": TEMPLATE_ID,
                "code": "activity-routine",
                "tier": "quick",
                "section": "activity_routine",
                "answer_type": "single",
                "dimension": "activity_routine",
                "options_json": [
                    {"value": "regular", "label": "目前较规律"},
                    {"value": "sometimes", "label": "有时能做到"},
                    {"value": "rare", "label": "目前较少"},
                ],
                "scoring_rule_json": {"score_by_option": {"regular": 4, "sometimes": 2, "rare": 0}},
                "safety_rule_json": None,
                "required": True,
                "sort_order": 3,
                "created_at": CREATED_AT,
            },
            {
                "id": "00000000-0000-4000-8000-000000000414",
                "template_id": TEMPLATE_ID,
                "code": "goal-readiness",
                "tier": "quick",
                "section": "goal_feasibility",
                "answer_type": "single",
                "dimension": "goal_feasibility",
                "options_json": [
                    {"value": "ready", "label": "已有一个想先尝试的小改变"},
                    {"value": "exploring", "label": "还在了解适合自己的方式"},
                    {"value": "not_ready", "label": "暂时不想设定改变"},
                ],
                "scoring_rule_json": {"score_by_option": {"ready": 4, "exploring": 2, "not_ready": 0}},
                "safety_rule_json": None,
                "required": True,
                "sort_order": 4,
                "created_at": CREATED_AT,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM assessment_questions WHERE template_id = :template_id"
        ).bindparams(template_id=TEMPLATE_ID)
    )
    op.execute(
        sa.text(
            "DELETE FROM assessment_templates WHERE id = :template_id"
        ).bindparams(template_id=TEMPLATE_ID)
    )
