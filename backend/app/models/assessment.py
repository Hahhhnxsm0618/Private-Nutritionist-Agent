"""首次登录问卷、答案和候选画像事实。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.mysql import DATETIME
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class AssessmentTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """版本化问卷模板；历史版本发布后不能原地改写。"""

    __tablename__ = "assessment_templates"
    __table_args__ = (UniqueConstraint("code", "version", name="uq_assessment_templates_code_version"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    target_population: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    published_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    questions: Mapped[list["AssessmentQuestion"]] = relationship(back_populates="template")
    submissions: Mapped[list["AssessmentSubmission"]] = relationship(back_populates="template")


class AssessmentQuestion(UUIDPrimaryKeyMixin, Base):
    """模板中的一题及其结构化选项、计分和安全规则。"""

    __tablename__ = "assessment_questions"
    __table_args__ = (UniqueConstraint("template_id", "code", name="uq_assessment_questions_template_code"),)

    template_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_templates.id"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    tier: Mapped[str] = mapped_column(String(32), nullable=False)
    section: Mapped[str] = mapped_column(String(64), nullable=False)
    answer_type: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension: Mapped[str | None] = mapped_column(String(64))
    options_json: Mapped[list | dict] = mapped_column(JSON, nullable=False)
    scoring_rule_json: Mapped[dict | None] = mapped_column(JSON)
    safety_rule_json: Mapped[dict | None] = mapped_column(JSON)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    template: Mapped[AssessmentTemplate] = relationship(back_populates="questions")


class AssessmentSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """用户对某个问卷版本的一次可续填提交。"""

    __tablename__ = "assessment_submissions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_templates.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    highest_tier_completed: Mapped[str | None] = mapped_column(String(32))
    coverage: Mapped[float | None] = mapped_column(Float)
    baseline_score: Mapped[float | None] = mapped_column(Float)
    result_json: Mapped[dict | None] = mapped_column(JSON)
    submitted_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))

    user: Mapped["User"] = relationship()
    template: Mapped[AssessmentTemplate] = relationship(back_populates="submissions")
    answers: Mapped[list["AssessmentAnswer"]] = relationship(back_populates="submission")
    fact_candidates: Mapped[list["AssessmentFactCandidate"]] = relationship(
        back_populates="submission"
    )


class AssessmentAnswer(UUIDPrimaryKeyMixin, Base):
    """单题答案；答案与长期健康事实严格分开。"""

    __tablename__ = "assessment_answers"
    __table_args__ = (UniqueConstraint("submission_id", "question_id", name="uq_assessment_answers_question"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_submissions.id"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_questions.id"), nullable=False, index=True
    )
    answer_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSON, nullable=True
    )
    answer_status: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    answered_at: Mapped[datetime | None] = mapped_column(DATETIME(fsp=6))
    created_at: Mapped[datetime] = mapped_column(DATETIME(fsp=6), nullable=False)

    submission: Mapped[AssessmentSubmission] = relationship(back_populates="answers")
    question: Mapped[AssessmentQuestion] = relationship()


class AssessmentFactCandidate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """问卷产生的待确认画像事实，不等同于 confirmed health_fact。"""

    __tablename__ = "assessment_fact_candidates"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    submission_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_submissions.id"), nullable=False, index=True
    )
    fact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSON, nullable=False
    )
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health_fact_id: Mapped[str | None] = mapped_column(ForeignKey("health_facts.id"), index=True)

    submission: Mapped[AssessmentSubmission] = relationship(back_populates="fact_candidates")
