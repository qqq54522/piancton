from fastapi import APIRouter, Depends, Query, Request, status

from app.api.dependencies import (
    get_audit_service,
    get_user_service,
    require_admin,
    require_admin_role,
)
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.auth import PasswordReset, UserCreate, UserRead, UserUpdate
from app.services.audit_service import AuditService
from app.services.user_service import UserService

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_admin_role),
    audit: AuditService = Depends(get_audit_service),
):
    return audit.list_recent(limit)


@router.get("", response_model=list[UserRead])
def list_users(
    _: User = Depends(require_admin_role),
    service: UserService = Depends(get_user_service),
):
    return service.list()


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    request: Request,
    actor: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
    audit: AuditService = Depends(get_audit_service),
):
    user = service.create(payload)
    audit.record(
        actor_user_id=actor.id,
        action="user.create",
        target_type="user",
        target_id=user.id,
        details={"username": user.username, "role": user.role},
        request_id=request.state.request_id,
    )
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    actor: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
    audit: AuditService = Depends(get_audit_service),
):
    user = service.update(user_id, payload, actor.id)
    audit.record(
        actor_user_id=actor.id,
        action="user.update",
        target_type="user",
        target_id=user.id,
        details=payload.model_dump(exclude_unset=True),
        request_id=request.state.request_id,
    )
    return user


@router.post("/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: str,
    payload: PasswordReset,
    request: Request,
    actor: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.reset_password(user_id, payload.password)
    audit.record(
        actor_user_id=actor.id,
        action="user.reset_password",
        target_type="user",
        target_id=user_id,
        request_id=request.state.request_id,
    )
