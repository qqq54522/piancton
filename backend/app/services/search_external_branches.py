from __future__ import annotations

import asyncio
import time
from dataclasses import replace

from app.ai.contracts import ModelCallResult
from app.schemas.ai import SearchUnderstanding
from app.services.embedding_recall_service import EmbeddingRecallService
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.meilisearch_recall_service import MeilisearchRecallService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_branch_runner import SearchBranchRunner
from app.services.search_cache import SearchCaches
from app.services.search_models import (
    ExternalSearchCandidate,
    QueryUnderstandingOutcome,
    SearchBranchDiagnostic,
    SearchBranchResult,
    SearchDeadline,
    SearchHit,
)
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter


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
        proof_point_timeout_seconds: float,
        candidate_review_timeout_seconds: float,
        candidate_review_limit: int,
        embedding_top_n: int,
        candidate_limit: int,
        vikingdb_knowledge_router: VikingDBKnowledgeRouter | None = None,
        vikingdb_skill_backup_enabled: bool = True,
        understanding_grace_seconds: float = 5.0,
        understanding_retry_attempts: int = 1,
        understanding_retry_backoff_seconds: float = 1.0,
    ):
        self.search_backend = search_backend.strip().lower()
        self.meilisearch = meilisearch
        self.embedding = embedding
        self.understanding = understanding
        self.vikingdb_knowledge_router = vikingdb_knowledge_router
        self.vikingdb_skill_backup_enabled = vikingdb_skill_backup_enabled
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
        self.proof_point_timeout_seconds = max(0.01, proof_point_timeout_seconds)
        self.candidate_review_timeout_seconds = max(
            0.01,
            candidate_review_timeout_seconds,
        )
        self.candidate_review_limit = max(1, candidate_review_limit)
        self.understanding_grace_seconds = max(0.0, understanding_grace_seconds)
        self.understanding_retry_attempts = max(0, understanding_retry_attempts)
        self.understanding_retry_backoff_seconds = max(
            0.0, understanding_retry_backoff_seconds
        )
        self.embedding_top_n = max(1, embedding_top_n)
        self.candidate_limit = max(1, candidate_limit)
        self.runner = SearchBranchRunner()
        self.semantic_profile = ImageSemanticProfileService()

    @property
    def pure_vikingdb_knowledge_mode(self) -> bool:
        return bool(
            self.vikingdb_knowledge_router is not None
            and self.vikingdb_knowledge_router.configured
            and not self.vikingdb_skill_backup_enabled
        )

    def start_meilisearch(
        self,
        keyword: str,
        limit: int,
        local_understanding: SearchUnderstanding | None,
        *,
        deadline: SearchDeadline | None = None,
    ):
        if self.pure_vikingdb_knowledge_mode and not _is_manual_business_filter(
            local_understanding
        ):
            skipped = self.runner.skipped(
                "meilisearch",
                "火山知识路由测试模式下关闭旧全文召回旁路",
            )
            return asyncio.create_task(_ready(skipped))
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
                lambda _signal: self.meilisearch.recall_candidates(
                    keyword,
                    recall_limit,
                ),
                timeout_seconds=_clamp_timeout(
                    self.meilisearch_timeout_seconds,
                    deadline,
                ),
            )
        )

    def start_embedding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        *,
        deadline: SearchDeadline | None = None,
    ):
        if self.pure_vikingdb_knowledge_mode and not _is_manual_business_filter(
            local_understanding
        ):
            return self.runner.skipped(
                "embedding",
                "火山知识路由测试模式下关闭旧 Embedding 旁路",
            ), None
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
                lambda _signal: self.embedding.query_vector(keyword),
                timeout_seconds=_clamp_timeout(
                    self.embedding_timeout_seconds,
                    deadline,
                ),
            )
        )
        return None, task

    def start_understanding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        *,
        deadline: SearchDeadline | None = None,
    ):
        if (
            not _is_manual_business_filter(local_understanding)
            and
            self.vikingdb_knowledge_router is not None
            and self.vikingdb_knowledge_router.configured
        ):
            task = asyncio.create_task(
                self._run_vikingdb_or_skill_understanding(
                    keyword,
                    deadline=deadline,
                )
            )
            return None, task
        if _has_high_confidence_local_concept(local_understanding):
            return self.runner.skipped(
                "query_understanding",
                "本地高置信业务证据已满足，无需模型补充",
            ), None
        if not self.understanding.should_use_model(keyword, local_understanding):
            return self.runner.skipped(
                "query_understanding",
                "查询理解模型未配置，使用本地固定目录兜底",
            ), None
        if self.understanding.supports_staged_model:
            task = asyncio.create_task(
                self._run_staged_understanding(keyword, deadline=deadline)
            )
            return None, task
        task = asyncio.create_task(
            self._run_basic_understanding(keyword, deadline=deadline)
        )
        return None, task

    async def _run_basic_understanding(
        self,
        keyword: str,
        *,
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult:
        result = await self.runner.run_thread(
            "query_understanding",
            lambda signal: self.understanding.understand_with_model(
                keyword,
                cancellation=signal,
            ),
            timeout_seconds=_clamp_timeout(
                self.understanding_timeout_seconds,
                deadline,
            ),
            attempt_task="search_intent_understanding",
            attempt_layer="第二层：卖点识别",
        )
        call = result.value if isinstance(result.value, ModelCallResult) else None
        if call is None:
            return result
        attempts = self.understanding.model_attempts(
            call.attempts,
            task="search_intent_understanding",
            layer="第二层：卖点识别",
        )
        return SearchBranchResult(
            value=call.value,
            diagnostic=replace(
                result.diagnostic,
                result_count=1 if isinstance(call.value, SearchUnderstanding) else 0,
                attempts=attempts or result.diagnostic.attempts,
            ),
        )

    async def _run_vikingdb_or_skill_understanding(
        self,
        keyword: str,
        *,
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult:
        assert self.vikingdb_knowledge_router is not None
        viking_result = await self.runner.run_thread(
            "vikingdb_knowledge_router",
            lambda _signal: self.vikingdb_knowledge_router.route(keyword),
            timeout_seconds=_clamp_timeout(
                self.selling_point_timeout_seconds,
                deadline,
            ),
        )
        if isinstance(viking_result.value, SearchUnderstanding):
            return viking_result
        if not self.vikingdb_skill_backup_enabled:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status=viking_result.diagnostic.status,
                    duration_ms=viking_result.diagnostic.duration_ms,
                    result_count=0,
                    detail=(
                        "VikingDB 知识路由未产出可信卖点，且 Skill 备份已关闭："
                        f"{viking_result.diagnostic.detail or 'no_match'}"
                    ),
                ),
            )
        fallback = (
            await self._run_staged_understanding(keyword, deadline=deadline)
            if self.understanding.supports_staged_model
            else await self._run_basic_understanding(keyword, deadline=deadline)
        )
        return SearchBranchResult(
            value=fallback.value,
            diagnostic=replace(
                fallback.diagnostic,
                duration_ms=fallback.diagnostic.duration_ms
                + viking_result.diagnostic.duration_ms,
                detail=(
                    "VikingDB 知识路由未命中，已走 Skill 备份；"
                    f"{fallback.diagnostic.detail or ''}"
                ).rstrip("；"),
            ),
        )

    async def _run_staged_understanding(
        self,
        keyword: str,
        *,
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult[QueryUnderstandingOutcome]:
        started = time.monotonic()
        route_result = await self.runner.run_thread(
            "query_system_routing",
            lambda signal: self.understanding.route_with_model(
                keyword,
                cancellation=signal,
            ),
            timeout_seconds=_clamp_timeout(
                self.system_routing_timeout_seconds + self.understanding_grace_seconds,
                deadline,
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
            attempt_task="search_system_routing",
            attempt_layer="第一层：体系路由",
        )
        route_call = (
            route_result.value
            if isinstance(route_result.value, ModelCallResult)
            else None
        )
        route_attempts = self.understanding.model_attempts(
            route_call.attempts if route_call is not None else (),
            task="search_system_routing",
            layer="第一层：体系路由",
        )
        if not route_attempts:
            route_attempts = route_result.diagnostic.attempts
        route_attempts_detail = self.understanding.model_attempts_detail(
            route_call.attempts if route_call is not None else (),
        )
        if route_result.diagnostic.status != "ok" or route_call is None:
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=None,
                    route_completed=False,
                    selling_point_completed=False,
                    proof_point_completed=False,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status=route_result.diagnostic.status,
                    duration_ms=_elapsed_ms(started),
                    detail=(
                        "体系路由失败："
                        f"{route_result.diagnostic.detail or route_result.diagnostic.status}"
                        f"{_attempt_suffix('体系Provider', route_attempts_detail)}"
                    ),
                    attempts=route_attempts,
                ),
            )

        routing = route_call.value
        system_codes = self.understanding.routed_system_codes(routing)
        if not system_codes:
            no_system_result = await self.runner.run_thread(
                "query_selling_point_understanding",
                lambda signal: self.understanding.understand_selling_points_with_model_route(
                    keyword,
                    routing,
                    cancellation=signal,
                ),
                timeout_seconds=_clamp_timeout(
                    self.selling_point_timeout_seconds
                    + self.understanding_grace_seconds,
                    deadline,
                ),
                attempt_task="search_intent_understanding",
                attempt_layer="第二层：卖点识别",
            )
            understanding_call = (
                no_system_result.value
                if isinstance(no_system_result.value, ModelCallResult)
                else None
            )
            understanding = (
                understanding_call.value if understanding_call is not None else None
            )
            understanding_attempts = (
                understanding_call.attempts
                if understanding_call is not None
                else ()
            )
            understanding_diagnostics = (
                self.understanding.model_attempts(
                    understanding_attempts,
                    task="search_intent_understanding",
                    layer="第二层：卖点识别",
                )
                if understanding_call is not None
                else no_system_result.diagnostic.attempts
            )
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=understanding,
                    route_completed=True,
                    selling_point_completed=True,
                    proof_point_completed=True,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status=no_system_result.diagnostic.status,
                    duration_ms=_elapsed_ms(started),
                    result_count=1 if understanding is not None else 0,
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        "无需进入卖点层"
                        f"{_attempt_suffix('体系Provider', route_attempts_detail)}"
                    ),
                    attempts=(
                        *route_attempts,
                        *understanding_diagnostics,
                    ),
                ),
            )

        selling_result = await self.runner.run_thread(
            "query_selling_point_understanding",
            lambda signal: self.understanding.understand_selling_points_with_model_route(
                keyword,
                routing,
                cancellation=signal,
            ),
            timeout_seconds=_clamp_timeout(
                self.selling_point_timeout_seconds + self.understanding_grace_seconds,
                deadline,
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
            attempt_task="search_intent_understanding",
            attempt_layer="第二层：卖点识别",
        )
        selling_call = (
            selling_result.value
            if isinstance(selling_result.value, ModelCallResult)
            else None
        )
        selling_attempts = self.understanding.model_attempts(
            selling_call.attempts if selling_call is not None else (),
            task="search_intent_understanding",
            layer="第二层：卖点识别",
        )
        if not selling_attempts:
            selling_attempts = selling_result.diagnostic.attempts
        selling_attempts_detail = self.understanding.model_attempts_detail(
            selling_call.attempts if selling_call is not None else (),
        )
        selling_completed = bool(
            selling_result.diagnostic.status == "ok"
            and selling_call is not None
            and isinstance(selling_call.value, SearchUnderstanding)
        )
        if not selling_completed:
            repaired = self.understanding.repair_routed_selling_point_understanding(
                keyword,
                routing,
            )
            if repaired is not None:
                selling_understanding = repaired
                selling_completed = True
            else:
                selling_understanding = None
        else:
            assert selling_call is not None
            selling_understanding = selling_call.value
        if not selling_completed:
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=None,
                    routed_system_codes=system_codes,
                    route_completed=True,
                    selling_point_completed=False,
                    proof_point_completed=False,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status=(
                        "ok"
                        if selling_understanding is not None
                        else selling_result.diagnostic.status
                    ),
                    duration_ms=_elapsed_ms(started),
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        f"卖点识别 {selling_result.diagnostic.duration_ms}ms；"
                        + (
                            "按本地规则保护性补全；"
                            if selling_understanding is not None
                            else "卖点层未完成，启用精度保护"
                        )
                        +
                        f"{_attempt_suffix('体系Provider', route_attempts_detail)}"
                        f"{_attempt_suffix('卖点Provider', selling_attempts_detail)}"
                    ),
                    attempts=(*route_attempts, *selling_attempts),
                ),
            )

        assert isinstance(selling_understanding, SearchUnderstanding)
        if not selling_understanding.matched_business_concepts:
            return SearchBranchResult(
                value=QueryUnderstandingOutcome(
                    understanding=selling_understanding,
                    routed_system_codes=system_codes,
                    route_completed=True,
                    selling_point_completed=True,
                    proof_point_completed=True,
                ),
                diagnostic=SearchBranchDiagnostic(
                    source="query_understanding",
                    status="ok",
                    duration_ms=_elapsed_ms(started),
                    result_count=1,
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        f"卖点识别 {selling_result.diagnostic.duration_ms}ms；"
                        + (
                            "按本地规则保护性补全；"
                            if selling_result.diagnostic.status != "ok"
                            else ""
                        )
                        + "未命中卖点，无需进入证明点层"
                        f"{_attempt_suffix('体系Provider', route_attempts_detail)}"
                        f"{_attempt_suffix('卖点Provider', selling_attempts_detail)}"
                    ),
                    attempts=(*route_attempts, *selling_attempts),
                ),
            )

        proof_result = await self.runner.run_thread(
            "query_proof_point_understanding",
            lambda signal: self.understanding.understand_proof_points_with_model(
                keyword,
                selling_understanding,
                cancellation=signal,
            ),
            timeout_seconds=_clamp_timeout(
                self.proof_point_timeout_seconds + self.understanding_grace_seconds,
                deadline,
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
            attempt_task="search_proof_point_understanding",
            attempt_layer="第三层：证明点识别",
        )
        proof_call = (
            proof_result.value
            if isinstance(proof_result.value, ModelCallResult)
            else None
        )
        proof_attempts = self.understanding.model_attempts(
            proof_call.attempts if proof_call is not None else (),
            task="search_proof_point_understanding",
            layer="第三层：证明点识别",
        )
        if not proof_attempts:
            proof_attempts = proof_result.diagnostic.attempts
        proof_attempts_detail = self.understanding.model_attempts_detail(
            proof_call.attempts if proof_call is not None else (),
        )
        proof_completed = bool(
            proof_result.diagnostic.status == "ok"
            and proof_call is not None
            and isinstance(proof_call.value, SearchUnderstanding)
        )
        return SearchBranchResult(
            value=QueryUnderstandingOutcome(
                understanding=(
                    proof_call.value
                    if proof_completed and proof_call is not None
                    else selling_understanding
                ),
                routed_system_codes=system_codes,
                route_completed=True,
                selling_point_completed=True,
                proof_point_completed=proof_completed,
            ),
            diagnostic=SearchBranchDiagnostic(
                source="query_understanding",
                status="ok" if proof_completed else proof_result.diagnostic.status,
                duration_ms=_elapsed_ms(started),
                result_count=1 if proof_completed else 0,
                detail=(
                    f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                    f"卖点识别 {selling_result.diagnostic.duration_ms}ms"
                    f"；证明点识别 {proof_result.diagnostic.duration_ms}ms"
                    + ("" if proof_completed else "；证明点层未完成")
                    + _attempt_suffix("体系Provider", route_attempts_detail)
                    + _attempt_suffix("卖点Provider", selling_attempts_detail)
                    + _attempt_suffix("证明点Provider", proof_attempts_detail)
                ),
                attempts=(*route_attempts, *selling_attempts, *proof_attempts),
            ),
        )

    def final_understanding(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        result: SearchBranchResult,
        *,
        pure_vikingdb_required: bool | None = None,
    ) -> SearchUnderstanding | None:
        if pure_vikingdb_required is None:
            pure_vikingdb_required = (
                self.pure_vikingdb_knowledge_mode
                and not _is_manual_business_filter(local_understanding)
            )
        value = result.value
        if isinstance(value, QueryUnderstandingOutcome):
            value = value.understanding
        if isinstance(value, SearchUnderstanding):
            if result.diagnostic.source == "vikingdb_knowledge_router":
                return value
            if pure_vikingdb_required:
                return None
            return self.understanding.arbitrate_model_understanding(
                local_understanding,
                value,
            )
        if pure_vikingdb_required:
            return None
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
                and value.proof_point_completed
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

    async def review_candidates(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        hits: list[SearchHit],
        limit: int,
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult[list[SearchHit]]:
        review_limit = min(max(limit, 1), self.candidate_review_limit)
        contexts = self._candidate_review_contexts(hits[:review_limit])
        if not contexts:
            return SearchBranchResult(
                value=hits,
                diagnostic=SearchBranchDiagnostic(
                    source="candidate_review",
                    status="skipped",
                    duration_ms=0,
                    result_count=len(hits),
                    detail="没有可复核候选",
                ),
            )
        result = await self.runner.run_thread(
            "candidate_review",
            lambda signal: self.understanding.review_candidates_with_model(
                keyword=keyword,
                understanding=understanding,
                candidates=contexts,
                cancellation=signal,
            ),
            timeout_seconds=_clamp_timeout(
                self.candidate_review_timeout_seconds,
                deadline,
            ),
            attempt_task="search_candidate_review",
            attempt_layer="第四层：候选图片复核",
        )
        review_call = (
            result.value if isinstance(result.value, ModelCallResult) else None
        )
        attempts = self.understanding.model_attempts(
            review_call.attempts if review_call is not None else (),
            task="search_candidate_review",
            layer="第四层：候选图片复核",
        )
        if not attempts:
            attempts = result.diagnostic.attempts
        attempts_detail = self.understanding.model_attempts_detail(
            review_call.attempts if review_call is not None else (),
        )
        if result.diagnostic.status != "ok" or result.value is None:
            return SearchBranchResult(
                value=hits,
                diagnostic=SearchBranchDiagnostic(
                    source="candidate_review",
                    status=result.diagnostic.status,
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=len(hits),
                    detail=(
                        result.diagnostic.detail
                        or "第四层候选图片复核未完成，保留原排序"
                    )
                    + _attempt_suffix("复核Provider", attempts_detail),
                    attempts=attempts,
                ),
            )
        if review_call is None:
            detail = "第四层候选图片复核未返回正式模型结果，保留原排序"
            return SearchBranchResult(
                value=hits,
                diagnostic=SearchBranchDiagnostic(
                    source="candidate_review",
                    status="failed",
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=len(hits),
                    detail=detail,
                    attempts=attempts,
                ),
            )
        review_result = review_call.value
        reviewed_hits, applied = _apply_candidate_review(
            hits,
            review_result.decisions,
        )
        return SearchBranchResult(
            value=reviewed_hits,
            diagnostic=SearchBranchDiagnostic(
                source="candidate_review",
                status="ok",
                duration_ms=result.diagnostic.duration_ms,
                result_count=applied,
                detail=(
                    f"第四层复核 {len(contexts)} 张候选，应用 {applied} 条决策"
                    + _attempt_suffix("复核Provider", attempts_detail)
                ),
                attempts=attempts,
            ),
        )

    def _candidate_review_contexts(self, hits: list[SearchHit]) -> list[dict]:
        contexts = []
        for hit in hits:
            image = hit.image
            group = image.asset_group
            accepted_phrases = [
                phrase.phrase
                for phrase in (group.search_phrases if group else [])
                if phrase.review_status == "accepted"
            ][:8]
            accepted_links = [
                link
                for link in (group.concept_links if group else [])
                if link.review_status == "accepted"
                and link.relation_role in {"expresses", "supports"}
            ]
            profile = self.semantic_profile.profile_from_image(image)
            contexts.append(
                {
                    "image_id": image.id,
                    "title": image.title,
                    "asset_title": group.title if group else image.title,
                    "score": hit.score,
                    "reasons": list(hit.reasons),
                    "image_summary": image.image_summary or "",
                    "visual_facts": (profile.visual_facts if profile else [])[:6],
                    "scenes": (profile.scenes if profile else [])[:4],
                    "asset_search_phrases": accepted_phrases,
                    "business_relations": [
                        {
                            "concept_code": link.concept.code,
                            "concept_name": link.concept.name,
                            "relation_role": link.relation_role,
                        }
                        for link in accepted_links
                    ],
                    "primary_proof_point_code": (
                        group.primary_proof_point_code if group else None
                    ),
                    "primary_evidence_point_code": (
                        group.primary_evidence_point_code if group else None
                    ),
                }
            )
        return contexts


async def _ready(value):
    return value


def _cache_key(value: str) -> str:
    return "".join(value.lower().split())


def _attempt_suffix(label: str, attempts: str) -> str:
    return f"；{label}：{attempts}" if attempts else ""


def _apply_candidate_review(hits: list[SearchHit], decisions) -> tuple[list[SearchHit], int]:
    by_image_id = {
        item.image_id: item
        for item in decisions
        if item.confidence >= 0.7
    }
    applied = 0
    kept: list[SearchHit] = []
    demoted: list[SearchHit] = []
    for hit in hits:
        decision = by_image_id.get(hit.image.id)
        if decision is None:
            kept.append(hit)
            continue
        applied += 1
        reason = f"第四层复核：{decision.reason}"
        if decision.decision == "exclude":
            continue
        if decision.decision == "demote":
            demoted.append(
                SearchHit(
                    image=hit.image,
                    score=(hit.score or 0.65) * 0.75,
                    reasons=tuple(dict.fromkeys([*hit.reasons, reason])),
                )
            )
            continue
        kept.append(
            SearchHit(
                image=hit.image,
                score=hit.score,
                reasons=tuple(dict.fromkeys([*hit.reasons, reason])),
            )
        )
    return [*kept, *demoted], applied


def _has_high_confidence_local_concept(
    understanding: SearchUnderstanding | None,
) -> bool:
    if understanding is None:
        return False
    return any(
        item.weight >= 0.85
        for item in understanding.matched_business_concepts
    )


def _is_manual_business_filter(understanding: SearchUnderstanding | None) -> bool:
    return bool(
        understanding
        and understanding.search_strategy == "按用户手动选择的业务层级执行硬约束搜索"
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _clamp_timeout(configured_seconds: float, deadline: SearchDeadline | None) -> float:
    if deadline is None:
        return max(0.01, configured_seconds)
    return deadline.clamp(configured_seconds)
