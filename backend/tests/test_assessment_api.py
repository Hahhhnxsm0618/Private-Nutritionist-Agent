from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.assessment.router import get_assessment_service
from app.assessment.schemas import (
    AssessmentCompleteResponse,
    AssessmentOnboardingResponse,
    AssessmentQuestionResponse,
    AssessmentScoreResult,
    AssessmentSubmissionResponse,
)
from app.assessment.service import AssessmentNotFoundError
from app.auth.router import get_current_user
from app.main import app
from app.profile.schemas import HealthFactResponse

NOW = datetime.now(UTC)


def _submission(user_id: str = "user-1") -> AssessmentSubmissionResponse:
    return AssessmentSubmissionResponse(
        id="submission-1",
        user_id=user_id,
        template_id="template-1",
        status="draft",
        highest_tier_completed=None,
        coverage=None,
        baseline_score=None,
        result_json=None,
        submitted_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


class StubAssessmentService:
    async def get_onboarding_state(self, user_id):
        return AssessmentOnboardingResponse(
            has_completed_quick=False,
            active_submission_id=None,
            available_tiers=["quick", "standard", "full"],
        )

    async def publish_template(self, template_id, publisher_user_id):
        assert publisher_user_id == "admin-1"
        return {
            "id": template_id,
            "code": "onboarding",
            "version": "quick-draft-v1",
            "status": "published",
            "target_population": "adult_general",
            "rule_version": "assessment-rules-v1",
            "published_at": NOW,
            "published_by_user_id": publisher_user_id,
            "created_at": NOW,
            "updated_at": NOW,
        }

    async def review_template(self, template_id, reviewer_user_id, request):
        return {
            "id": "review-1",
            "template_id": template_id,
            "reviewer_user_id": reviewer_user_id,
            "status": request.status,
            "rule_version": "assessment-rules-v1",
            "reviewed_at": NOW,
            "created_at": NOW,
        }

    async def create_submission(self, user_id, request):
        assert user_id == "user-1"
        return _submission(user_id)

    async def get_questions(self, user_id, submission_id, tier):
        if user_id != "user-1":
            raise AssessmentNotFoundError
        return [
            AssessmentQuestionResponse(
                id="question-1",
                code="goal",
                tier=tier,
                section="goal",
                answer_type="single",
                dimension="goal_feasibility",
                options_json=[{"value": "ready", "label": "准备好了"}],
                required=True,
                sort_order=1,
            )
        ]

    async def upsert_answer(self, user_id, submission_id, question_code, request):
        if user_id != "user-1":
            raise AssessmentNotFoundError
        return SimpleNamespace(
            id="answer-1",
            user_id=user_id,
            submission_id=submission_id,
            question_id="question-1",
            answer_json=request.value,
            answer_status=request.status,
            score=None,
            answered_at=NOW,
            created_at=NOW,
        )

    async def complete_submission(self, user_id, submission_id):
        return AssessmentCompleteResponse(
            submission=_submission(user_id).model_copy(update={"status": "completed_quick", "coverage": 100.0, "baseline_score": 100.0}),
            result=AssessmentScoreResult(
                coverage=100.0,
                baseline_score=100.0,
                dimensions={"diet_structure": None, "diet_behavior": None, "activity_routine": None, "goal_feasibility": 100.0},
                evidence=[],
                rule_version="assessment-rules-v1",
            ),
            fact_candidates=[],
        )

    async def get_result(self, user_id, submission_id):
        if user_id != "user-1":
            raise AssessmentNotFoundError
        return await self.complete_submission(user_id, submission_id)

    async def confirm_fact_candidate(self, user_id, submission_id, candidate_id):
        if user_id != "user-1":
            raise AssessmentNotFoundError
        return HealthFactResponse(
            id="fact-1",
            user_id=user_id,
            fact_type="goal",
            value={"value": "ready"},
            source_type="assessment",
            source_message_id=None,
            status="pending",
            consent_id="consent-1",
            valid_until=None,
            created_at=NOW,
            updated_at=NOW,
        )


def test_assessment_api_uses_authenticated_user_and_returns_core_flow() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-1"})()
    client = TestClient(app)

    try:
        state = client.get("/api/v1/assessments/onboarding")
        created = client.post("/api/v1/assessments/submissions", json={"tier": "quick"})
        questions = client.get("/api/v1/assessments/submissions/submission-1/questions?tier=quick")
        answer = client.put(
            "/api/v1/assessments/submissions/submission-1/answers/goal",
            json={"value": "ready"},
        )
        completed = client.post("/api/v1/assessments/submissions/submission-1/complete")
        confirmed = client.post(
            "/api/v1/assessments/submissions/submission-1/fact-candidates/candidate-1/confirm"
        )

        assert state.status_code == 200
        assert created.status_code == 201
        assert questions.status_code == 200
        assert answer.status_code == 200
        assert completed.status_code == 200
        assert completed.json()["submission"]["status"] == "completed_quick"
        assert confirmed.status_code == 200
        assert confirmed.json()["source_type"] == "assessment"
    finally:
        app.dependency_overrides.clear()


def test_assessment_api_maps_cross_user_resource_to_not_found() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type("User", (), {"id": "user-2"})()
    client = TestClient(app)

    try:
        response = client.get("/api/v1/assessments/submissions/submission-1/result")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "RESOURCE_NOT_FOUND"
    finally:
        app.dependency_overrides.clear()


def test_only_admin_can_publish_assessment_template() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"id": "admin-1", "role": "admin"}
    )()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/assessments/admin/templates/template-1/publish"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "published"
    finally:
        app.dependency_overrides.clear()


def test_non_admin_cannot_publish_assessment_template() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"id": "user-1", "role": "user"}
    )()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/assessments/admin/templates/template-1/publish"
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


def test_only_nutritionist_can_review_assessment_template() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"id": "nutritionist-1", "role": "nutritionist"}
    )()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/assessments/templates/template-1/review",
            json={"status": "approved"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
    finally:
        app.dependency_overrides.clear()


def test_non_nutritionist_cannot_review_assessment_template() -> None:
    app.dependency_overrides[get_assessment_service] = lambda: StubAssessmentService()
    app.dependency_overrides[get_current_user] = lambda: type(
        "User", (), {"id": "admin-1", "role": "admin"}
    )()
    client = TestClient(app)

    try:
        response = client.post(
            "/api/v1/assessments/templates/template-1/review",
            json={"status": "approved"},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "FORBIDDEN"
    finally:
        app.dependency_overrides.clear()
