from datetime import datetime
from typing import Literal, Optional

from app.schemas.base import ApiModel


class SearchMetricItem(ApiModel):
    label: str
    count: int


class SearchLogRead(ApiModel):
    id: str
    actor_user_id: Optional[str] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    keyword: str
    served_mode: str
    fallback: bool
    fallback_reason: Optional[str] = None
    result_count: int
    normalized_query: Optional[str] = None
    query_type: Optional[str] = None
    matched_concept: Optional[str] = None
    top_image_ids: list[str]
    top_asset_group_ids: list[str]
    match_reasons: list[str]
    duration_ms: Optional[int] = None
    timed_out: bool = False
    cache_hit: bool = False
    reranker_used: bool = False
    degraded_sources: list[str]
    created_at: datetime


class SearchFeedbackCreate(ApiModel):
    search_log_id: Optional[str] = None
    keyword: str
    feedback_type: Literal[
        "relevant",
        "not_relevant",
        "too_few_results",
        "need_different_style",
        "right_business_wrong_visual",
        "right_visual_wrong_business",
        "wrong_version",
        "asset_request",
    ]
    note: Optional[str] = None
    result_image_id: Optional[str] = None
    asset_group_id: Optional[str] = None


class SearchFeedbackRead(ApiModel):
    id: str
    actor_user_id: Optional[str] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    search_log_id: Optional[str] = None
    keyword: str
    feedback_type: str
    note: Optional[str] = None
    result_image_id: Optional[str] = None
    asset_group_id: Optional[str] = None
    created_at: datetime


class SearchInteractionRead(ApiModel):
    id: str
    search_log_id: str
    actor_user_id: Optional[str] = None
    actor_username: Optional[str] = None
    actor_role: Optional[str] = None
    keyword: str
    action: str
    result_image_id: Optional[str] = None
    asset_group_id: Optional[str] = None
    position: Optional[int] = None
    source: str = "search_results"
    conversation_id: Optional[str] = None
    created_at: datetime


class SearchActivitySummary(ApiModel):
    total_searches: int
    search_user_count: int
    positive_feedback_count: int
    negative_feedback_count: int
    feedback_response_rate: float
    interaction_count: int
    top_queries: list[SearchMetricItem]
    recent_feedback: list[SearchFeedbackRead]
    recent_logs: list[SearchLogRead]
    recent_interactions: list[SearchInteractionRead]


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


class AiConceptReviewQueueItem(ApiModel):
    id: str
    asset_group_id: str
    image_id: str
    image_title: str
    thumbnail_url: str
    concept_code: str
    concept_name: str
    system_names: list[str]
    relation_role: str
    confidence: Optional[float] = None
    reason: Optional[str] = None
    created_at: datetime


class ConceptHealthItem(ApiModel):
    concept_id: str
    concept_code: str
    concept_name: str
    system_names: list[str]
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
    suggested_concept: Optional[str] = None
    reason: str
    source: str


class AssetOperationsOverview(ApiModel):
    asset_group_count: int
    image_count: int
    current_image_count: int
    missing_source_link_count: int
    missing_source_link_rate: float
    single_version_group_count: int
    missing_business_relation_count: int
    missing_search_phrase_count: int
    missing_style_count: int
    unset_scene_count: int
    missing_channel_count: int
    total_download_count: int
    unused_asset_group_count: int


class AssetOpsIssueRead(ApiModel):
    id: str
    asset_group_id: str
    title: str
    primary_image_id: Optional[str] = None
    issue_type: str
    severity: Literal["high", "medium", "low"]
    message: str
    suggested_action: str
    updated_at: datetime


class SourceLinkRecentItem(ApiModel):
    id: str
    asset_group_id: str
    asset_group_title: str
    primary_image_id: Optional[str] = None
    label: str
    link_type: str
    url: str
    review_status: Literal["ok", "stale"]
    updated_at: datetime


class SourceLinkHealth(ApiModel):
    total_links: int
    groups_with_source_links: int
    groups_without_source_links: int
    stale_link_count: int
    groups_requiring_review: int
    link_type_counts: list[SearchMetricItem]
    recent_links: list[SourceLinkRecentItem]


class SearchPerformanceSummary(ApiModel):
    sample_count: int
    average_duration_ms: float
    p50_duration_ms: int
    p95_duration_ms: int
    p99_duration_ms: int
    slow_search_count: int
    slow_search_rate: float
    timeout_count: int
    fallback_count: int
    cache_hit_count: int
    cache_hit_rate: float
    reranker_used_count: int
    ai_understood_count: int
    model_work_unit_count: int
    model_work_unit_rate: float
    recent_slow_logs: list[SearchLogRead]


class SearchOpsSummary(ApiModel):
    total_searches: int
    search_user_count: int
    zero_result_count: int
    fallback_count: int
    timed_out_count: int
    cache_hit_count: int
    reranker_used_count: int
    average_duration_ms: float
    p95_duration_ms: int
    ai_understood_count: int
    top_queries: list[SearchMetricItem]
    zero_result_queries: list[SearchMetricItem]
    top_normalized_queries: list[SearchMetricItem]
    top_matched_concepts: list[SearchMetricItem]
    feedback_count: int
    positive_feedback_count: int
    negative_feedback_count: int
    feedback_response_rate: float
    interaction_count: int
    feedback_by_type: list[SearchMetricItem]
    feedback_queries: list[SearchMetricItem]
    recent_feedback: list[SearchFeedbackRead]
    recent_logs: list[SearchLogRead]
    recent_interactions: list[SearchInteractionRead]
    search_issues: list[SearchOpsIssueRead]
    ai_review_queue: list[AiConceptReviewQueueItem]
    concept_health: list[ConceptHealthItem]
    asset_gaps: list[AssetGapItem]
    asset_operations: AssetOperationsOverview
    asset_ops_issues: list[AssetOpsIssueRead]
    source_link_health: SourceLinkHealth
    search_performance: SearchPerformanceSummary
