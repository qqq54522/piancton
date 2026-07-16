from __future__ import annotations

from typing import Literal

from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchDiagnosticsRead, SearchResponse
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, RerankOutcome, SearchHit
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

    def prioritize_confirmed_concepts(
        self,
        hits: list[SearchHit],
        concept_matches: list[ConceptMatch],
        *,
        confidence: float,
    ) -> list[SearchHit]:
        """Keep high-confidence intent and confirmed asset relations above weak signals."""
        matched_ids = {
            item.concept_id
            for item in concept_matches
            if item.score >= 0.84
        }
        if confidence < 0.85 or not matched_ids:
            return hits

        prioritized: list[SearchHit] = []
        for hit in hits:
            links = hit.image.asset_group.concept_links if hit.image.asset_group else []
            if any(
                link.concept_id in matched_ids
                and link.review_status == "accepted"
                and link.relation_role == "excludes"
                for link in links
            ):
                continue
            accepted = [
                link
                for link in links
                if link.concept_id in matched_ids
                and link.review_status == "accepted"
                and link.relation_role != "excludes"
            ]
            base_score = hit.score if hit.score is not None else 0.65
            score = min(base_score, 0.82)
            reason = "高置信卖点意图：保留画面/话术兜底"
            manual = [
                link for link in accepted if link.origin in {"manual", "migrated"}
            ]
            roles = {link.relation_role for link in manual}
            if "expresses" in roles:
                score = 0.96 + min(1.0, base_score) * 0.04
                reason = "高置信卖点意图命中人工确认的主要表达关系"
            elif "supports" in roles:
                score = 0.90 + min(1.0, base_score) * 0.05
                reason = "高置信卖点意图命中人工确认的可以支持关系"
            elif manual:
                score = 0.84 + min(1.0, base_score) * 0.04
                reason = "高置信卖点意图命中人工确认的画面关联关系"
            elif accepted:
                score = 0.84 + min(1.0, base_score) * 0.05
                reason = "高置信卖点意图命中已采纳的 AI 关系"
            prioritized.append(
                SearchHit(
                    image=hit.image,
                    score=min(1.0, score),
                    reasons=tuple(unique([*hit.reasons, reason])),
                )
            )
        return self.sort_hits(prioritized)

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
