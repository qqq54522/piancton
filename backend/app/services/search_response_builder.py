from __future__ import annotations

from typing import Literal

from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchDiagnosticsRead, SearchResponse
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
        search_diagnostics: SearchDiagnosticsRead | None = None,
    ) -> SearchResponse:
        needle = keyword.strip().lower()
        hits = self.deduplicate_asset_groups(hits)
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
            search_diagnostics=search_diagnostics,
            match_summary=f"找到 {len(results)} 张与“{keyword}”相关的图片",
        )

    def deduplicate_asset_groups(self, hits: list[SearchHit]) -> list[SearchHit]:
        """Keep one current representative per group without changing recall orchestration."""
        selected: dict[str, SearchHit] = {}
        for hit in hits:
            key = hit.image.asset_group_id or hit.image.id
            current = selected.get(key)
            if current is None:
                selected[key] = hit
                continue
            current_is_primary = current.image.id == (
                current.image.asset_group.primary_image_id
                if current.image.asset_group else current.image.id
            )
            candidate_is_primary = hit.image.id == (
                hit.image.asset_group.primary_image_id
                if hit.image.asset_group else hit.image.id
            )
            best_score = max(
                current.score if current.score is not None else 0.65,
                hit.score if hit.score is not None else 0.65,
            )
            reasons = tuple(dict.fromkeys([*current.reasons, *hit.reasons]))
            representative = current
            if candidate_is_primary and not current_is_primary:
                representative = hit
            selected[key] = SearchHit(
                image=representative.image,
                score=best_score,
                reasons=reasons,
            )
        return list(selected.values())
