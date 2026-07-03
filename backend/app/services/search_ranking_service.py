from __future__ import annotations

from typing import Literal

from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchResponse
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.image_summary_match_service import ImageSummaryMatchService
from app.services.query_expansion_service import unique
from app.services.search_models import SearchHit, StrictSearchPolicy
from app.services.search_response_builder import SearchResponseBuilder
from app.services.search_scorer import SearchScorer
from app.services.semantic_rerank_service import SemanticRerankService
from app.services.semantic_search_clients import RerankerClient
from app.services.strict_intent_filter import StrictIntentFilter


class SearchRankingService:
    def __init__(
        self,
        reranker: RerankerClient | None = None,
        reranker_top_n: int = 50,
        semantic_profile: ImageSemanticProfileService | None = None,
        summary_matcher: ImageSummaryMatchService | None = None,
    ):
        profile = semantic_profile or ImageSemanticProfileService()
        scorer = SearchScorer(profile)
        self.reranker = SemanticRerankService(reranker, reranker_top_n, profile)
        self.strict_filter = StrictIntentFilter(profile)
        self.summary_matcher = summary_matcher
        self.response_builder = SearchResponseBuilder(scorer)

    def merge_hits(
        self,
        primary: list[SearchHit],
        secondary: list[SearchHit],
    ) -> list[SearchHit]:
        merged: dict[str, SearchHit] = {}
        for hit in [*primary, *secondary]:
            existing = merged.get(hit.image.id)
            if existing is None:
                merged[hit.image.id] = hit
                continue
            scores = [
                score for score in (existing.score, hit.score) if score is not None
            ]
            merged[hit.image.id] = SearchHit(
                image=existing.image,
                score=max(scores) if scores else None,
                reasons=tuple(unique([*existing.reasons, *hit.reasons])),
            )
        return list(merged.values())

    def sort_hits(self, hits: list[SearchHit]) -> list[SearchHit]:
        return sorted(
            hits,
            key=lambda hit: hit.score if hit.score is not None else 0.65,
            reverse=True,
        )

    def rerank_hits(
        self,
        keyword: str,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        return self.reranker.rerank_hits(keyword, hits, limit)

    def apply_strict_policy(
        self,
        hits: list[SearchHit],
        policy: StrictSearchPolicy | None,
    ) -> list[SearchHit]:
        if not policy or not policy.enabled:
            return hits
        return self.sort_hits(self.strict_filter.apply(hits, policy))

    def apply_summary_judgement(
        self,
        *,
        keyword: str,
        understanding,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if not self.summary_matcher:
            return hits
        return self.sort_hits(
            self.summary_matcher.judge(
                keyword=keyword,
                understanding=understanding,
                hits=hits,
                limit=limit,
            )
        )

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
        return self.response_builder.build_response(
            keyword=keyword,
            hits=hits,
            search_mode=search_mode,
            fallback=fallback,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
        )
