from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_usage_analytics_service, require_csrf, require_roles
from app.models.user import User
from app.schemas.usage import PageViewCreate, UsageAnalyticsSummary
from app.services.usage_analytics_service import UsageAnalyticsService

router = APIRouter(tags=["usage"])


@router.post("/usage/page-view", status_code=status.HTTP_204_NO_CONTENT)
def record_page_view(
    payload: PageViewCreate,
    user: User = Depends(require_csrf),
    service: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    service.record_page_view(user, path=payload.path, title=payload.title)


@router.get("/admin/usage/summary", response_model=UsageAnalyticsSummary)
def usage_summary(
    days: int = Query(default=7, ge=1, le=90),
    _: User = Depends(require_roles("admin")),
    service: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    return service.summary(days=days)
