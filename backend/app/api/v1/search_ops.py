from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_search_analytics_service, require_admin_role
from app.models.user import User
from app.schemas.search_ops import SearchOpsSummary
from app.services.search_analytics_service import SearchAnalyticsService

router = APIRouter(prefix="/admin/search-ops", tags=["admin"])


@router.get("/summary", response_model=SearchOpsSummary)
def search_ops_summary(
    days: int = Query(default=7, ge=1, le=90),
    _: User = Depends(require_admin_role),
    service: SearchAnalyticsService = Depends(get_search_analytics_service),
):
    return service.summary(days=days)
