from __future__ import annotations

import asyncio
import hashlib
import json
import time

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
        proof_point_timeout_seconds: float,
        candidate_review_timeout_seconds: float,
        candidate_review_limit: int,
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
                    proof_point_completed=True,
                ),
            ), None
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
        route_attempts = self.understanding.model_attempts_detail()
        if route_result.diagnostic.status != "ok" or route_result.value is None:
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
                        f"{_attempt_suffix('体系Provider', route_attempts)}"
                    ),
                ),
            )

        routing = route_result.value
        system_codes = self.understanding.routed_system_codes(routing)
        if not system_codes:
            understanding = self.understanding.understand_selling_points_with_model_route(
                keyword,
                routing,
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
                    status="ok",
                    duration_ms=_elapsed_ms(started),
                    result_count=1 if understanding is not None else 0,
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        "无需进入卖点层"
                        f"{_attempt_suffix('体系Provider', route_attempts)}"
                    ),
                ),
            )

        selling_result = await self.runner.run_thread(
            "query_selling_point_understanding",
            lambda: self.understanding.understand_selling_points_with_model_route(
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
        selling_attempts = self.understanding.model_attempts_detail()
        selling_completed = bool(
            selling_result.diagnostic.status == "ok"
            and isinstance(selling_result.value, SearchUnderstanding)
        )
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
                    status=selling_result.diagnostic.status,
                    duration_ms=_elapsed_ms(started),
                    detail=(
                        f"体系路由 {route_result.diagnostic.duration_ms}ms；"
                        f"卖点识别 {selling_result.diagnostic.duration_ms}ms；"
                        "卖点层未完成，启用精度保护"
                        f"{_attempt_suffix('体系Provider', route_attempts)}"
                        f"{_attempt_suffix('卖点Provider', selling_attempts)}"
                    ),
                ),
            )

        selling_understanding = selling_result.value
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
                        "未命中卖点，无需进入证明点层"
                        f"{_attempt_suffix('体系Provider', route_attempts)}"
                        f"{_attempt_suffix('卖点Provider', selling_attempts)}"
                    ),
                ),
            )

        proof_result = await self.runner.run_thread(
            "query_proof_point_understanding",
            lambda: self.understanding.understand_proof_points_with_model(
                keyword,
                selling_understanding,
            ),
            timeout_seconds=(
                self.proof_point_timeout_seconds
                + self.understanding_grace_seconds
            ),
            retry_attempts=self.understanding_retry_attempts,
            retry_backoff_seconds=self.understanding_retry_backoff_seconds,
        )
        proof_attempts = self.understanding.model_attempts_detail()
        proof_completed = bool(
            proof_result.diagnostic.status == "ok"
            and isinstance(proof_result.value, SearchUnderstanding)
        )
        return SearchBranchResult(
            value=QueryUnderstandingOutcome(
                understanding=(
                    proof_result.value
                    if proof_completed
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
                    + _attempt_suffix("体系Provider", route_attempts)
                    + _attempt_suffix("卖点Provider", selling_attempts)
                    + _attempt_suffix("证明点Provider", proof_attempts)
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
        completed = True
        if isinstance(value, QueryUnderstandingOutcome):
            completed = value.proof_point_completed
            value = value.understanding
        if isinstance(value, SearchUnderstanding):
            if completed and not result.diagnostic.cache_hit:
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
    ) -> SearchBranchResult[list[SearchHit]]:
        review_limit = min(max(limit, 1), self.candidate_review_limit)
        contexts = self._candidate_review_contexts(hits[:review_limit])
        if not contexts:
            return self.runner.skipped("candidate_review", "没有可复核候选")
        cache_key = _candidate_review_cache_key(keyword, understanding, contexts)
        cached = self.caches.candidate_reviews.get(cache_key)
        if cached is not None:
            reviewed_hits, applied = _apply_candidate_review(hits, cached.decisions)
            return SearchBranchResult(
                value=reviewed_hits,
                diagnostic=SearchBranchDiagnostic(
                    source="candidate_review",
                    status="ok",
                    duration_ms=0,
                    result_count=applied,
                    cache_hit=True,
                    detail=(
                        f"第四层复核缓存命中 {len(contexts)} 张候选，应用 {applied} 条决策"
                    ),
                ),
            )
        result = await self.runner.run_thread(
            "candidate_review",
            lambda: self.understanding.review_candidates_with_model(
                keyword=keyword,
                understanding=understanding,
                candidates=contexts,
            ),
            timeout_seconds=self.candidate_review_timeout_seconds,
        )
        attempts = self.understanding.model_attempts_detail()
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
                    + _attempt_suffix("复核Provider", attempts),
                ),
            )
        reviewed_hits, applied = _apply_candidate_review(hits, result.value.decisions)
        self.caches.candidate_reviews.set(cache_key, result.value)
        return SearchBranchResult(
            value=reviewed_hits,
            diagnostic=SearchBranchDiagnostic(
                source="candidate_review",
                status="ok",
                duration_ms=result.diagnostic.duration_ms,
                result_count=applied,
                detail=(
                    f"第四层复核 {len(contexts)} 张候选，应用 {applied} 条决策"
                    + _attempt_suffix("复核Provider", attempts)
                ),
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


def _candidate_review_cache_key(
    keyword: str,
    understanding: SearchUnderstanding | None,
    contexts: list[dict],
) -> str:
    payload = {
        "keyword": _cache_key(keyword),
        "understanding": (
            understanding.model_dump(mode="json") if understanding else None
        ),
        "candidates": [_stable_candidate_review_context(item) for item in contexts],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _stable_candidate_review_context(context: dict) -> dict:
    return {
        key: value
        for key, value in context.items()
        if key not in {"score", "reasons"}
    }


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


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
