from __future__ import annotations

from typing import Literal

from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchResponse
from app.services.search_models import SearchHit
from app.services.search_scorer import SearchScorer


class SearchResponseBuilder:
    def __init__(self, scorer: SearchScorer | None = None):
        self.scorer = scorer or SearchScorer()

    def build_response(
        self,
        *,
        keyword: str,
        hits: list[SearchHit],
        search_mode: Literal["fuzzy", "meilisearch"],
        fallback: bool,
        fallback_reason: str | None = None,
        search_understanding: SearchUnderstanding | None = None,
    ) -> SearchResponse:
        needle = keyword.strip().lower()
        results = [
            self.scorer.build_scored_image(
                hit.image,
                needle,
                hit.score,
                list(hit.reasons),
            )
            for hit in hits
        ]
        return SearchResponse(
            results=results,
            search_mode=search_mode,
            fallback=fallback,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
            match_summary=f"找到 {len(results)} 张与“{keyword}”相关的图片",
        )
