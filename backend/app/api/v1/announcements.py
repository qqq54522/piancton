from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import (
    get_announcement_service,
    get_audit_service,
    get_current_user,
    require_csrf,
    require_roles,
    require_write_role,
)
from app.core.errors import ForbiddenError
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementFeedResponse,
    AnnouncementListResponse,
    AnnouncementMarkRead,
    AnnouncementRead,
    AnnouncementUnreadCount,
)
from app.services.announcement_service import AnnouncementService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/announcements", tags=["announcements"])
admin_router = APIRouter(prefix="/admin/announcements", tags=["announcements"])


def _require_business(user: User) -> User:
    if user.role != "business":
        raise ForbiddenError()
    return user


@router.get("", response_model=AnnouncementFeedResponse)
def get_feed(
    user: User = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    return service.feed(_require_business(user))


@router.get("/unread-count", response_model=AnnouncementUnreadCount)
def get_unread_count(
    user: User = Depends(get_current_user),
    service: AnnouncementService = Depends(get_announcement_service),
):
    return service.unread_count(_require_business(user))


@router.post("/read", response_model=AnnouncementUnreadCount)
def mark_read(
    payload: AnnouncementMarkRead,
    user: User = Depends(require_csrf),
    service: AnnouncementService = Depends(get_announcement_service),
):
    return service.mark_read(_require_business(user), payload.through_published_at)


@admin_router.get("", response_model=AnnouncementListResponse)
def list_announcements(
    _: User = Depends(require_roles("designer", "admin")),
    service: AnnouncementService = Depends(get_announcement_service),
):
    return service.list_for_managers()


@admin_router.post(
    "",
    response_model=AnnouncementRead,
    status_code=status.HTTP_201_CREATED,
)
def publish_announcement(
    payload: AnnouncementCreate,
    request: Request,
    actor: User = Depends(require_write_role),
    service: AnnouncementService = Depends(get_announcement_service),
    audit: AuditService = Depends(get_audit_service),
):
    announcement = service.publish(actor, payload)
    audit.record(
        actor_user_id=actor.id,
        action="announcement.publish",
        target_type="announcement",
        target_id=announcement.id,
        details={"title": announcement.title},
        request_id=request.state.request_id,
    )
    return announcement
