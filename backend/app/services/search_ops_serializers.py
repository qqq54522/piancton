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
        created_at=event.created_at,
    )


def log_read(log: SearchLog) -> SearchLogRead:
    return SearchLogRead(
        id=log.id,
        keyword=log.keyword,
        requested_mode=log.requested_mode,
        served_mode=log.served_mode,
        fallback=log.fallback,
        fallback_reason=log.fallback_reason,
        result_count=log.result_count,
        normalized_query=log.normalized_query,
        query_type=log.query_type,
        matched_category=log.matched_category,
        top_image_ids=json_list(log.top_image_ids_json),
        match_reasons=json_list(log.match_reasons_json),
        created_at=log.created_at,
    )
