from fastapi import APIRouter, Depends, Request

from app.api.dependencies import (
    get_audit_service,
    get_channel_folder_service,
    get_current_user,
    require_write_role,
)
from app.models.user import User
from app.schemas.channel_folder import (
    ChannelCreate,
    ChannelRead,
    FolderCreate,
    FolderRead,
    FolderRename,
    PlacementBatch,
    PlacementResult,
)
from app.services.audit_service import AuditService
from app.services.channel_folder_service import ChannelFolderService

router = APIRouter(prefix="/channel-folders", tags=["channel-folders"])


@router.get("", response_model=list[ChannelRead])
def catalog(
    _: User = Depends(get_current_user),
    service: ChannelFolderService = Depends(get_channel_folder_service),
):
    return service.list_catalog()


@router.post("/channels", response_model=list[ChannelRead])
def create_channel(
    payload: ChannelCreate,
    request: Request,
    user: User = Depends(require_write_role),
    service: ChannelFolderService = Depends(get_channel_folder_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.create_channel(payload.name)
    audit.record(
        actor_user_id=user.id,
        action="channel.create",
        target_type="channel",
        target_id=payload.name.strip(),
        request_id=request.state.request_id,
    )
    return service.list_catalog()


@router.post("/folders", response_model=FolderRead)
def create_folder(
    payload: FolderCreate,
    request: Request,
    user: User = Depends(require_write_role),
    service: ChannelFolderService = Depends(get_channel_folder_service),
    audit: AuditService = Depends(get_audit_service),
):
    folder = service.create_folder(payload.channel, payload.name, payload.parent_id)
    audit.record(
        actor_user_id=user.id,
        action="channel.folder.create",
        target_type="channel_folder",
        target_id=folder.id,
        details={"channel": payload.channel, "parentId": payload.parent_id},
        request_id=request.state.request_id,
    )
    return folder


@router.patch("/folders/{folder_id}", response_model=list[ChannelRead])
def rename_folder(
    folder_id: str,
    payload: FolderRename,
    request: Request,
    user: User = Depends(require_write_role),
    service: ChannelFolderService = Depends(get_channel_folder_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.rename_folder(folder_id, payload.name)
    audit.record(
        actor_user_id=user.id,
        action="channel.folder.rename",
        target_type="channel_folder",
        target_id=folder_id,
        details={"name": payload.name},
        request_id=request.state.request_id,
    )
    return service.list_catalog()


@router.delete("/folders/{folder_id}", response_model=list[ChannelRead])
def delete_folder(
    folder_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: ChannelFolderService = Depends(get_channel_folder_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.delete_folder(folder_id)
    audit.record(
        actor_user_id=user.id,
        action="channel.folder.delete",
        target_type="channel_folder",
        target_id=folder_id,
        request_id=request.state.request_id,
    )
    return service.list_catalog()


@router.post("/placements", response_model=PlacementResult)
def assign(
    payload: PlacementBatch,
    request: Request,
    user: User = Depends(require_write_role),
    service: ChannelFolderService = Depends(get_channel_folder_service),
    audit: AuditService = Depends(get_audit_service),
):
    count = service.assign(payload.channel, payload.image_ids, payload.folder_id)
    audit.record(
        actor_user_id=user.id,
        action="channel.folder.assign",
        target_type="channel_folder",
        target_id=payload.folder_id,
        details={"channel": payload.channel, "imageIds": payload.image_ids},
        request_id=request.state.request_id,
    )
    return PlacementResult(assigned=count)
