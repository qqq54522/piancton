from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from app.repositories.image_repository import ImageRepository
from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchBranchStatusRead, SearchResponse
from app.services.ai_service import AiService
from app.services.identity_search_service import IdentitySearchService
from app.services.search_cache import SearchCaches
from app.services.search_knowledge_fallback_router import SearchKnowledgeFallbackRouter
from app.services.search_models import SearchHit
from app.services.search_service_components import build_search_components
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient
from app.services.viking_knowledge_service_router import VikingKnowledgeServiceRouter
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter
from app.services.volc_ai_search_service import VolcAiSearchService

logger = logging.getLogger(__name__)


class SearchService:
    """Thin search facade; Phase 4 orchestration lives in a dedicated coordinator."""

    def __init__(
        self,
        db: Session,
        *,
        search_backend: str = "database",
        meilisearch_url: str = "",
        meilisearch_api_key: str = "",
        meilisearch_index: str = "images",
        search_timeout_seconds: float = 0.2,
        ai_service: AiService | None = None,
        embedding_client: EmbeddingClient | None = None,
        embedding_top_n: int = 100,
        reranker: RerankerClient | None = None,
        reranker_top_n: int = 20,
        total_timeout_seconds: float = 2.5,
        meilisearch_timeout_seconds: float = 0.2,
        embedding_timeout_seconds: float = 0.65,
        understanding_timeout_seconds: float = 0.9,
        system_routing_timeout_seconds: float = 8.0,
        selling_point_timeout_seconds: float = 20.0,
        proof_point_timeout_seconds: float = 20.0,
        candidate_review_timeout_seconds: float = 20.0,
        candidate_review_limit: int = 5,
        understanding_grace_seconds: float = 5.0,
        understanding_retry_attempts: int = 1,
        understanding_retry_backoff_seconds: float = 1.0,
        reranker_timeout_seconds: float = 0.7,
        result_recommendation_timeout_seconds: float = 6.0,
        result_recommendation_limit: int = 12,
        candidate_limit: int = 20,
        cache_ttl_seconds: float = 300.0,
        cache_max_entries: int = 512,
        caches: SearchCaches | None = None,
        vikingdb_knowledge_router: (
            VikingDBKnowledgeRouter
            | VikingKnowledgeServiceRouter
            | SearchKnowledgeFallbackRouter
            | None
        ) = None,
        vikingdb_skill_backup_enabled: bool = True,
        ai_search: VolcAiSearchService | None = None,
    ):
        components = build_search_components(
            db,
            search_backend=search_backend,
            meilisearch_url=meilisearch_url,
            meilisearch_api_key=meilisearch_api_key,
            meilisearch_index=meilisearch_index,
            search_timeout_seconds=search_timeout_seconds,
            ai_service=ai_service,
            embedding_client=embedding_client,
            embedding_top_n=embedding_top_n,
            reranker=reranker,
            reranker_top_n=reranker_top_n,
            total_timeout_seconds=total_timeout_seconds,
            meilisearch_timeout_seconds=meilisearch_timeout_seconds,
            embedding_timeout_seconds=embedding_timeout_seconds,
            understanding_timeout_seconds=understanding_timeout_seconds,
            system_routing_timeout_seconds=system_routing_timeout_seconds,
            selling_point_timeout_seconds=selling_point_timeout_seconds,
            proof_point_timeout_seconds=proof_point_timeout_seconds,
            candidate_review_timeout_seconds=candidate_review_timeout_seconds,
            candidate_review_limit=candidate_review_limit,
            understanding_grace_seconds=understanding_grace_seconds,
            understanding_retry_attempts=understanding_retry_attempts,
            understanding_retry_backoff_seconds=understanding_retry_backoff_seconds,
            reranker_timeout_seconds=reranker_timeout_seconds,
            result_recommendation_timeout_seconds=result_recommendation_timeout_seconds,
            result_recommendation_limit=result_recommendation_limit,
            candidate_limit=candidate_limit,
            cache_ttl_seconds=cache_ttl_seconds,
            cache_max_entries=cache_max_entries,
            caches=caches,
            vikingdb_knowledge_router=vikingdb_knowledge_router,
            vikingdb_skill_backup_enabled=vikingdb_skill_backup_enabled,
        )
        self.query_understanding = components.query_understanding
        self.orchestrator = components.orchestrator
        self.identity_search = IdentitySearchService(db)
        self.images = ImageRepository(db)
        self.ai_search = ai_search

    async def search_async(
        self,
        keyword: str,
        limit: int,
        system_code: str | None = None,
        concept_code: str | None = None,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
        user_id: str = "",
    ) -> SearchResponse:
        if (
            self.ai_search is not None
            and not any([system_code, concept_code, proof_point_code, evidence_point_code])
        ):
            understanding_task = asyncio.create_task(
                self.orchestrator.understand_for_external_results(keyword)
            )
            # Let the external understanding branch dispatch its network work
            # before the synchronous AI Search adapter hydrates result images.
            await asyncio.sleep(0)
            ai_response = self.ai_search.search(keyword, limit=limit, user_id=user_id)
            if ai_response is not None and not ai_response.fallback:
                try:
                    understanding = await understanding_task
                    ai_response = self._govern_external_response(
                        keyword=keyword,
                        response=ai_response,
                        understanding=understanding,
                        limit=limit,
                    )
                    ai_response.route_explanation = _understanding_route_explanation(
                        understanding
                    )
                    route_explanation = (
                        await self.orchestrator.explain_external_result_route(
                            keyword=keyword,
                            understanding=understanding,
                            result_count=len(ai_response.results),
                        )
                    )
                    ai_response.route_explanation = (
                        route_explanation.value
                        or _understanding_route_explanation(understanding)
                    )
                    if ai_response.search_diagnostics is not None:
                        ai_response.search_diagnostics.branches.append(
                            SearchBranchStatusRead.model_validate(
                                route_explanation.diagnostic,
                                from_attributes=True,
                            )
                        )
                        ai_response.search_diagnostics.total_duration_ms += (
                            route_explanation.diagnostic.duration_ms
                        )
                except Exception:
                    logger.warning(
                        "AI Search results returned without selling-point explanation",
                        exc_info=True,
                    )
                return ai_response
            understanding_task.cancel()
            try:
                await understanding_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.warning(
                    "AI Search explanation task failed during local fallback",
                    exc_info=True,
                )
        return await self.orchestrator.search(
            keyword,
            limit,
            system_code,
            concept_code,
            proof_point_code,
            evidence_point_code,
        )

    def _govern_external_response(
        self,
        *,
        keyword: str,
        response: SearchResponse,
        understanding: SearchUnderstanding | None,
        limit: int,
    ) -> SearchResponse:
        response.search_understanding = understanding
        images = self.images.get_many_by_ids(
            [item.image.id for item in response.results]
        )
        images_by_id = {image.id: image for image in images}
        hits = [
            SearchHit(
                image=images_by_id[item.image.id],
                score=item.final_score,
                reasons=tuple(item.match_reasons),
            )
            for item in response.results
            if item.image.id in images_by_id
        ]
        outcome = self.orchestrator.route_external_results(
            keyword=keyword,
            understanding=understanding,
            hits=hits,
        )
        if not outcome.active_matches:
            return response

        governed = self.orchestrator.ranking.build_response(
            keyword=keyword,
            hits=outcome.hits[:limit],
            search_mode=response.search_mode,
            fallback=False,
            search_understanding=understanding,
            search_diagnostics=response.search_diagnostics,
            query_concept_matches=list(outcome.active_matches),
        )
        concept_names = "、".join(item.name for item in outcome.active_matches)
        if governed.results:
            governed.match_summary = (
                f"已识别卖点：{concept_names}；"
                f"找到 {len(governed.results)} 张已确认匹配的图片"
            )
        else:
            governed.match_summary = (
                f"已识别卖点：{concept_names}，"
                "但素材库暂未找到已确认匹配的图片"
            )
        return governed

    def query_recommendations(
        self,
        *,
        user_id: str = "",
        limit: int = 8,
    ) -> list[str]:
        if self.ai_search is None:
            return []
        return self.ai_search.query_recommendations(user_id=user_id, limit=limit)

    def query_completions(self, query: str, *, limit: int = 8) -> list[str]:
        if self.ai_search is None:
            return []
        return self.ai_search.query_completions(query, limit=limit)

    def search(
        self,
        keyword: str,
        limit: int,
        system_code: str | None = None,
        concept_code: str | None = None,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
    ) -> SearchResponse:
        """Synchronous entry point for CLI scripts and non-async callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.search_async(
                    keyword,
                    limit,
                    system_code,
                    concept_code,
                    proof_point_code,
                    evidence_point_code,
                    user_id="",
                )
            )
        raise RuntimeError("异步上下文请调用 SearchService.search_async")


def _understanding_route_explanation(
    understanding: SearchUnderstanding | None,
) -> str | None:
    if understanding is None:
        return None
    matches = [
        item
        for item in understanding.matched_business_concepts
        if item.relation == "direct"
    ]
    if not matches:
        return None
    names = [item.concept.rsplit(">", 1)[-1].strip() for item in matches]
    reasons = list(
        dict.fromkeys(item.reason.strip() for item in matches if item.reason.strip())
    )
    prefix = (
        f"本次需求同时涉及{'、'.join(names)}"
        if len(names) > 1
        else f"本次需求命中{names[0]}"
    )
    detail = f"：{'；'.join(reasons[:3])}" if reasons else ""
    return f"{prefix}{detail}。"[:500]
