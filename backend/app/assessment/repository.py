"""首次登录问卷的 SQLAlchemy 数据访问。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.schemas import AssessmentAnswerUpsert
from app.assessment.scoring import AssessmentScoreResult
from app.models.assessment import (
    AssessmentAnswer,
    AssessmentFactCandidate,
    AssessmentQuestion,
    AssessmentSubmission,
    AssessmentTemplate,
)


class SqlAlchemyAssessmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_published_template(self, code: str) -> AssessmentTemplate | None:
        result = await self.session.execute(
            select(AssessmentTemplate)
            .where(AssessmentTemplate.code == code, AssessmentTemplate.status == "published")
            .order_by(AssessmentTemplate.published_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_template_for_submission(self, submission: AssessmentSubmission) -> AssessmentTemplate:
        result = await self.session.execute(
            select(AssessmentTemplate).where(AssessmentTemplate.id == submission.template_id)
        )
        return result.scalar_one()

    async def get_submission(self, user_id: str, submission_id: str) -> AssessmentSubmission | None:
        result = await self.session.execute(
            select(AssessmentSubmission).where(
                AssessmentSubmission.id == submission_id,
                AssessmentSubmission.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_draft_submission(
        self, user_id: str, template_id: str
    ) -> AssessmentSubmission | None:
        result = await self.session.execute(
            select(AssessmentSubmission)
            .where(
                AssessmentSubmission.user_id == user_id,
                AssessmentSubmission.template_id == template_id,
                AssessmentSubmission.status == "draft",
            )
            .order_by(AssessmentSubmission.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def has_completed_quick(self, user_id: str, template_id: str) -> bool:
        result = await self.session.execute(
            select(AssessmentSubmission.id).where(
                AssessmentSubmission.user_id == user_id,
                AssessmentSubmission.template_id == template_id,
                AssessmentSubmission.status == "completed_quick",
            )
        )
        return result.first() is not None

    async def create_submission(
        self, user_id: str, template_id: str, now: datetime
    ) -> AssessmentSubmission:
        submission = AssessmentSubmission(
            user_id=user_id,
            template_id=template_id,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        self.session.add(submission)
        await self.session.flush()
        await self.session.refresh(submission)
        return submission

    async def list_questions(self, template_id: str, tiers: list[str]) -> list[AssessmentQuestion]:
        result = await self.session.execute(
            select(AssessmentQuestion)
            .where(
                AssessmentQuestion.template_id == template_id,
                AssessmentQuestion.tier.in_(tiers),
            )
            .order_by(AssessmentQuestion.sort_order.asc())
        )
        return list(result.scalars().all())

    async def get_question(self, template_id: str, question_code: str) -> AssessmentQuestion | None:
        result = await self.session.execute(
            select(AssessmentQuestion).where(
                AssessmentQuestion.template_id == template_id,
                AssessmentQuestion.code == question_code,
            )
        )
        return result.scalar_one_or_none()

    async def list_answers(self, user_id: str, submission_id: str) -> list[AssessmentAnswer]:
        result = await self.session.execute(
            select(AssessmentAnswer)
            .where(
                AssessmentAnswer.user_id == user_id,
                AssessmentAnswer.submission_id == submission_id,
            )
            .order_by(AssessmentAnswer.created_at.asc())
        )
        return list(result.scalars().all())

    async def upsert_answer(
        self,
        user_id: str,
        submission_id: str,
        question: AssessmentQuestion,
        answer: AssessmentAnswerUpsert,
        now: datetime,
    ) -> AssessmentAnswer:
        result = await self.session.execute(
            select(AssessmentAnswer).where(
                AssessmentAnswer.user_id == user_id,
                AssessmentAnswer.submission_id == submission_id,
                AssessmentAnswer.question_id == question.id,
            )
        )
        stored = result.scalar_one_or_none()
        if stored is None:
            stored = AssessmentAnswer(
                user_id=user_id,
                submission_id=submission_id,
                question_id=question.id,
                created_at=now,
            )
            self.session.add(stored)
        stored.answer_json = answer.value
        stored.answer_status = answer.status
        stored.score = None
        stored.answered_at = now
        await self.session.flush()
        await self.session.refresh(stored)
        return stored

    async def complete_submission(
        self,
        submission: AssessmentSubmission,
        result: AssessmentScoreResult,
        highest_tier: str,
        now: datetime,
    ) -> AssessmentSubmission:
        submission.status = f"completed_{highest_tier}"
        submission.highest_tier_completed = highest_tier
        submission.coverage = result.coverage
        submission.baseline_score = result.baseline_score
        submission.result_json = result.model_dump(mode="json")
        submission.submitted_at = now
        submission.updated_at = now
        await self.session.flush()
        await self.session.refresh(submission)
        return submission

    async def create_fact_candidates(
        self, user_id: str, submission_id: str, candidates: list[dict], now: datetime
    ) -> list[AssessmentFactCandidate]:
        stored = [AssessmentFactCandidate(created_at=now, updated_at=now, **candidate) for candidate in candidates]
        self.session.add_all(stored)
        await self.session.flush()
        for candidate in stored:
            await self.session.refresh(candidate)
        return stored

    async def list_fact_candidates(
        self, user_id: str, submission_id: str
    ) -> list[AssessmentFactCandidate]:
        result = await self.session.execute(
            select(AssessmentFactCandidate).where(
                AssessmentFactCandidate.user_id == user_id,
                AssessmentFactCandidate.submission_id == submission_id,
            )
        )
        return list(result.scalars().all())

    async def commit(self) -> None:
        await self.session.commit()
