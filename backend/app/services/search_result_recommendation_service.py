from __future__ import annotations

import re
import time

from app.ai.contracts import ModelCallResult, ResultRecommendationCapabilities
from app.schemas.ai import SearchUnderstanding
from app.schemas.image import ScoredImage
from app.services.search_branch_runner import SearchBranchRunner
from app.services.search_models import (
    BranchStatus,
    ModelAttemptDiagnostic,
    SearchBranchDiagnostic,
    SearchBranchResult,
    SearchDeadline,
    SearchHit,
)
from app.services.search_scorer import SearchScorer

_ROUTE_EXPLANATION_PROCESS_MARKERS = (
    "未指定渠道",
    "当前返回",
    "卡片下方",
    "已审核素材",
    "保留手机端大图",
    "保留手机端小图",
    "已按当前渠道",
    "渠道/场景筛选",
    "同时按",
    "收窄版位",
)
ROUTE_EXPLANATION_MAX_WAIT_SECONDS = 8.0


class SearchResultRecommendationService:
    """Explain final results after recall, ranking, and candidate review."""

    def __init__(
        self,
        ai_service,
        *,
        timeout_seconds: float = 6.0,
        result_limit: int = 12,
    ):
        self.ai_service = ai_service
        self.timeout_seconds = max(0.5, timeout_seconds)
        self.result_limit = max(1, result_limit)
        self.runner = SearchBranchRunner()
        self.scorer = SearchScorer()

    async def explain_route(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        result_count: int,
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult[str]:
        if result_count <= 0:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="search_route_explanation",
                    status="skipped",
                    duration_ms=0,
                    result_count=0,
                    detail="没有最终结果需要解释命中卖点",
                ),
            )
        if not understanding or not understanding.matched_business_concepts:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="search_route_explanation",
                    status="skipped",
                    duration_ms=0,
                    result_count=0,
                    detail="没有可靠卖点命中，不生成顶部解释",
                ),
            )
        explain = getattr(self.ai_service, "explain_search_route", None)
        provider = getattr(self.ai_service, "provider", None)
        if explain is None or not getattr(provider, "configured", False):
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="search_route_explanation",
                    status="skipped",
                    duration_ms=0,
                    result_count=0,
                    detail="命中卖点解释 API 未配置，使用前端默认说明",
                    attempts=(
                        self._synthetic_attempt(
                            "skipped",
                            "命中卖点解释 API 未配置",
                            layer="搜索结果：命中卖点解释",
                        ),
                    ),
                ),
            )
        if deadline is not None and deadline.expired:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="search_route_explanation",
                    status="timed_out",
                    duration_ms=0,
                    result_count=0,
                    detail="搜索总时间预算已到，跳过命中卖点解释",
                    attempts=(
                        self._synthetic_attempt(
                            "timed_out",
                            "搜索总时间预算已到",
                            layer="搜索结果：命中卖点解释",
                        ),
                    ),
                ),
            )

        result = await self.runner.run_thread(
            "search_route_explanation",
            lambda signal: explain(
                keyword=keyword,
                understanding=understanding,
                result_count=result_count,
                cancellation=signal,
            ),
            timeout_seconds=(
                deadline.clamp(min(self.timeout_seconds, ROUTE_EXPLANATION_MAX_WAIT_SECONDS))
                if deadline is not None
                else min(self.timeout_seconds, ROUTE_EXPLANATION_MAX_WAIT_SECONDS)
            ),
            attempt_task="search_result_recommendation_reason",
            attempt_layer="搜索结果：命中卖点解释",
        )
        model_call = (
            result.value if isinstance(result.value, ModelCallResult) else None
        )
        attempts = (
            self._model_attempts(
                model_call.attempts,
                layer="搜索结果：命中卖点解释",
            )
            if model_call is not None
            else result.diagnostic.attempts
        )
        if result.diagnostic.status != "ok" or model_call is None:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source="search_route_explanation",
                    status=result.diagnostic.status,
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=0,
                    detail=(
                        result.diagnostic.detail
                        or "命中卖点解释 API 未完成，使用前端默认说明"
                    ),
                    attempts=attempts,
                ),
            )
        explanation = _clean_route_explanation(model_call.value.explanation)
        return SearchBranchResult(
            value=explanation or None,
            diagnostic=SearchBranchDiagnostic(
                source="search_route_explanation",
                status="ok" if explanation else "failed",
                duration_ms=result.diagnostic.duration_ms,
                result_count=1 if explanation else 0,
                detail="已生成搜索级命中卖点解释" if explanation else "模型未返回解释",
                attempts=attempts,
            ),
        )

    async def enrich(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        hits: list[SearchHit],
        results: list[ScoredImage],
        deadline: SearchDeadline | None = None,
    ) -> SearchBranchResult[list[ScoredImage]]:
        if not hits or not results:
            return self._skipped(
                results,
                "没有最终结果需要生成动态推荐理由",
            )

        candidates = [
            self._candidate_context(keyword, understanding, hit, result)
            for hit, result in zip(
                hits[: self.result_limit],
                results[: self.result_limit],
            )
        ]
        if (
            not isinstance(self.ai_service, ResultRecommendationCapabilities)
            or not self.ai_service.provider.configured
        ):
            return self._skipped(
                results,
                "动态推荐理由 API 未配置，保留本地确定性推荐理由",
            )
        if deadline is not None and deadline.expired:
            return self._skipped(
                results,
                "搜索总时间预算已到，保留本地确定性推荐理由",
                status="timed_out",
            )

        started = time.monotonic()
        result = await self.runner.run_thread(
            "result_recommendation_reason",
            lambda signal: self.ai_service.recommend_search_result_reasons(
                keyword=keyword,
                understanding=understanding,
                candidates=candidates,
                cancellation=signal,
            ),
            timeout_seconds=(
                deadline.clamp(self.timeout_seconds)
                if deadline is not None
                else self.timeout_seconds
            ),
            attempt_task="search_result_recommendation_reason",
            attempt_layer="第五层：动态推荐理由",
        )
        model_call = (
            result.value if isinstance(result.value, ModelCallResult) else None
        )
        attempts = (
            self._model_attempts(model_call.attempts)
            if model_call is not None
            else result.diagnostic.attempts
        )
        if result.diagnostic.status != "ok" or result.value is None:
            return SearchBranchResult(
                value=results,
                diagnostic=SearchBranchDiagnostic(
                    source="result_recommendation_reason",
                    status=result.diagnostic.status,
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=0,
                    detail=(
                        result.diagnostic.detail
                        or "动态推荐理由 API 未完成，保留本地确定性推荐理由"
                    ),
                    attempts=attempts
                    or (
                        self._synthetic_attempt(
                            result.diagnostic.status,
                            result.diagnostic.detail
                            or "动态推荐理由 API 未完成",
                        ),
                    ),
                ),
            )

        if model_call is None:
            detail = "动态推荐理由未返回正式模型结果，回退本地确定性推荐理由"
            return SearchBranchResult(
                value=results,
                diagnostic=SearchBranchDiagnostic(
                    source="result_recommendation_reason",
                    status="failed",
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=0,
                    detail=detail,
                    attempts=attempts or (self._synthetic_attempt("failed", detail),),
                ),
            )
        model_result = model_call.value
        candidate_ids = {item["image_id"] for item in candidates}
        returned_ids = [item.image_id for item in model_result.reasons]
        if (
            len(returned_ids) != len(set(returned_ids))
            or set(returned_ids) != candidate_ids
        ):
            detail = "动态推荐理由返回结果不完整或包含未知图片，回退本地确定性推荐理由"
            return SearchBranchResult(
                value=results,
                diagnostic=SearchBranchDiagnostic(
                    source="result_recommendation_reason",
                    status="failed",
                    duration_ms=result.diagnostic.duration_ms,
                    result_count=0,
                    detail=detail,
                    attempts=attempts
                    or (self._synthetic_attempt("failed", detail),),
                ),
            )
        generated = {
            item.image_id: item.reason.strip()
            for item in model_result.reasons
            if item.image_id in candidate_ids and item.reason.strip()
        }
        enriched = [
            item.model_copy(
                update={
                    "result_recommendation_reason": generated.get(
                        item.image.id,
                        item.result_recommendation_reason,
                    )
                }
            )
            for item in results
        ]
        missing = len(candidate_ids) - len(generated)
        detail = f"动态生成 {len(generated)} 张结果推荐理由"
        if missing:
            detail += f"，{missing} 张回退本地理由"
        return SearchBranchResult(
            value=enriched,
            diagnostic=SearchBranchDiagnostic(
                source="result_recommendation_reason",
                status="ok",
                duration_ms=max(result.diagnostic.duration_ms, _elapsed_ms(started)),
                result_count=len(generated),
                detail=detail,
                attempts=attempts
                or (
                    self._synthetic_attempt(
                        "ok",
                        "模型调用成功但未返回 Provider 遥测",
                    ),
                ),
            ),
        )

    def _candidate_context(
        self,
        keyword: str,
        understanding: SearchUnderstanding | None,
        hit: SearchHit,
        result: ScoredImage,
    ) -> dict:
        image = hit.image
        group = image.asset_group
        profile = self.scorer.semantic_profile.profile_from_image(image)
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
        return {
            "image_id": image.id,
            "query": keyword,
            "title": image.title,
            "asset_title": result.asset_title or image.title,
            "channel": image.channel,
            "style_label": group.style_label if group else None,
            "is_scene_image": group.is_scene_image if group else None,
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
            "matched_query_concepts": [
                item.model_dump(mode="json")
                for item in result.matched_query_concepts
            ],
            "proof_point": result.primary_proof_point_name,
            "evidence_point": result.primary_evidence_point_name,
            "match_reasons": list(hit.reasons),
            "current_reason": result.result_recommendation_reason,
            "understanding": (
                understanding.model_dump(mode="json") if understanding else None
            ),
        }

    def _model_attempts(
        self,
        attempts: tuple[dict, ...] | list[dict] | None,
        *,
        layer: str = "第五层：动态推荐理由",
    ) -> tuple[ModelAttemptDiagnostic, ...]:
        if not isinstance(attempts, (list, tuple)):
            return ()
        rows = []
        for item in attempts:
            if not isinstance(item, dict):
                continue
            rows.append(
                ModelAttemptDiagnostic(
                    task="search_result_recommendation_reason",
                    layer=layer,
                    provider=str(item.get("provider") or "unknown")[:120],
                    model=str(item.get("model") or "unknown")[:120],
                    status=str(item.get("status") or "unknown")[:24],
                    duration_ms=int(item.get("duration_ms") or 0),
                    fallback_index=(
                        int(item["fallback_index"])
                        if item.get("fallback_index") is not None
                        else None
                    ),
                    error=str(item.get("error") or "")[:300],
                )
            )
        return tuple(rows)

    def _skipped(
        self,
        results: list[ScoredImage],
        detail: str,
        *,
        status: BranchStatus = "skipped",
    ) -> SearchBranchResult[list[ScoredImage]]:
        return SearchBranchResult(
            value=results,
            diagnostic=SearchBranchDiagnostic(
                source="result_recommendation_reason",
                status=status,
                duration_ms=0,
                result_count=0,
                detail=detail,
                attempts=(self._synthetic_attempt("skipped", detail),),
            ),
        )

    @staticmethod
    def _synthetic_attempt(
        status: str,
        error: str,
        *,
        layer: str = "第五层：动态推荐理由",
    ) -> ModelAttemptDiagnostic:
        return ModelAttemptDiagnostic(
            task="search_result_recommendation_reason",
            layer=layer,
            provider="api_center",
            model="未调用",
            status=status,
            duration_ms=0,
            error=error[:300],
        )


def _clean_route_explanation(value: str) -> str:
    explanation = re.sub(r"\s+", " ", value).strip()
    if not explanation:
        return ""
    cutoff_indexes = [
        explanation.find(marker)
        for marker in _ROUTE_EXPLANATION_PROCESS_MARKERS
        if marker in explanation
    ]
    if cutoff_indexes:
        explanation = explanation[: min(cutoff_indexes)].strip()
    return explanation.rstrip("，,；; ")


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
