from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from app.schemas.base import ApiModel

UsageEventType = Literal["login", "page_view", "download", "search_interaction"]

SearchInteractionAction = Literal[
    "exposure",
    "open_detail",
    "download",
    "copy_identity",
    "add_to_project",
    "remove_from_project",
    "send_to_agent",
]


class PageViewCreate(ApiModel):
    path: str
    title: Optional[str] = None


class SearchInteractionCreate(ApiModel):
    search_log_id: Optional[str] = None
    keyword: str = ""
    action: SearchInteractionAction
    result_image_id: Optional[str] = None
    asset_group_id: Optional[str] = None
    position: Optional[int] = None
    source: Literal[
        "search_results",
        "agent_chat",
        "detail_same_selling_point",
        "detail_visual_similar",
        "detail_same_channel",
        "detail_current_channel",
        "detail_mobile_large",
        "detail_mobile_small",
        "detail_brand_manual",
        "detail_website",
        "detail_ppt",
        "detail_personalized",
    ] = "search_results"
    conversation_id: Optional[str] = None


class UsageTotals(ApiModel):
    login_count: int
    page_view_count: int
    download_count: int
    active_user_count: int


class DailyUsageMetric(ApiModel):
    date: date
    login_count: int
    page_view_count: int
    download_count: int
    active_user_count: int


class UserUsageMetric(ApiModel):
    user_id: str
    username: str
    role: str
    is_active: bool
    login_count: int
    page_view_count: int
    download_count: int
    activity_count: int
    last_activity_at: Optional[datetime] = None


class UsageEventRead(ApiModel):
    id: str
    user_id: Optional[str] = None
    username: Optional[str] = None
    event_type: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    path: Optional[str] = None
    details: dict
    created_at: datetime


class UsageAnalyticsSummary(ApiModel):
    date_from: date
    date_to: date
    totals: UsageTotals
    daily: list[DailyUsageMetric]
    users: list[UserUsageMetric]
    recent_events: list[UsageEventRead]
