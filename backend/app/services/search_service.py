from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.image import SearchResponse
from app.services.ai_service import AiService
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.embedding_recall_service import EmbeddingRecallService
from app.services.intent_catalog_service import IntentCatalogService
from app.services.meilisearch_recall_service import MeilisearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_profile_service import QueryProfileService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_cache import SearchCaches, build_search_caches
from app.services.search_external_branches import SearchExternalBranches
from app.services.search_orchestrator import AsyncSearchOrchestrator
from app.services.search_ranking_service import SearchRankingService
from app.services.search_rerank_coordinator import SearchRerankCoordinator
from app.services.search_system_filter import SearchSystemFilter
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient


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
        understanding_grace_seconds: float = 5.0,
        understanding_retry_attempts: int = 1,
        understanding_retry_backoff_seconds: float = 1.0,
        reranker_timeout_seconds: float = 0.7,
        candidate_limit: int = 20,
        cache_ttl_seconds: float = 300.0,
        cache_max_entries: int = 512,
        caches: SearchCaches | None = None,
    ):
        images = ImageRepository(db)
        concepts = BusinessConceptRepository(db)
        self.expansion = QueryExpansionService()
        self.query_understanding = QueryUnderstandingService(
            ai_service,
            runtime_catalog=IntentCatalogService(concepts).runtime_catalog(),
        )
        self.ranking = SearchRankingService(
            reranker,
            min(max(1, reranker_top_n), max(1, candidate_limit)),
        )
        self.database_recall = DatabaseSearchRecallService(images)
        self.concept_recall = ConceptSearchRecallService(concepts, images)
        self.embedding_recall = EmbeddingRecallService(images, embedding_client)
        self.meilisearch_recall = MeilisearchRecallService(
            images,
            url=meilisearch_url,
            api_key=meilisearch_api_key,
            index=meilisearch_index,
            timeout_seconds=min(search_timeout_seconds, meilisearch_timeout_seconds),
        )
        search_caches = caches or build_search_caches(
            ttl_seconds=cache_ttl_seconds,
            max_entries=cache_max_entries,
        )
        external_branches = SearchExternalBranches(
            search_backend=search_backend,
            meilisearch=self.meilisearch_recall,
            embedding=self.embedding_recall,
            understanding=self.query_understanding,
            caches=search_caches,
            meilisearch_timeout_seconds=meilisearch_timeout_seconds,
            embedding_timeout_seconds=embedding_timeout_seconds,
            understanding_timeout_seconds=understanding_timeout_seconds,
            system_routing_timeout_seconds=system_routing_timeout_seconds,
            selling_point_timeout_seconds=selling_point_timeout_seconds,
            understanding_grace_seconds=understanding_grace_seconds,
            understanding_retry_attempts=understanding_retry_attempts,
            understanding_retry_backoff_seconds=understanding_retry_backoff_seconds,
            embedding_top_n=embedding_top_n,
            candidate_limit=candidate_limit,
        )
        rerank_coordinator = SearchRerankCoordinator(
            self.ranking,
            total_timeout_seconds=total_timeout_seconds,
            reranker_timeout_seconds=reranker_timeout_seconds,
        )
        self.orchestrator = AsyncSearchOrchestrator(
            expansion=self.expansion,
            query_understanding=self.query_understanding,
            query_profile=QueryProfileService(),
            concept_recall=self.concept_recall,
            database_recall=self.database_recall,
            ranking=self.ranking,
            external_branches=external_branches,
            rerank_coordinator=rerank_coordinator,
            system_filter=SearchSystemFilter(),
            candidate_limit=candidate_limit,
        )

    async def search_async(
        self,
        keyword: str,
        limit: int,
        system_code: str | None = None,
        concept_code: str | None = None,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
    ) -> SearchResponse:
        return await self.orchestrator.search(
            keyword,
            limit,
            system_code,
            concept_code,
            proof_point_code,
            evidence_point_code,
        )

    def search(
        self,
        keyword: str,
        limit: int,
        system_code: str | None = None,
        concept_code: str | None = None,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
    ) -> SearchResponse:
        """Compatibility wrapper for scripts and synchronous service tests."""
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
                )
            )
        raise RuntimeError("异步上下文请调用 SearchService.search_async")
