"""首次登录问卷和饮食画像评估 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.assessment.repository import SqlAlchemyAssessmentRepository
from app.assessment.schemas import (
    AssessmentAnswerResponse,
    AssessmentAnswerUpsert,
    AssessmentCompleteResponse,
    AssessmentOnboardingResponse,
    AssessmentQuestionResponse,
    AssessmentReviewRequest,
    AssessmentReviewResponse,
    AssessmentSubmissionCreate,
    AssessmentSubmissionResponse,
    AssessmentTemplateResponse,
)
from app.assessment.service import (
    AssessmentNotFoundError,
    AssessmentService,
    AssessmentValidationError,
)
from app.auth.router import get_current_user
from app.db.session import get_db_session
from app.profile.repository import SqlAlchemyProfileRepository
from app.profile.schemas import HealthFactResponse
from app.profile.service import MemoryDisabledError

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


async def get_assessment_service(
    session: AsyncSession = Depends(get_db_session),
) -> AssessmentService:
    return AssessmentService(
        SqlAlchemyAssessmentRepository(session),
        SqlAlchemyProfileRepository(session),
    )


def resource_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "RESOURCE_NOT_FOUND", "message": "资源不存在"},
    )


def validation_failed(error: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": "ASSESSMENT_VALIDATION_ERROR", "message": str(error)},
    )


async def get_admin_user(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "需要管理员权限"},
        )
    return user


async def get_nutritionist_user(user=Depends(get_current_user)):
    if user.role != "nutritionist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "需要营养师权限"},
        )
    return user


@router.get("/onboarding", response_model=AssessmentOnboardingResponse)
async def onboarding(
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentOnboardingResponse:
    return await service.get_onboarding_state(user.id)


@router.post(
    "/admin/templates/{template_id}/publish",
    response_model=AssessmentTemplateResponse,
)
async def publish_template(
    template_id: str,
    user=Depends(get_admin_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentTemplateResponse:
    try:
        return await service.publish_template(template_id, user.id)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "PROFESSIONAL_REVIEW_REQUIRED",
                "message": "模板发布前必须完成营养师专业审核",
            },
        ) from error


@router.post(
    "/templates/{template_id}/review",
    response_model=AssessmentReviewResponse,
)
async def review_template(
    template_id: str,
    request: AssessmentReviewRequest,
    user=Depends(get_nutritionist_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentReviewResponse:
    try:
        return await service.review_template(template_id, user.id, request)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error


@router.post(
    "/submissions",
    response_model=AssessmentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    request: AssessmentSubmissionCreate,
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentSubmissionResponse:
    try:
        return await service.create_submission(user.id, request)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error


@router.get(
    "/submissions/{submission_id}/questions",
    response_model=list[AssessmentQuestionResponse],
)
async def list_questions(
    submission_id: str,
    tier: str = Query(default="quick"),
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> list[AssessmentQuestionResponse]:
    try:
        return await service.get_questions(user.id, submission_id, tier)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error


@router.put(
    "/submissions/{submission_id}/answers/{question_code}",
    response_model=AssessmentAnswerResponse,
)
async def upsert_answer(
    submission_id: str,
    question_code: str,
    request: AssessmentAnswerUpsert,
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentAnswerResponse:
    try:
        return await service.upsert_answer(user.id, submission_id, question_code, request)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error


@router.post(
    "/submissions/{submission_id}/complete",
    response_model=AssessmentCompleteResponse,
)
async def complete_submission(
    submission_id: str,
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentCompleteResponse:
    try:
        return await service.complete_submission(user.id, submission_id)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error


@router.get(
    "/submissions/{submission_id}/result",
    response_model=AssessmentCompleteResponse,
)
async def get_result(
    submission_id: str,
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> AssessmentCompleteResponse:
    try:
        return await service.get_result(user.id, submission_id)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error


@router.post(
    "/submissions/{submission_id}/fact-candidates/{candidate_id}/confirm",
    response_model=HealthFactResponse,
)
async def confirm_fact_candidate(
    submission_id: str,
    candidate_id: str,
    user=Depends(get_current_user),
    service: AssessmentService = Depends(get_assessment_service),
) -> HealthFactResponse:
    try:
        return await service.confirm_fact_candidate(user.id, submission_id, candidate_id)
    except AssessmentNotFoundError as error:
        raise resource_not_found() from error
    except MemoryDisabledError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "MEMORY_DISABLED", "message": "长期记忆已关闭，不能确认候选画像事实"},
        ) from error
    except AssessmentValidationError as error:
        raise validation_failed(error) from error
