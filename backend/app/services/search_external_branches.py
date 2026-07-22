from __future__ import annotations

import asyncio
import time

from app.schemas.ai import SearchUnderstanding
from app.services.embedding_recall_service import EmbeddingRecallService
from app.services.meilisearch_recall_service import MeilisearchRecallService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_branch_runner import SearchBranchRunner
from app.services.search_cache import SearchCaches
from app.services.search_models import (
    ExternalSearchCandidate,
    QueryUnderstandingOutcome,
    SearchBranchDiagnostic,
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
        system_routing_timeout_seconds: float,
        selling_point_timeout_seconds: float,
        embedding_top_n: int,
        candidate_limit: int,
        understanding_grace_seconds: float = 5.0,
        understanding_retry_attempts: int = 1,
        understanding_retry_backoff_seconds: float = 1.0,
    ):
        self.search_backend = search_backend.strip().lower()
        self.meilisearch = meilisearch
        self.embedding = embedding
        self.understanding = understanding
        self.caches = caches
        self.meilisearch_timeout_seconds = max(0.01, meilisearch_timeout_seconds)
        self.embedding_timeout_seconds = max(0.01, embedding_timeout_seconds)
        self.understanding_timeout_seconds = max(0.01, understanding_timeout_seconds)
        self.system_routing_timeout_seconds = max(
            0.01, system_routing_timeout_seconds
        )
        self.selling_point_timeout_seconds = max(
            0.01, selling_point_timeout_seconds
        )
        self.understanding_grace_seconds = max(0.0, understanding_grace_seconds)
        self.understanding_retry_attempts = max(0, understanding_retry_attempts)
        self.understanding_retry_backoff_seconds = max(
            0.0, understanding_retry_backoff_seconds
        )
        self.embedding_top_n = max(1, embedding_top_n)
        self.candidate_limit = max(1, candidate_limit)
        self.runner = SearchBranchRunner()

    def start_meilisearch(
        self,
        keyword: str,
        limit: int,
        local_understanding: SearchUnderstanding | None,
    ):
        if _has_high_confidence_local_concept(local_understanding):
            skipped = self.runner.skipped(
                "meilisearch",
                "本地高置信业务概念已满足",
            )
            return asyncio.create_task(_ready(skipped))
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
        proof_completion = self.understanding.needs_proof_point_completion(
            keyword,
            local_understanding,
        )
        if not self.understanding.should_use_model(keyword, local_understanding):
            detail = (
                "本地高置信业务证据已满足，无需模型补充"
                if _has_high_confidence_local_concept(local_understanding)
                else "查询理解模型未配置，使用本地固定目录兜底"
            )
            return self.runner.skipped(
                "query_understanding",
                detail,
            ), None
        cache_key = self.understanding.cache_key(keyword)
        cached = self.caches.understanding.get(cache_key)
        if cached is not None:
            return self.runner.cached(
                "query_understanding",
                QueryUnderstandingOutcome(
                    understanding=cached,
                    route_completed=True,
                    selling_point_completed=True,
                ),
            ), None
        if (
            proof_completion
            and local_understanding is not None
            and self.understanding.supports_staged_model
        ):
            task = asyncio.create_task(
                self._run_scoped_proof_completion(keyword, local_understanding)
            )
            return None, task
        if self.understanding.supports_staged_model:
            task = asyncio.create_task(
                self._run_staged_understanding(keyword)
            )
            return None, task
        task = asyncio.create_task(
            self.runner.run_thread(
                "query_understanding",
                lambda: self.understanding.understand_with_model(keyword),
                timeout_seconds=self.understanding_timeout_seconds,
            )
        )
        return None, task

    async def _run_scoped_proof_completion(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding,
    ) -> SearchBranchResult:
        started = time.monotonic()
        result = await self.runner.run_thread(
            "query_proof_point_completion",
            lambda: self.understanding.complete_proof_points_with_model(
                keyword,
                local_understanding,
            ),
            timeout_seconds=(
                self.selling_point_timeout_seconds
                + self.understanding_grace_seconds
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
        )
        return SearchBranchResult(
            value=result.value,
            diagnostic=SearchBranchDiagnostic(
                source="query_understanding",
                status=result.diagnostic.status,
                duration_ms=_elapsed_ms(started),
                result_count=1 if isinstance(result.value, SearchUnderstanding) else 0,
                detail=(
                    "已确认卖点内证明点补全"
                    if result.diagnostic.status == "ok"
                    else f"证明点补全{result.diagnostic.detail or result.diagnostic.status}"
                ),
            ),
        )

    async def _run_staged_understanding(
        self,
        keyword: str,
    ) -> SearchBranchResult[QueryUnderstandingOutcome]:
        started = time.monotonic()
        route_result = await self.runner.run_thread(
            "query_system_routing",
            lambda: self.understanding.route_with_model(keyword),
            timeout_seconds=(
                self.system_routing_timeout_seconds
                + self.understanding_grace_seconds
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
        )
        if route_result.diagnostic.status != "ok" or route_result.value is None:
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=None,
                    route_completed=False,
                    selling_point_completed=False,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status=route_result.diagnostic.status,
                    duration_ms=_elapsed_ms(started),
                    detail=(
                        "体系路由失败："
                        f"{route_result.diagnostic.detail or route_result.diagnostic.status}"
                    ),
                ),
            )

        routing = route_result.value
        system_codes = self.understanding.routed_system_codes(routing)
        if not system_codes:
            understanding = self.understanding.understand_with_model_route(
                keyword,
                routing,
            )
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=understanding,
                    route_completed=True,
                    selling_point_completed=True,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status="ok",
                    duration_ms=_elapsed_ms(started),
                    result_count=1 if understanding is not None else 0,
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        "无需进入卖点层"
                    ),
                ),
            )

        selling_result = await self.runner.run_thread(
            "query_selling_point_understanding",
            lambda: self.understanding.understand_with_model_route(
                keyword,
                routing,
            ),
            timeout_seconds=(
                self.selling_point_timeout_seconds
                + self.understanding_grace_seconds
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
        )
        selling_completed = bool(
            selling_result.diagnostic.status == "ok"
            and isinstance(selling_result.value, SearchUnderstanding)
        )
        return SearchBranchResult(
            value=QueryUnderstandingOutcome(
                understanding=(
                    selling_result.value if selling_completed else None
                ),
                routed_system_codes=system_codes,
                route_completed=True,
                selling_point_completed=selling_completed,
            ),
            diagnostic=SearchBranchDiagnostic(
                source="query_understanding",
                status=(
                    "ok" if selling_completed else selling_result.diagnostic.status
                ),
                duration_ms=_elapsed_ms(started),
                result_count=1 if selling_completed else 0,
                detail=(
                    f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                    f"卖点识别 {selling_result.diagnostic.duration_ms}ms"
                    + (
                        ""
                        if selling_completed
                        else "；卖点层未完成，启用精度保护"
                    )
                ),
            ),
        )

    def final_understanding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        result: SearchBranchResult,
    ) -> SearchUnderstanding | None:
        value = result.value
        if isinstance(value, QueryUnderstandingOutcome):
            value = value.understanding
        if isinstance(value, SearchUnderstanding):
            if not result.diagnostic.cache_hit:
                self.caches.understanding.set(
                    self.understanding.cache_key(keyword),
                    value,
                )
            return self.understanding.arbitrate_model_understanding(
                local_understanding,
                value,
            )
        if result.diagnostic.status in {"failed", "timed_out"}:
            if _has_high_confidence_local_concept(local_understanding):
                return local_understanding
            return self.understanding.weak_local_fallback(keyword)
        return local_understanding

    def understanding_succeeded(self, result: SearchBranchResult) -> bool:
        value = result.value
        if isinstance(value, QueryUnderstandingOutcome):
            return bool(
                value.selling_point_completed
                and isinstance(value.understanding, SearchUnderstanding)
            )
        return bool(
            result.diagnostic.status == "ok"
            and isinstance(value, SearchUnderstanding)
        )

    def requires_precision_lock(self, result: SearchBranchResult) -> bool:
        value = result.value
        return bool(
            isinstance(value, QueryUnderstandingOutcome)
            and value.route_completed
            and value.routed_system_codes
            and not value.selling_point_completed
        )

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


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
