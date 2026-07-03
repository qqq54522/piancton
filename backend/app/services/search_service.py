from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.search_query_expansion import ExpandedQuery
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import SearchUnderstanding
from app.schemas.image import SearchResponse
from app.services.ai_service import AiService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.embedding_recall_service import EmbeddingRecallService
from app.services.image_summary_match_service import ImageSummaryMatchService
from app.services.meilisearch_recall_service import MeilisearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_models import SearchUnavailable, StrictSearchPolicy
from app.services.search_ranking_service import SearchRankingService
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient


class SearchService:
    """Search orchestration isolated from image CRUD.

    Database fuzzy search remains the safe default. External search backends are
    shadowed behind the same contract and fall back to the database path.
    """

    def __init__(
        self,
        db: Session,
        *,
        search_backend: str = "database",
        meilisearch_url: str = "",
        meilisearch_api_key: str = "",
        meilisearch_index: str = "images",
        search_timeout_seconds: float = 2.0,
        ai_service: AiService | None = None,
        embedding_client: EmbeddingClient | None = None,
        embedding_top_n: int = 100,
        reranker: RerankerClient | None = None,
        reranker_top_n: int = 50,
    ):
        repo = ImageRepository(db)
        self.search_backend = search_backend.strip().lower()
        self.embedding_top_n = embedding_top_n
        self.expansion = QueryExpansionService()
        self.query_understanding = QueryUnderstandingService(ai_service)
        self.ranking = SearchRankingService(
            reranker,
            reranker_top_n,
            summary_matcher=ImageSummaryMatchService(ai_service),
        )
        self.database_recall = DatabaseSearchRecallService(repo)
        self.embedding_recall = EmbeddingRecallService(repo, embedding_client)
        self.meilisearch_recall = MeilisearchRecallService(
            repo,
            url=meilisearch_url,
            api_key=meilisearch_api_key,
            index=meilisearch_index,
            timeout_seconds=search_timeout_seconds,
        )

    def search(
        self,
        keyword: str,
        limit: int,
        search_mode: Literal["configured", "precise", "smart"] = "configured",
    ) -> SearchResponse:
        needle = keyword.strip().lower()
        mode = search_mode.strip().lower()
        if mode == "smart":
            return self._search_smart(keyword, limit)
        if mode == "precise":
            return self._search_database(keyword, limit)
        if self.search_backend == "meilisearch":
            try:
                hits = self.meilisearch_recall.search(needle, limit)
                hits = self.ranking.merge_hits(
                    hits, self.embedding_recall.search(keyword, limit * 3)
                )
                return self.ranking.build_response(
                    keyword=keyword,
                    hits=self.ranking.rerank_hits(keyword, hits, limit),
                    search_mode="meilisearch",
                    fallback=False,
                )
            except SearchUnavailable as exc:
                return self._search_database(keyword, limit, fallback_reason=str(exc))
        return self._search_database(keyword, limit)

    def _search_smart(self, keyword: str, limit: int) -> SearchResponse:
        understanding = self._understand_search(keyword)
        ai_expanded_queries = self.expansion.queries_from_understanding(understanding)
        smart_keyword = self.expansion.smart_keyword(keyword, ai_expanded_queries)
        if self.meilisearch_recall.configured:
            try:
                hits = self.meilisearch_recall.search(smart_keyword, limit)
                hits = self.ranking.merge_hits(
                    hits, self.embedding_recall.search(smart_keyword, limit * 3)
                )
                hits = self.ranking.rerank_hits(keyword, hits, limit)
                hits = self.ranking.apply_strict_policy(
                    hits,
                    self._strict_policy(understanding),
                )
                hits = self.ranking.apply_summary_judgement(
                    keyword=keyword,
                    understanding=understanding,
                    hits=hits,
                    limit=limit,
                )[:limit]
                return self.ranking.build_response(
                    keyword=keyword,
                    hits=hits,
                    search_mode="meilisearch",
                    fallback=False,
                    search_understanding=understanding,
                )
            except SearchUnavailable as exc:
                return self._search_database(
                    keyword,
                    limit,
                    fallback_reason=f"智能搜索降级：{exc}",
                    extra_queries=ai_expanded_queries,
                    search_understanding=understanding,
                )
        return self._search_database(
            keyword,
            limit,
            fallback_reason="智能搜索未配置 Meilisearch，已使用精准搜索兜底",
            extra_queries=ai_expanded_queries,
            search_understanding=understanding,
        )

    def _search_database(
        self,
        keyword: str,
        limit: int,
        fallback_reason: str | None = None,
        extra_queries: list[ExpandedQuery] | None = None,
        search_understanding: SearchUnderstanding | None = None,
    ) -> SearchResponse:
        hits = self.embedding_recall.search(
            keyword,
            max(limit * 3, self.embedding_top_n),
        )
        hits = self.ranking.merge_hits(
            hits,
            self.database_recall.search_queries(
                self.expansion.database_queries(keyword, extra_queries or []),
                limit=max(limit * 3, limit),
            ),
        )
        hits = self.ranking.sort_hits(hits)
        hits = self.ranking.rerank_hits(keyword, hits, limit)
        hits = self.ranking.apply_strict_policy(
            hits,
            self._strict_policy(search_understanding),
        )
        hits = self.ranking.apply_summary_judgement(
            keyword=keyword,
            understanding=search_understanding,
            hits=hits,
            limit=limit,
        )[:limit]
        return self.ranking.build_response(
            keyword=keyword,
            hits=hits,
            search_mode="fuzzy",
            fallback=fallback_reason is not None,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
        )

    def _understand_search(self, keyword: str) -> SearchUnderstanding | None:
        try:
            return self.query_understanding.understand(keyword)
        except AppError:
            return None

    def _strict_policy(
        self,
        understanding: SearchUnderstanding | None,
    ) -> StrictSearchPolicy | None:
        if not understanding or understanding.query_type != "business_intent_search":
            return None
        direct_matches = [
            item
            for item in understanding.matched_level2_categories
            if item.relation == "direct"
        ]
        if not direct_matches:
            return None
        primary = max(direct_matches, key=lambda item: item.weight)
        return StrictSearchPolicy(
            primary_label=understanding.normalized_query,
            primary_category=primary.category,
            confidence=primary.weight,
            intent_reason=primary.reason,
            exclude_terms=tuple(understanding.exclude_tags),
        )
