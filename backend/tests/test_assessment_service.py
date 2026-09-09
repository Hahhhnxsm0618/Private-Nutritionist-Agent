from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.assessment.schemas import AssessmentAnswerUpsert, AssessmentSubmissionCreate
from app.assessment.service import (
    AssessmentNotFoundError,
    AssessmentService,
    AssessmentValidationError,
)


class FakeAssessmentRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.template = SimpleNamespace(
            id="template-1",
            code="onboarding",
            version="v1",
            status="published",
            rule_version="assessment-rules-v1",
        )
        self.questions = [
            SimpleNamespace(
                id="question-1",
                template_id="template-1",
                code="breakfast",
                tier="quick",
                section="routine",
                answer_type="single",
                dimension="diet_behavior",
                options_json=[{"value": "regular", "label": "规律"}],
                scoring_rule_json={"score_by_option": {"regular": 4}},
                safety_rule_json=None,
                required=True,
                sort_order=1,
            ),
            SimpleNamespace(
                id="question-2",
                template_id="template-1",
                code="goal",
                tier="quick",
                section="goal",
                answer_type="single",
                dimension="goal_feasibility",
                options_json=[{"value": "ready", "label": "准备好了"}],
                scoring_rule_json={"score_by_option": {"ready": 4}},
                safety_rule_json=None,
                required=True,
                sort_order=2,
            ),
        ]
        self.submissions = {}
        self.answers = {}
        self.candidates = []
        self.now = now
        self.counter = 0

    async def get_published_template(self, code):
        return self.template if code == self.template.code else None

    async def get_submission(self, user_id, submission_id):
        submission = self.submissions.get(submission_id)
        return submission if submission and submission.user_id == user_id else None

    async def get_template_for_submission(self, submission):
        return self.template

    async def get_draft_submission(self, user_id, template_id):
        return next(
            (
                submission
                for submission in self.submissions.values()
                if submission.user_id == user_id
                and submission.template_id == template_id
                and submission.status == "draft"
            ),
            None,
        )

    async def has_completed_quick(self, user_id, template_id):
        return any(
            submission.user_id == user_id
            and submission.template_id == template_id
            and submission.status == "completed_quick"
            for submission in self.submissions.values()
        )

    async def create_submission(self, user_id, template_id, now):
        self.counter += 1
        submission = SimpleNamespace(
            id=f"submission-{self.counter}",
            user_id=user_id,
            template_id=template_id,
            status="draft",
            highest_tier_completed=None,
            coverage=None,
            baseline_score=None,
            result_json=None,
            submitted_at=None,
            created_at=now,
            updated_at=now,
        )
        self.submissions[submission.id] = submission
        return submission

    async def list_questions(self, template_id, tiers):
        return [question for question in self.questions if question.template_id == template_id and question.tier in tiers]

    async def list_answers(self, user_id, submission_id):
        return [
            answer
            for answer in self.answers.values()
            if answer.user_id == user_id and answer.submission_id == submission_id
        ]

    async def get_question(self, template_id, question_code):
        return next(
            (
                question
                for question in self.questions
                if question.template_id == template_id and question.code == question_code
            ),
            None,
        )

    async def upsert_answer(self, user_id, submission_id, question, answer, now):
        key = (submission_id, question.id)
        item = self.answers.get(key)
        if item is None:
            item = SimpleNamespace(id=f"answer-{len(self.answers) + 1}")
            self.answers[key] = item
        item.user_id = user_id
        item.submission_id = submission_id
        item.question_id = question.id
        item.answer_json = answer.value
        item.answer_status = answer.status
        item.score = None
        item.answered_at = now
        item.created_at = now
        return item

    async def complete_submission(self, submission, result, highest_tier, now):
        submission.status = f"completed_{highest_tier}"
        submission.highest_tier_completed = highest_tier
        submission.coverage = result.coverage
        submission.baseline_score = result.baseline_score
        submission.result_json = result.model_dump(mode="json")
        submission.submitted_at = now
        submission.updated_at = now
        return submission

    async def create_fact_candidates(self, user_id, submission_id, candidates, now):
        stored = []
        for candidate in candidates:
            stored.append(SimpleNamespace(id=f"candidate-{len(self.candidates) + 1}", **candidate))
        self.candidates.extend(stored)
        return stored

    async def list_fact_candidates(self, user_id, submission_id):
        return [candidate for candidate in self.candidates if candidate.user_id == user_id and candidate.submission_id == submission_id]

    async def commit(self):
        return None


@pytest.fixture
def service() -> AssessmentService:
    return AssessmentService(FakeAssessmentRepository())


@pytest.mark.asyncio
async def test_submission_can_be_answered_and_completed_with_pending_candidate(service):
    submission = await service.create_submission("user-1", AssessmentSubmissionCreate())

    await service.upsert_answer(
        "user-1", submission.id, "breakfast", AssessmentAnswerUpsert(value="regular")
    )
    await service.upsert_answer(
        "user-1", submission.id, "goal", AssessmentAnswerUpsert(value="ready")
    )
    result = await service.complete_submission("user-1", submission.id)

    assert result.submission.status == "completed_quick"
    assert result.submission.baseline_score == 100.0
    assert result.fact_candidates[0].status == "pending"


@pytest.mark.asyncio
async def test_low_coverage_completion_does_not_expose_total_score(service):
    submission = await service.create_submission("user-1", AssessmentSubmissionCreate())
    await service.upsert_answer(
        "user-1", submission.id, "breakfast", AssessmentAnswerUpsert(value="regular")
    )

    result = await service.complete_submission("user-1", submission.id)

    assert result.submission.coverage == 50.0
    assert result.submission.baseline_score is None


@pytest.mark.asyncio
async def test_other_user_cannot_read_or_answer_submission(service):
    submission = await service.create_submission("user-1", AssessmentSubmissionCreate())

    with pytest.raises(AssessmentNotFoundError):
        await service.get_questions("user-2", submission.id, "quick")

    with pytest.raises(AssessmentNotFoundError):
        await service.upsert_answer(
            "user-2", submission.id, "breakfast", AssessmentAnswerUpsert(value="regular")
        )


@pytest.mark.asyncio
async def test_invalid_answer_option_is_rejected(service):
    submission = await service.create_submission("user-1", AssessmentSubmissionCreate())

    with pytest.raises(AssessmentValidationError):
        await service.upsert_answer(
            "user-1", submission.id, "breakfast", AssessmentAnswerUpsert(value="other")
        )


@pytest.mark.asyncio
async def test_completing_same_submission_twice_does_not_duplicate_candidates(service):
    submission = await service.create_submission("user-1", AssessmentSubmissionCreate())
    await service.upsert_answer(
        "user-1", submission.id, "breakfast", AssessmentAnswerUpsert(value="regular")
    )
    await service.upsert_answer(
        "user-1", submission.id, "goal", AssessmentAnswerUpsert(value="ready")
    )

    first = await service.complete_submission("user-1", submission.id)
    second = await service.complete_submission("user-1", submission.id)

    assert len(first.fact_candidates) == 1
    assert len(second.fact_candidates) == 1
