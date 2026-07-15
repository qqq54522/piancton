from __future__ import annotations

import asyncio

from app.schemas.ai import SearchUnderstanding
from app.services.embedding_recall_service import EmbeddingRecallService
from app.services.meilisearch_recall_service import MeilisearchRecallService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_branch_runner import SearchBranchRunner
from app.services.search_cache import SearchCaches
from app.services.search_models import (
    ExternalSearchCandidate,
    SearchBranchResult,
    SearchHit,
)


class SearchExternalBranches:
    """Starts external work without ORM access, then hydrates on the request session."""

    def __init__(
        self,
        *,
        search_backend: str,
        meilisearch: MeilisearchRecallService,
        embedding: EmbeddingRecallService,
        understanding: QueryUnderstandingService,
        caches: SearchCaches,
        meilisearch_timeout_seconds: float,
        embedding_timeout_seconds: float,
        understanding_timeout_seconds: float,
        embedding_top_n: int,
        candidate_limit: int,
    ):
        self.search_backend = search_backend.strip().lower()
        self.meilisearch = meilisearch
        self.embedding = embedding
        self.understanding = understanding
        self.caches = caches
        self.meilisearch_timeout_seconds = max(0.01, meilisearch_timeout_seconds)
        self.embedding_timeout_seconds = max(0.01, embedding_timeout_seconds)
        self.understanding_timeout_seconds = max(0.01, understanding_timeout_seconds)
        self.embedding_top_n = max(1, embedding_top_n)
        self.candidate_limit = max(1, candidate_limit)
        self.runner = SearchBranchRunner()

    def start_meilisearch(self, keyword: str, limit: int):
        enabled = self.meilisearch.configured and self.search_backend == "meilisearch"
        if not enabled:
            skipped = self.runner.skipped(
                "meilisearch",
                "搜索增强未启用或服务未配置",
            )
            return asyncio.create_task(_ready(skipped))
        recall_limit = max(limit * 3, self.candidate_limit)
        return asyncio.create_task(
            self.runner.run_thread(
                "meilisearch",
                lambda: self.meilisearch.recall_candidates(keyword, recall_limit),
                timeout_seconds=self.meilisearch_timeout_seconds,
            )
        )

    def start_embedding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
    ):
        if _has_high_confidence_local_concept(local_understanding):
            return self.runner.skipped(
                "embedding",
                "本地高置信业务概念已满足",
            ), None
        if not self.embedding.configured:
            return self.runner.skipped("embedding", "服务未配置"), None
        cache_key = f"{self.embedding.model_name}:{_cache_key(keyword)}"
        cached = self.caches.embedding_vectors.get(cache_key)
        if cached is not None:
            return self.runner.cached("embedding", list(cached)), None
        task = asyncio.create_task(
            self.runner.run_thread(
                "embedding",
                lambda: self.embedding.query_vector(keyword),
                timeout_seconds=self.embedding_timeout_seconds,
            )
        )
        return None, task

    def start_understanding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
    ):
        cache_key = _cache_key(keyword)
        cached = self.caches.understanding.get(cache_key)
        if cached is not None:
            return self.runner.cached("query_understanding", cached), None
        if not self.understanding.should_use_model(keyword, local_understanding):
            return self.runner.skipped(
                "query_understanding",
                "本地高置信理解已满足",
            ), None
        task = asyncio.create_task(
            self.runner.run_thread(
                "query_understanding",
                lambda: self.understanding.understand_with_model(keyword),
                timeout_seconds=self.understanding_timeout_seconds,
            )
        )
        return None, task

    def final_understanding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        result: SearchBranchResult,
    ) -> SearchUnderstanding | None:
        value = result.value
        if isinstance(value, SearchUnderstanding):
            if not result.diagnostic.cache_hit:
                self.caches.understanding.set(_cache_key(keyword), value)
            return value
        if result.diagnostic.status in {"failed", "timed_out"}:
            return self.understanding.weak_local_fallback(keyword)
        return local_understanding

    def hydrate_meilisearch(
        self,
        result: SearchBranchResult,
    ) -> list[SearchHit]:
        candidates = result.value
        if not isinstance(candidates, list):
            return []
        valid = [item for item in candidates if isinstance(item, ExternalSearchCandidate)]
        return self.meilisearch.hydrate(valid)

    def hydrate_embedding(
        self,
        result: SearchBranchResult,
        *,
        limit: int,
        keyword: str,
    ) -> list[SearchHit]:
        vector = result.value
        if not isinstance(vector, list) or not vector:
            return []
        try:
            normalized_vector = [float(item) for item in vector]
        except (TypeError, ValueError):
            return []
        if not result.diagnostic.cache_hit:
            cache_key = f"{self.embedding.model_name}:{_cache_key(keyword)}"
            self.caches.embedding_vectors.set(cache_key, tuple(normalized_vector))
        candidates = self.embedding.score_candidates(
            normalized_vector,
            max(limit * 3, self.embedding_top_n),
        )
        return self.embedding.hydrate(candidates)

    def with_result_count(
        self,
        result: SearchBranchResult,
        count: int,
    ) -> SearchBranchResult:
        return self.runner.with_result_count(result, count)


async def _ready(value):
    return value


def _cache_key(value: str) -> str:
    return "".join(value.lower().split())


def _has_high_confidence_local_concept(
    understanding: SearchUnderstanding | None,
) -> bool:
    if understanding is None:
        return False
    return any(
        item.weight >= 0.85
        for item in understanding.matched_business_concepts
    )
