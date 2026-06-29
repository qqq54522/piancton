from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import get_search_analytics_service, require_csrf
from app.models.user import User
from app.schemas.search_ops import SearchFeedbackCreate, SearchFeedbackRead
from app.services.search_analytics_service import SearchAnalyticsService

router = APIRouter(prefix="/search-feedback", tags=["search-feedback"])


@router.post("", response_model=SearchFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_search_feedback(
    payload: SearchFeedbackCreate,
    request: Request,
    user: User = Depends(require_csrf),
    service: SearchAnalyticsService = Depends(get_search_analytics_service),
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
        created_at=datetime.now(timezone.utc),
    )
