"""对话会话和消息持久化 HTTP 路由。"""

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.router import get_current_user
from app.conversation.repository import SqlAlchemyConversationRepository
from app.conversation.schemas import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    MessageTurnResponse,
)
from app.conversation.service import (
    ConversationArchivedError,
    ConversationNotFoundError,
    ConversationService,
)
from app.db.session import get_db_session

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


async def get_conversation_service(
    session: AsyncSession = Depends(get_db_session),
) -> ConversationService:
    return ConversationService(SqlAlchemyConversationRepository(session))


def resource_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "RESOURCE_NOT_FOUND", "message": "资源不存在"},
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    return await service.create_conversation(user.id, request)


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    include_archived: bool = Query(default=False),
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationResponse]:
    return await service.list_conversations(user.id, include_archived)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationResponse:
    try:
        return await service.get_conversation(user.id, conversation_id)
    except ConversationNotFoundError as error:
        raise resource_not_found() from error


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_conversation(
    conversation_id: str,
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> Response:
    try:
        await service.archive_conversation(user.id, conversation_id)
    except ConversationNotFoundError as error:
        raise resource_not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> list[MessageResponse]:
    try:
        return await service.list_messages(user.id, conversation_id, limit)
    except ConversationNotFoundError as error:
        raise resource_not_found() from error


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageTurnResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user_message(
    conversation_id: str,
    request: MessageCreate,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> MessageTurnResponse:
    try:
        return await service.create_user_message(
            user.id,
            conversation_id,
            request,
            request_id or str(uuid4()),
        )
    except ConversationNotFoundError as error:
        raise resource_not_found() from error
    except ConversationArchivedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONVERSATION_ARCHIVED", "message": "会话已归档，不能继续发送消息"},
        ) from error


@router.post(
    "/{conversation_id}/retry",
    response_model=MessageTurnResponse,
)
async def retry_user_message(
    conversation_id: str,
    message_id: str,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> MessageTurnResponse:
    try:
        return await service.retry_user_message(
            user.id, conversation_id, message_id, request_id or str(uuid4())
        )
    except ConversationNotFoundError as error:
        raise resource_not_found() from error
    except ConversationArchivedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONVERSATION_ARCHIVED", "message": "会话已归档，不能重试消息"},
        ) from error


@router.post(
    "/{conversation_id}/messages/stream",
    response_class=StreamingResponse,
)
async def stream_user_message(
    conversation_id: str,
    request: MessageCreate,
    request_id: str | None = Header(default=None, alias="X-Request-ID"),
    user=Depends(get_current_user),
    service: ConversationService = Depends(get_conversation_service),
) -> StreamingResponse:
    try:
        stream = service.stream_user_message(
            user.id, conversation_id, request, request_id or str(uuid4())
        )
        return StreamingResponse(stream, media_type="text/event-stream")
    except ConversationNotFoundError as error:
        raise resource_not_found() from error
    except ConversationArchivedError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONVERSATION_ARCHIVED", "message": "会话已归档，不能继续发送消息"},
        ) from error
