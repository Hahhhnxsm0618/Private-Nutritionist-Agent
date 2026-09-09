"""健康档案、健康事实和长期记忆设置的 HTTP 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user
from app.db.session import get_db_session
from app.profile.repository import SqlAlchemyProfileRepository
from app.profile.schemas import (
    HealthFactCreate,
    HealthFactResponse,
    HealthFactUpdate,
    ProfileResponse,
    ProfileUpdate,
)
from app.profile.service import (
    ConsentRequiredError,
    HealthProfileService,
    MemoryDisabledError,
    ResourceNotFoundError,
)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


async def get_profile_service(session: AsyncSession = Depends(get_db_session)) -> HealthProfileService:
    return HealthProfileService(SqlAlchemyProfileRepository(session))


def resource_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "RESOURCE_NOT_FOUND", "message": "资源不存在"},
    )


@router.get("", response_model=ProfileResponse)
async def get_profile(
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    try:
        return await service.get_profile(user.id)
    except ResourceNotFoundError as error:
        raise resource_not_found() from error


@router.patch("", response_model=ProfileResponse)
async def update_profile(
    request: ProfileUpdate,
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.update_profile(user.id, request)


@router.get("/facts", response_model=list[HealthFactResponse])
async def list_facts(
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> list[HealthFactResponse]:
    return await service.list_facts(user.id)


@router.post("/facts", response_model=HealthFactResponse, status_code=status.HTTP_201_CREATED)
async def create_fact(
    request: HealthFactCreate,
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> HealthFactResponse:
    try:
        return await service.create_fact(user.id, request)
    except ConsentRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "CONSENT_REQUIRED", "message": "保存健康事实前必须明确授权"},
        ) from error
    except MemoryDisabledError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "MEMORY_DISABLED", "message": "长期记忆已关闭，不能保存健康事实"},
        ) from error


@router.patch("/facts/{fact_id}", response_model=HealthFactResponse)
async def update_fact(
    fact_id: str,
    request: HealthFactUpdate,
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> HealthFactResponse:
    try:
        return await service.update_fact(user.id, fact_id, request)
    except ResourceNotFoundError as error:
        raise resource_not_found() from error


@router.post("/facts/{fact_id}/confirm", response_model=HealthFactResponse)
async def confirm_fact(
    fact_id: str,
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> HealthFactResponse:
    try:
        return await service.confirm_fact(user.id, fact_id)
    except ResourceNotFoundError as error:
        raise resource_not_found() from error


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fact(
    fact_id: str,
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> Response:
    try:
        await service.delete_fact(user.id, fact_id)
    except ResourceNotFoundError as error:
        raise resource_not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/memory/disable", response_model=ProfileResponse)
async def disable_memory(
    user=Depends(get_current_user),
    service: HealthProfileService = Depends(get_profile_service),
) -> ProfileResponse:
    return await service.disable_memory(user.id)
