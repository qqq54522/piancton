from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from app.api.dependencies import (
    get_asset_agent_service,
    get_asset_agent_temporary_image_service,
    require_csrf,
    require_roles,
)
from app.core.errors import ForbiddenError
from app.models.user import User
from app.schemas.asset_agent import (
    AssetAgentChatRequest,
    AssetAgentChatResponse,
    AssetAgentSessionContextUpdateRequest,
    AssetAgentSessionCreateRequest,
    AssetAgentSessionListResponse,
    AssetAgentSessionRead,
    AssetAgentTemporaryImageRead,
)
from app.services.asset_agent_service import AssetAgentService
from app.services.asset_agent_temporary_image_service import (
    AssetAgentTemporaryImageService,
)

router = APIRouter(prefix="/asset-agent", tags=["asset-agent"])


def require_asset_agent_user(user: User = Depends(require_csrf)) -> User:
    if user.role not in {"admin", "designer", "business"}:
        raise ForbiddenError()
    return user


@router.post(
    "/temporary-images",
    response_model=AssetAgentTemporaryImageRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_asset_agent_temporary_image(
    file: UploadFile = File(...),
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentTemporaryImageService = Depends(
        get_asset_agent_temporary_image_service
    ),
):
    return service.create(
        file.file,
        owner_id=user.id,
        filename=file.filename or "临时图片",
    )


@router.get("/temporary-images/{temporary_image_token}")
def get_asset_agent_temporary_image(
    temporary_image_token: str,
    service: AssetAgentTemporaryImageService = Depends(
        get_asset_agent_temporary_image_service
    ),
):
    image = service.public_file(temporary_image_token)
    return FileResponse(
        image.path,
        media_type=image.media_type,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


@router.delete(
    "/temporary-images/{temporary_image_token}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_asset_agent_temporary_image(
    temporary_image_token: str,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentTemporaryImageService = Depends(
        get_asset_agent_temporary_image_service
    ),
):
    service.delete(temporary_image_token, owner_id=user.id)


@router.get("/sessions", response_model=AssetAgentSessionListResponse)
def list_asset_agent_sessions(
    user: User = Depends(require_roles("admin", "designer", "business")),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return service.list_sessions(user)


@router.post("/sessions", response_model=AssetAgentSessionRead)
def create_asset_agent_session(
    payload: AssetAgentSessionCreateRequest,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return service.create_session(user, payload)


@router.patch("/sessions/{session_id}/context", response_model=AssetAgentSessionRead)
def update_asset_agent_session_context(
    session_id: str,
    payload: AssetAgentSessionContextUpdateRequest,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return service.update_context(user, session_id, payload)


@router.post("/sessions/{session_id}/messages", response_model=AssetAgentChatResponse)
def send_asset_agent_message(
    session_id: str,
    payload: AssetAgentChatRequest,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return service.chat_in_session(user, session_id, payload)


@router.post("/sessions/{session_id}/messages/stream")
def stream_asset_agent_message(
    session_id: str,
    payload: AssetAgentChatRequest,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return StreamingResponse(
        service.chat_in_session_stream(user, session_id, payload),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset_agent_session(
    session_id: str,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    service.delete_session(user, session_id)


@router.post("/chat", response_model=AssetAgentChatResponse)
def chat_with_asset_agent(
    payload: AssetAgentChatRequest,
    user: User = Depends(require_asset_agent_user),
    service: AssetAgentService = Depends(get_asset_agent_service),
):
    return service.chat(user, payload)
