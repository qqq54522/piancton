from __future__ import annotations

import json

from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.models.usage import UserUsageEvent
from app.models.user import User
from app.schemas.search_ops import SearchFeedbackRead, SearchInteractionRead, SearchLogRead


def json_list(payload: str) -> list[str]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def feedback_read(event: SearchFeedbackEvent, user: User | None = None) -> SearchFeedbackRead:
    return SearchFeedbackRead(
        id=event.id,
        actor_user_id=event.actor_user_id,
        actor_username=user.username if user else None,
        actor_role=user.role if user else None,
        search_log_id=event.search_log_id,
        keyword=event.keyword,
        feedback_type=event.feedback_type,
        note=event.note,
        result_image_id=event.result_image_id,
        asset_group_id=event.asset_group_id,
        created_at=event.created_at,
    )


def log_read(log: SearchLog, user: User | None = None) -> SearchLogRead:
    return SearchLogRead(
        id=log.id,
        actor_user_id=log.actor_user_id,
        actor_username=user.username if user else None,
        actor_role=user.role if user else None,
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


def interaction_read(event: UserUsageEvent, user: User | None = None) -> SearchInteractionRead:
    details = _json_dict(event.details_json)
    return SearchInteractionRead(
        id=event.id,
        search_log_id=str(details.get("searchLogId") or ""),
        actor_user_id=event.user_id,
        actor_username=user.username if user else None,
        actor_role=user.role if user else None,
        keyword=str(details.get("keyword") or ""),
        action=str(details.get("action") or ""),
        result_image_id=event.target_id,
        asset_group_id=(str(details["assetGroupId"]) if details.get("assetGroupId") else None),
        position=(int(details["position"]) if isinstance(details.get("position"), int) else None),
        source=str(details.get("source") or "search_results"),
        conversation_id=(
            str(details["conversationId"]) if details.get("conversationId") else None
        ),
        created_at=event.created_at,
    )


def _json_dict(payload: str) -> dict:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
