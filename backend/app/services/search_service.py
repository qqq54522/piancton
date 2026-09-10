from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.schemas.image import SearchResponse
from app.services.ai_service import AiService
from app.services.identity_search_service import IdentitySearchService
from app.services.search_cache import SearchCaches
from app.services.search_service_components import build_search_components
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient
from app.services.viking_knowledge_service_router import VikingKnowledgeServiceRouter
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter


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
            VikingDBKnowledgeRouter | VikingKnowledgeServiceRouter | None
        ) = None,
        vikingdb_skill_backup_enabled: bool = True,
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
                )
            )
        raise RuntimeError("异步上下文请调用 SearchService.search_async")
