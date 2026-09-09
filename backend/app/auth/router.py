"""认证 HTTP 路由和当前用户依赖。"""

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import SqlAlchemyAuthRepository
from app.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import decode_access_token
from app.auth.service import AuthenticationError, AuthService, DuplicateEmailError
from app.db.session import get_db_session, settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    return AuthService(SqlAlchemyAuthRepository(session), auth_settings=settings)


def authentication_failed() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "AUTHENTICATION_FAILED", "message": "认证失败"},
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await service.register(request)
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "邮箱已注册"},
        ) from error


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await service.login(request)
    except AuthenticationError as error:
        raise authentication_failed() from error


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        return await service.refresh(request)
    except AuthenticationError as error:
        raise authentication_failed() from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> Response:
    await service.logout(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise authentication_failed()
    try:
        user_id = decode_access_token(credentials.credentials, service.settings)
        return await service.get_current_user(user_id)
    except (jwt.InvalidTokenError, AuthenticationError) as error:
        raise authentication_failed() from error


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)
