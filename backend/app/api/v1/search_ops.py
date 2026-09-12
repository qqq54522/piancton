from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_search_ops_service, require_roles
from app.models.user import User
from app.schemas.search_ops import SearchActivitySummary, SearchOpsSummary
from app.services.search_ops_service import SearchOpsService

router = APIRouter(prefix="/admin/search-ops", tags=["admin"])


@router.get("/activity-summary", response_model=SearchActivitySummary)
def search_activity_summary(
    days: int = Query(default=7, ge=1, le=90),
    _: User = Depends(require_roles("designer", "admin")),
    service: SearchOpsService = Depends(get_search_ops_service),
):
    return service.activity_summary(days=days)


@router.get("/summary", response_model=SearchOpsSummary)
def search_ops_summary(
    days: int = Query(default=7, ge=1, le=90),
    _: User = Depends(require_roles("designer", "admin")),
    service: SearchOpsService = Depends(get_search_ops_service),
):
    return service.summary(days=days)
