from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.image_repository import ImageRepository
from app.schemas.image import SearchDiagnosticsRead, SearchResponse
from app.services.search_models import SearchBranchDiagnostic, SearchHit
from app.services.search_response_builder import SearchResponseBuilder
from app.services.search_scorer import SearchScorer
from app.services.volc_ai_search_client import (
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

logger = logging.getLogger(__name__)


class VolcAiSearchService:
    """Homepage search adapter backed by Volcengine AI Search."""

    def __init__(
        self,
        db: Session,
        client: VolcAiSearchClient,
        *,
        enabled: bool,
        page_size: int,
    ):
        self.images = ImageRepository(db)
        self.client = client
        self.enabled = enabled
        self.page_size = max(1, min(page_size, 100))
        self.response_builder = SearchResponseBuilder(SearchScorer())

    @property
    def configured(self) -> bool:
        return self.enabled and self.client.search_configured

    def search(
        self,
        keyword: str,
        *,
        limit: int,
        user_id: str = "",
    ) -> SearchResponse | None:
        if not keyword.strip():
            return None
        if not self.configured:
            return None
        started = time.monotonic()
        try:
            result = self.client.search(
                keyword,
                page_size=max(limit, self.page_size),
                user_id=user_id,
            )
        except VolcAiSearchClientError as exc:
            logger.warning("AI Search homepage search failed", exc_info=True)
            diagnostic = _diagnostic(
                started,
                status="failed",
                detail=str(exc),
                result_count=0,
            )
            return _fallback_response(keyword, diagnostic)

        candidates = _extract_image_candidates(result.matches)
        images = self.images.get_many_by_ids([item.image_id for item in candidates])
        found_ids = {image.id for image in images}
        missing_identity_codes = [
            item.identity_code
            for item in candidates
            if item.image_id not in found_ids and item.identity_code
        ]
        images.extend(self.images.get_many_by_identity_codes(missing_identity_codes))
        score_by_id = {item.image_id: item.score for item in candidates}
        score_by_code = {
            item.identity_code: item.score
            for item in candidates
            if item.identity_code
        }
        hits = [
            SearchHit(
                image=image,
                score=score_by_id.get(
                    image.id,
                    score_by_code.get(image.identity_code or "", 0.75),
                ),
                reasons=("火山 AI Search 召回",),
            )
            for image in images
        ]
        response = self.response_builder.build_response(
            keyword=keyword,
            hits=hits[:limit],
            search_mode="meilisearch",
            fallback=False,
        )
        diagnostic = _diagnostic(
            started,
            status="ok",
            detail="首页搜索优先使用火山 AI Search",
            result_count=len(hits),
        )
        response.search_diagnostics = SearchDiagnosticsRead(
            total_duration_ms=diagnostic.duration_ms,
            timed_out=False,
            reranker_used=False,
            cache_hit=False,
            degraded_sources=[],
            branches=[
                {
                    "source": diagnostic.source,
                    "status": diagnostic.status,
                    "durationMs": diagnostic.duration_ms,
                    "resultCount": diagnostic.result_count,
                    "cacheHit": False,
                    "detail": diagnostic.detail,
                    "attempts": [],
                }
            ],
        )
        response.match_summary = f"找到 {len(response.results)} 张与“{keyword}”相关的图片"
        return response

    def query_recommendations(
        self,
        *,
        user_id: str = "",
        limit: int = 8,
    ) -> list[str]:
        if not self.configured:
            return []
        try:
            return self.client.query_recommendations(
                user_id=user_id,
                page_size=max(1, min(limit, 20)),
            )
        except VolcAiSearchClientError:
            logger.warning("AI Search query recommendation failed", exc_info=True)
            return []


def _fallback_response(keyword: str, diagnostic: SearchBranchDiagnostic) -> SearchResponse:
    return SearchResponse(
        results=[],
        has_more=False,
        search_mode="meilisearch",
        fallback=True,
        fallback_reason=f"AI Search 不可用（{diagnostic.detail}），已回退本地搜索",
        search_diagnostics=SearchDiagnosticsRead(
            total_duration_ms=diagnostic.duration_ms,
            timed_out=False,
            reranker_used=False,
            cache_hit=False,
            degraded_sources=["volc_ai_search"],
            branches=[
                {
                    "source": diagnostic.source,
                    "status": diagnostic.status,
                    "durationMs": diagnostic.duration_ms,
                    "resultCount": diagnostic.result_count,
                    "cacheHit": False,
                    "detail": diagnostic.detail,
                    "attempts": [],
                }
            ],
        ),
        match_summary=f"火山 AI Search 暂不可用，正在回退本地搜索“{keyword}”",
    )


def _diagnostic(
    started: float,
    *,
    status: str,
    detail: str | None,
    result_count: int,
) -> SearchBranchDiagnostic:
    return SearchBranchDiagnostic(
        source="volc_ai_search",
        status=status,  # type: ignore[arg-type]
        duration_ms=int((time.monotonic() - started) * 1000),
        result_count=result_count,
        detail=detail,
    )


class _Candidate:
    def __init__(self, image_id: str, identity_code: str, score: float):
        self.image_id = image_id
        self.identity_code = identity_code
        self.score = score


def _extract_image_candidates(matches: list[dict[str, Any]]) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for item in matches:
        record = _record_payload(item)
        image_id = (
            _string_value(record, "image_id")
            or _string_value(record, "_id")
            or _string_value(record, "id")
        )
        identity_code = _string_value(record, "identity_code")
        if not image_id and not identity_code:
            continue
        candidates.append(
            _Candidate(
                image_id=image_id,
                identity_code=identity_code,
                score=_score(item),
            )
        )
    return candidates


def _record_payload(item: dict[str, Any]) -> dict[str, Any]:
    for key in ("fields", "field", "item", "doc", "document", "source", "_source"):
        value = item.get(key)
        if isinstance(value, dict):
            merged = dict(value)
            for fallback_key in ("_id", "id", "image_id", "score"):
                if fallback_key in item and fallback_key not in merged:
                    merged[fallback_key] = item[fallback_key]
            return merged
    return item


def _string_value(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _score(item: dict[str, Any]) -> float:
    for key in ("score", "_score", "similarity", "rank_score"):
        value = item.get(key)
        if isinstance(value, (int, float)):
            return max(0.0, min(float(value), 1.0))
        if isinstance(value, str):
            try:
                return max(0.0, min(float(value), 1.0))
            except ValueError:
                continue
    return 0.78
