from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.image_repository import ImageRepository
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


@dataclass
class SearchServiceComponents:
    orchestrator: AsyncSearchOrchestrator
    query_understanding: QueryUnderstandingService


def build_search_components(
    db: Session,
    *,
    search_backend: str,
    meilisearch_url: str,
    meilisearch_api_key: str,
    meilisearch_index: str,
    search_timeout_seconds: float,
    ai_service: AiService | None,
    embedding_client: EmbeddingClient | None,
    embedding_top_n: int,
    reranker: RerankerClient | None,
    reranker_top_n: int,
    total_timeout_seconds: float,
    meilisearch_timeout_seconds: float,
    embedding_timeout_seconds: float,
    understanding_timeout_seconds: float,
    system_routing_timeout_seconds: float,
    selling_point_timeout_seconds: float,
    proof_point_timeout_seconds: float,
    candidate_review_timeout_seconds: float,
    candidate_review_limit: int,
    understanding_grace_seconds: float,
    understanding_retry_attempts: int,
    understanding_retry_backoff_seconds: float,
    reranker_timeout_seconds: float,
    candidate_limit: int,
    cache_ttl_seconds: float,
    cache_max_entries: int,
    caches: SearchCaches | None,
) -> SearchServiceComponents:
    images = ImageRepository(db)
    concepts = BusinessConceptRepository(db)
    query_understanding = QueryUnderstandingService(
        ai_service,
        runtime_catalog=IntentCatalogService(concepts).runtime_catalog(),
    )
    ranking = SearchRankingService(
        reranker,
        min(max(1, reranker_top_n), max(1, candidate_limit)),
    )
    external_branches = SearchExternalBranches(
        search_backend=search_backend,
        meilisearch=MeilisearchRecallService(
            images,
            url=meilisearch_url,
            api_key=meilisearch_api_key,
            index=meilisearch_index,
            timeout_seconds=min(search_timeout_seconds, meilisearch_timeout_seconds),
        ),
        embedding=EmbeddingRecallService(images, embedding_client),
        understanding=query_understanding,
        caches=caches
        or build_search_caches(
            ttl_seconds=cache_ttl_seconds,
            max_entries=cache_max_entries,
        ),
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
        embedding_top_n=embedding_top_n,
        candidate_limit=candidate_limit,
    )
    return SearchServiceComponents(
        orchestrator=AsyncSearchOrchestrator(
            expansion=QueryExpansionService(),
            query_understanding=query_understanding,
            query_profile=QueryProfileService(),
            concept_recall=ConceptSearchRecallService(concepts, images),
            database_recall=DatabaseSearchRecallService(images),
            ranking=ranking,
            external_branches=external_branches,
            rerank_coordinator=SearchRerankCoordinator(
                ranking,
                total_timeout_seconds=total_timeout_seconds,
                reranker_timeout_seconds=reranker_timeout_seconds,
            ),
            system_filter=SearchSystemFilter(),
            candidate_limit=candidate_limit,
        ),
        query_understanding=query_understanding,
    )
