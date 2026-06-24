from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import (
    get_audit_service,
    get_current_user,
    get_tag_service,
    require_roles,
    require_write_role,
)
from app.models.user import User
from app.schemas.tag import TagCreate, TagDeleteImpact, TagRead, TagUpdate
from app.services.audit_service import AuditService
from app.services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    _: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    return service.list_tags()


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
def create_tag(
    payload: TagCreate,
    request: Request,
    user: User = Depends(require_write_role),
    service: TagService = Depends(get_tag_service),
    audit: AuditService = Depends(get_audit_service),
):
    tag = service.create(payload)
    audit.record(
        actor_user_id=user.id,
        action="tag.create",
        target_type="tag",
        target_id=tag.id,
        details={"name": tag.name, "parentId": tag.parent_id},
        request_id=request.state.request_id,
    )
    return tag


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(
    tag_id: str,
    payload: TagUpdate,
    request: Request,
    user: User = Depends(require_write_role),
    service: TagService = Depends(get_tag_service),
    audit: AuditService = Depends(get_audit_service),
):
    tag = service.update(tag_id, payload)
    audit.record(
        actor_user_id=user.id,
        action="tag.update",
        target_type="tag",
        target_id=tag_id,
        details=payload.model_dump(exclude_unset=True),
        request_id=request.state.request_id,
    )
    return tag


@router.get("/{tag_id}/delete-impact", response_model=TagDeleteImpact)
def delete_impact(
    tag_id: str,
    _: User = Depends(require_roles("designer", "admin")),
    service: TagService = Depends(get_tag_service),
):
    return service.delete_impact(tag_id)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(
    tag_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: TagService = Depends(get_tag_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.delete(tag_id)
    audit.record(
        actor_user_id=user.id,
        action="tag.delete",
        target_type="tag",
        target_id=tag_id,
        request_id=request.state.request_id,
    )
