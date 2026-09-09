"""首次登录问卷的请求和响应模型。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.assessment.scoring import AssessmentScoreResult

AssessmentTier = Literal["quick", "standard", "full"]
AnswerStatus = Literal["answered", "skipped", "not_applicable"]


class AssessmentSubmissionCreate(BaseModel):
    tier: AssessmentTier = "quick"
    template_code: str = Field(default="onboarding", min_length=1, max_length=64)


class AssessmentAnswerUpsert(BaseModel):
    value: Any | None = None
    status: AnswerStatus = "answered"


class AssessmentQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    tier: str
    section: str
    answer_type: str
    dimension: str | None
    options_json: list | dict
    required: bool
    sort_order: int


class AssessmentAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    submission_id: str
    question_id: str
    answer_json: Any | None
    answer_status: str
    score: int | None
    answered_at: datetime | None
    created_at: datetime


class AssessmentSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    template_id: str
    status: str
    highest_tier_completed: str | None
    coverage: float | None
    baseline_score: float | None
    result_json: dict | None
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssessmentFactCandidateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    submission_id: str
    fact_type: str
    value_json: Any
    sensitivity: str
    status: str
    consent_required: bool


class AssessmentCompleteResponse(BaseModel):
    submission: AssessmentSubmissionResponse
    result: AssessmentScoreResult
    fact_candidates: list[AssessmentFactCandidateResponse]


class AssessmentOnboardingResponse(BaseModel):
    has_completed_quick: bool
    active_submission_id: str | None
    available_tiers: list[AssessmentTier]


class AssessmentTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    version: str
    status: str
    target_population: str
    rule_version: str
    published_at: datetime | None
    published_by_user_id: str | None
    created_at: datetime
    updated_at: datetime


class AssessmentReviewRequest(BaseModel):
    status: Literal["approved", "rejected"]


class AssessmentReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_id: str
    reviewer_user_id: str
    status: str
    rule_version: str
    reviewed_at: datetime
    created_at: datetime
