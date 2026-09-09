"""首次登录问卷的用户隔离和完成流程。"""

from datetime import UTC, datetime
from typing import Protocol

from app.assessment.schemas import (
    AssessmentAnswerUpsert,
    AssessmentCompleteResponse,
    AssessmentOnboardingResponse,
    AssessmentQuestionResponse,
    AssessmentSubmissionCreate,
    AssessmentSubmissionResponse,
)
from app.assessment.scoring import (
    AssessmentAnswerForScoring,
    AssessmentQuestionForScoring,
    calculate_assessment_result,
)


class AssessmentNotFoundError(Exception):
    pass


class AssessmentValidationError(Exception):
    pass


class AssessmentRepository(Protocol):
    async def get_published_template(self, code: str): ...
    async def get_template_for_submission(self, submission): ...
    async def get_submission(self, user_id: str, submission_id: str): ...
    async def get_draft_submission(self, user_id: str, template_id: str): ...
    async def has_completed_quick(self, user_id: str, template_id: str) -> bool: ...
    async def create_submission(self, user_id: str, template_id: str, now: datetime): ...
    async def list_questions(self, template_id: str, tiers: list[str]): ...
    async def get_question(self, template_id: str, question_code: str): ...
    async def list_answers(self, user_id: str, submission_id: str): ...
    async def upsert_answer(self, user_id: str, submission_id: str, question, answer, now: datetime): ...
    async def complete_submission(self, submission, result, highest_tier: str, now: datetime): ...
    async def create_fact_candidates(self, user_id: str, submission_id: str, candidates, now: datetime): ...
    async def list_fact_candidates(self, user_id: str, submission_id: str): ...
    async def commit(self) -> None: ...


TIER_ORDER = {"quick": 1, "standard": 2, "full": 3}


class AssessmentService:
    def __init__(self, repository: AssessmentRepository) -> None:
        self.repository = repository

    async def get_onboarding_state(self, user_id: str) -> AssessmentOnboardingResponse:
        template = await self.repository.get_published_template("onboarding")
        if template is None:
            return AssessmentOnboardingResponse(
                has_completed_quick=False,
                active_submission_id=None,
                available_tiers=["quick", "standard", "full"],
            )
        draft = await self.repository.get_draft_submission(user_id, template.id)
        return AssessmentOnboardingResponse(
            has_completed_quick=await self.repository.has_completed_quick(user_id, template.id),
            active_submission_id=draft.id if draft else None,
            available_tiers=["quick", "standard", "full"],
        )

    async def create_submission(self, user_id: str, request: AssessmentSubmissionCreate):
        template = await self.repository.get_published_template(request.template_code)
        if template is None:
            raise AssessmentNotFoundError
        draft = await self.repository.get_draft_submission(user_id, template.id)
        if draft:
            return draft
        submission = await self.repository.create_submission(user_id, template.id, datetime.now(UTC))
        await self.repository.commit()
        return submission

    async def get_questions(
        self, user_id: str, submission_id: str, tier: str
    ) -> list[AssessmentQuestionResponse]:
        if tier not in TIER_ORDER:
            raise AssessmentValidationError("invalid tier")
        submission = await self._get_submission(user_id, submission_id)
        tiers = [name for name, order in TIER_ORDER.items() if order <= TIER_ORDER[tier]]
        questions = await self.repository.list_questions(submission.template_id, tiers)
        answers = await self.repository.list_answers(user_id, submission_id)
        answered_question_ids = {answer.question_id for answer in answers}
        return [
            AssessmentQuestionResponse.model_validate(question)
            for question in questions
            if question.id not in answered_question_ids
        ]

    async def upsert_answer(
        self,
        user_id: str,
        submission_id: str,
        question_code: str,
        request: AssessmentAnswerUpsert,
    ):
        submission = await self._get_submission(user_id, submission_id)
        question = await self.repository.get_question(submission.template_id, question_code)
        if question is None:
            raise AssessmentNotFoundError
        if request.status == "answered" and not self._is_valid_option(question.options_json, request.value):
            raise AssessmentValidationError("invalid option")
        answer = await self.repository.upsert_answer(
            user_id, submission_id, question, request, datetime.now(UTC)
        )
        await self.repository.commit()
        return answer

    async def complete_submission(
        self, user_id: str, submission_id: str
    ) -> AssessmentCompleteResponse:
        submission = await self._get_submission(user_id, submission_id)
        if submission.status.startswith("completed_") and submission.result_json:
            return await self.get_result(user_id, submission_id)
        template = await self.repository.get_template_for_submission(submission)
        questions = await self.repository.list_questions(submission.template_id, ["quick"])
        answers = await self.repository.list_answers(user_id, submission_id)
        score_questions = [
            AssessmentQuestionForScoring(
                code=question.code,
                dimension=question.dimension or "diet_behavior",
                score_by_option=(question.scoring_rule_json or {}).get("score_by_option", {}),
            )
            for question in questions
            if question.scoring_rule_json
        ]
        score_answers = [
            AssessmentAnswerForScoring(
                question_code=question.code,
                value=self._answer_value(answer.answer_json),
                status=answer.answer_status,
            )
            for question in questions
            for answer in answers
            if answer.question_id == question.id
        ]
        result = calculate_assessment_result(
            score_questions,
            score_answers,
            rule_version=template.rule_version,
        )
        completed = await self.repository.complete_submission(
            submission, result, "quick", datetime.now(UTC)
        )
        candidates = self._build_candidates(user_id, submission_id, questions, answers)
        await self.repository.create_fact_candidates(
            user_id, submission_id, candidates, datetime.now(UTC)
        )
        stored_candidates = await self.repository.list_fact_candidates(user_id, submission_id)
        await self.repository.commit()
        return AssessmentCompleteResponse(
            submission=AssessmentSubmissionResponse.model_validate(completed),
            result=result,
            fact_candidates=stored_candidates,
        )

    async def get_result(self, user_id: str, submission_id: str) -> AssessmentCompleteResponse:
        submission = await self._get_submission(user_id, submission_id)
        if not submission.result_json:
            raise AssessmentValidationError("assessment is not completed")
        candidates = await self.repository.list_fact_candidates(user_id, submission_id)
        from app.assessment.scoring import AssessmentScoreResult

        return AssessmentCompleteResponse(
            submission=AssessmentSubmissionResponse.model_validate(submission),
            result=AssessmentScoreResult.model_validate(submission.result_json),
            fact_candidates=candidates,
        )

    async def _get_submission(self, user_id: str, submission_id: str):
        submission = await self.repository.get_submission(user_id, submission_id)
        if submission is None:
            raise AssessmentNotFoundError
        return submission

    @staticmethod
    def _is_valid_option(options, value) -> bool:
        if isinstance(options, dict):
            return value in options
        return any(isinstance(option, dict) and option.get("value") == value for option in options)

    @staticmethod
    def _answer_value(value):
        if isinstance(value, dict):
            return value.get("value")
        return value

    @staticmethod
    def _build_candidates(user_id, submission_id, questions, answers):
        answer_by_question = {answer.question_id: answer for answer in answers}
        candidates = []
        for question in questions:
            answer = answer_by_question.get(question.id)
            if answer and answer.answer_status == "answered" and question.code == "goal":
                candidates.append(
                    {
                        "user_id": user_id,
                        "submission_id": submission_id,
                        "fact_type": "goal",
                        "value_json": {"value": AssessmentService._answer_value(answer.answer_json)},
                        "sensitivity": "normal",
                        "status": "pending",
                        "consent_required": True,
                    }
                )
        return candidates
