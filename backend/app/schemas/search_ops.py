from datetime import datetime
from typing import Literal, Optional

from app.schemas.base import ApiModel


class SearchMetricItem(ApiModel):
    label: str
    count: int


class SearchLogRead(ApiModel):
    id: str
    keyword: str
    requested_mode: str
    served_mode: str
    fallback: bool
    fallback_reason: Optional[str] = None
    result_count: int
    normalized_query: Optional[str] = None
    query_type: Optional[str] = None
    matched_category: Optional[str] = None
    top_image_ids: list[str]
    match_reasons: list[str]
    created_at: datetime


class SearchFeedbackCreate(ApiModel):
    search_log_id: Optional[str] = None
    keyword: str
    feedback_type: Literal[
        "not_relevant",
        "too_few_results",
        "need_different_style",
        "asset_request",
    ]
    note: Optional[str] = None


class SearchFeedbackRead(ApiModel):
    id: str
    search_log_id: Optional[str] = None
    keyword: str
    feedback_type: str
    note: Optional[str] = None
    created_at: datetime


class SearchOpsIssueRead(ApiModel):
    id: str
    keyword: str
    issue_type: str
    severity: Literal["high", "medium", "low"]
    source: str
    count: int
    reason: str
    suggested_action: str
    latest_at: datetime


class AiReviewQueueItem(ApiModel):
    id: str
    image_id: str
    image_title: str
    thumbnail_url: str
    label_code: str
    label_name: str
    system_name: Optional[str] = None
    role: str
    confidence: Optional[float] = None
    evidence_level: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime


class LabelHealthItem(ApiModel):
    tag_id: str
    label_code: Optional[str] = None
    label_name: str
    system_name: Optional[str] = None
    image_count: int
    manual_count: int
    ai_pending_count: int
    ai_accepted_count: int
    ai_rejected_count: int
    search_count: int
    health_level: Literal["healthy", "needs_assets", "needs_review", "watch"]
    recommendation: str


class AssetGapItem(ApiModel):
    keyword: str
    demand_count: int
    suggested_label: Optional[str] = None
    reason: str
    source: str


class SearchOpsSummary(ApiModel):
    total_searches: int
    zero_result_count: int
    fallback_count: int
    ai_understood_count: int
    smart_search_count: int
    precise_search_count: int
    top_queries: list[SearchMetricItem]
    zero_result_queries: list[SearchMetricItem]
    top_normalized_queries: list[SearchMetricItem]
    top_matched_categories: list[SearchMetricItem]
    feedback_count: int
    feedback_by_type: list[SearchMetricItem]
    feedback_queries: list[SearchMetricItem]
    recent_feedback: list[SearchFeedbackRead]
    recent_logs: list[SearchLogRead]
    search_issues: list[SearchOpsIssueRead]
    ai_review_queue: list[AiReviewQueueItem]
    label_health: list[LabelHealthItem]
    asset_gaps: list[AssetGapItem]
