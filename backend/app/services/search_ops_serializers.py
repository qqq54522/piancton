from __future__ import annotations

import json

from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.schemas.search_ops import SearchFeedbackRead, SearchLogRead


def json_list(payload: str) -> list[str]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def feedback_read(event: SearchFeedbackEvent) -> SearchFeedbackRead:
    return SearchFeedbackRead(
        id=event.id,
        search_log_id=event.search_log_id,
        keyword=event.keyword,
        feedback_type=event.feedback_type,
        note=event.note,
        result_image_id=event.result_image_id,
        asset_group_id=event.asset_group_id,
        created_at=event.created_at,
    )


def log_read(log: SearchLog) -> SearchLogRead:
    return SearchLogRead(
        id=log.id,
        keyword=log.keyword,
        served_mode=log.served_mode,
        fallback=log.fallback,
        fallback_reason=log.fallback_reason,
        result_count=log.result_count,
        normalized_query=log.normalized_query,
        query_type=log.query_type,
        matched_concept=log.matched_concept,
        top_image_ids=json_list(log.top_image_ids_json),
        top_asset_group_ids=json_list(log.top_asset_group_ids_json),
        match_reasons=json_list(log.match_reasons_json),
        duration_ms=log.duration_ms,
        timed_out=log.timed_out,
        cache_hit=log.cache_hit,
        reranker_used=log.reranker_used,
        degraded_sources=json_list(log.degraded_sources_json),
        created_at=log.created_at,
    )
