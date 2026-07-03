from __future__ import annotations

import json
import logging

from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.repositories.search_feedback_repository import SearchFeedbackRepository
from app.repositories.search_log_repository import SearchLogRepository
from app.schemas.image import SearchResponse
from app.schemas.search_ops import SearchFeedbackCreate, SearchFeedbackRead
from app.services.search_ops_serializers import feedback_read
from app.services.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


class SearchLogService:
    """Write path for search analytics: persists search logs and feedback.

    Never raises on failure: analytics writes must not break the search or
    feedback request they piggyback on.
    """

    def __init__(self, db):
        self.db = db
        self.logs = SearchLogRepository(db)
        self.feedback = SearchFeedbackRepository(db)
        self.uow = UnitOfWork(db)

    def record_search(
        self,
        *,
        actor_user_id: str | None,
        keyword: str,
        requested_mode: str,
        response: SearchResponse,
        request_id: str | None = None,
    ) -> str | None:
        understanding = response.search_understanding
        top_result_ids = [item.image.id for item in response.results[:8]]
        match_reasons = sorted(
            {
                reason
                for result in response.results[:5]
                for reason in result.match_reasons
            }
        )
        matched_category = None
        if understanding and understanding.matched_level2_categories:
            matched_category = understanding.matched_level2_categories[0].category

        try:
            log = self.logs.add(
                SearchLog(
                    actor_user_id=actor_user_id,
                    keyword=keyword.strip()[:200],
                    requested_mode=requested_mode,
                    served_mode=response.search_mode,
                    fallback=response.fallback,
                    fallback_reason=response.fallback_reason,
                    result_count=len(response.results),
                    normalized_query=(
                        understanding.normalized_query[:200]
                        if understanding and understanding.normalized_query
                        else None
                    ),
                    query_type=understanding.query_type if understanding else None,
                    matched_category=matched_category[:200] if matched_category else None,
                    top_image_ids_json=json.dumps(top_result_ids, ensure_ascii=False),
                    match_reasons_json=json.dumps(match_reasons, ensure_ascii=False),
                    request_id=request_id,
                )
            )
            self.uow.commit()
            return log.id
        except Exception:
            self.uow.rollback()
            logger.warning("failed to record search analytics", exc_info=True)
            return None

    def record_feedback(
        self,
        *,
        actor_user_id: str | None,
        payload: SearchFeedbackCreate,
        request_id: str | None = None,
    ) -> SearchFeedbackRead | None:
        try:
            event = self.feedback.add(
                SearchFeedbackEvent(
                    search_log_id=payload.search_log_id,
                    actor_user_id=actor_user_id,
                    keyword=payload.keyword.strip()[:200],
                    feedback_type=payload.feedback_type,
                    note=(payload.note or "").strip()[:1000] or None,
                    request_id=request_id,
                )
            )
            self.uow.commit()
            return feedback_read(event)
        except Exception:
            self.uow.rollback()
            logger.warning("failed to record search feedback", exc_info=True)
            return None
