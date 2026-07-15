from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_search_log_service, require_csrf
from app.models.user import User
from app.schemas.search_ops import SearchFeedbackCreate, SearchFeedbackRead
from app.services.search_log_service import SearchLogService

router = APIRouter(prefix="/search-feedback", tags=["search-feedback"])


@router.post("", response_model=SearchFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_search_feedback(
    payload: SearchFeedbackCreate,
    request: Request,
    user: User = Depends(require_csrf),
    service: SearchLogService = Depends(get_search_log_service),
):
    feedback = service.record_feedback(
        actor_user_id=user.id,
        payload=payload,
        request_id=request.state.request_id,
    )
    if feedback:
        return feedback
    return SearchFeedbackRead(
        id="",
        search_log_id=payload.search_log_id,
        keyword=payload.keyword,
        feedback_type=payload.feedback_type,
        note=payload.note,
        result_image_id=payload.result_image_id,
        asset_group_id=payload.asset_group_id,
        created_at=datetime.now(timezone.utc),
    )
