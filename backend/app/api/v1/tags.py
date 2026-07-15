from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user, get_tag_service
from app.models.user import User
from app.schemas.tag import TagRead
from app.services.tag_service import TagService

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    _: User = Depends(get_current_user),
    service: TagService = Depends(get_tag_service),
):
    return service.list_tags()
