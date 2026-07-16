from __future__ import annotations

from typing import Literal

from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchDiagnosticsRead, SearchResponse
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_concept_routing_service import SearchConceptRoutingService
from app.services.search_models import (
    ConceptMatch,
    ConceptRouteOutcome,
    RerankOutcome,
    SearchHit,
)
from app.services.search_response_builder import SearchResponseBuilder
from app.services.search_scorer import SearchScorer
from app.services.semantic_rerank_service import SemanticRerankService
from app.services.semantic_search_clients import RerankerClient


class SearchRankingService:
    def __init__(
        self,
        reranker: RerankerClient | None = None,
        reranker_top_n: int = 50,
        semantic_profile: ImageSemanticProfileService | None = None,
    ):
        profile = semantic_profile or ImageSemanticProfileService()
        scorer = SearchScorer()
        self.reranker = SemanticRerankService(reranker, reranker_top_n, profile)
        self.concept_routing = SearchConceptRoutingService()
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

    def fuse_sources(self, sources: list[list[SearchHit]]) -> list[SearchHit]:
        merged: dict[str, SearchHit] = {}
        source_counts: dict[str, int] = {}
        for hits in sources:
            seen_in_source: set[str] = set()
            for hit in hits:
                image_id = hit.image.id
                existing = merged.get(image_id)
                if existing is None:
                    merged[image_id] = hit
                else:
                    scores = [
                        value
                        for value in (existing.score, hit.score)
                        if value is not None
                    ]
                    merged[image_id] = SearchHit(
                        image=existing.image,
                        score=max(scores) if scores else None,
                        reasons=tuple(unique([*existing.reasons, *hit.reasons])),
                    )
                if image_id not in seen_in_source:
                    source_counts[image_id] = source_counts.get(image_id, 0) + 1
                    seen_in_source.add(image_id)

        fused: list[SearchHit] = []
        for image_id, hit in merged.items():
            source_count = source_counts.get(image_id, 1)
            base_score = hit.score if hit.score is not None else 0.65
            boost = min(0.06, max(0, source_count - 1) * 0.02)
            reasons = list(hit.reasons)
            if source_count > 1:
                reasons.append(f"多路召回一致：{source_count} 路")
            fused.append(
                SearchHit(
                    image=hit.image,
                    score=min(1.0, base_score + boost),
                    reasons=tuple(unique(reasons)),
                )
            )
        return self.sort_hits(fused)

    def collapse_asset_groups(self, hits: list[SearchHit]) -> list[SearchHit]:
        return self.response_builder.deduplicate_asset_groups(hits)

    def route_confirmed_concepts(
        self,
        hits: list[SearchHit],
        concept_matches: list[ConceptMatch],
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
    ) -> ConceptRouteOutcome:
        return self.concept_routing.route(
            hits,
            concept_matches,
            keyword=keyword,
            understanding=understanding,
        )

    def rerank_hits(
        self,
        keyword: str,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        return self.reranker.rerank_hits(keyword, hits, limit)

    async def rerank_hits_async(
        self,
        keyword: str,
        hits: list[SearchHit],
    ) -> RerankOutcome:
        return await self.reranker.rerank_hits_async(keyword, hits)

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
        query_concept_matches: list[ConceptMatch] | None = None,
    ) -> SearchResponse:
        return self.response_builder.build_response(
            keyword=keyword,
            hits=hits,
            search_mode=search_mode,
            fallback=fallback,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
            search_diagnostics=search_diagnostics,
            query_concept_matches=query_concept_matches,
        )
