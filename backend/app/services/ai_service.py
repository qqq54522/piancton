from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, cast

from pydantic import BaseModel, ValidationError

from app.ai.contracts import (
    CancellationSignal,
    ModelCallResult,
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelProviderValidationError,
    ModelRequest,
)
from app.ai.knowledge import AiKnowledge
from app.ai.normalizer import normalize_model_payload
from app.ai.skill_loader import (
    build_candidate_review_prompt,
    build_proof_point_prompt,
    build_result_recommendation_reason_prompt,
    build_search_route_explanation_prompt,
    build_selling_point_prompt,
    build_system_routing_prompt,
    build_task_prompt,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.ai_taxonomy import (
    BUSINESS_CONCEPT_CATALOG,
    BUSINESS_CONCEPT_CODES,
)
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.schemas.ai import (
    ImageAnalysisResult,
    ProviderStatus,
    SearchCandidateReviewResult,
    SearchEvidencePointMatch,
    SearchProofPointMatch,
    SearchProofPointUnderstanding,
    SearchResultRecommendationReasonResult,
    SearchRouteExplanationResult,
    SearchSystemRouting,
    SearchUnderstanding,
    SellingPointMatchResult,
)

ResultModel = TypeVar("ResultModel", bound=BaseModel)

SECONDARY_REASON_BOUNDARY_MARKERS = (
    "不是",
    "而非",
    "区别",
    "排除",
    "不属于",
    "避免误判",
    "相近",
    "未体现",
)


class AiService:
    """Model-neutral entry point for every AI task."""

    def __init__(
        self,
        provider: ModelProvider,
        knowledge: AiKnowledge | None = None,
        *,
        system_routing_timeout_seconds: float | None = None,
        selling_point_timeout_seconds: float | None = None,
        proof_point_timeout_seconds: float | None = None,
        candidate_review_timeout_seconds: float | None = None,
    ):
        # D027：knowledge 携带数据库当前启用卖点；缺省时回退静态种子目录。
        self.provider = provider
        self.knowledge = knowledge
        self.system_routing_timeout_seconds = system_routing_timeout_seconds
        self.selling_point_timeout_seconds = selling_point_timeout_seconds
        self.proof_point_timeout_seconds = proof_point_timeout_seconds
        self.candidate_review_timeout_seconds = candidate_review_timeout_seconds

    def provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider=self.provider.name,
            configured=self.provider.configured,
            model_name=get_settings().model_name,
        )

    def analyze_image(self, image_path: Path) -> ModelCallResult[ImageAnalysisResult]:
        call = self._run(
            ModelRequest(
                task="image_content_analysis",
                prompt=build_task_prompt(
                    "image_content_analysis",
                    catalog_text=self._catalog_text(),
                ),
                image_path=image_path,
            ),
            ImageAnalysisResult,
        )
        try:
            self._validate_image_analysis(call.value)
        except AppError as exc:
            exc.attempts = call.attempts
            raise
        return call

    def understand_search(
        self,
        keyword: str,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchUnderstanding]:
        routing = self.route_search_system(keyword, cancellation=cancellation)
        understanding = self.understand_search_from_route(
            keyword,
            routing.value,
            cancellation=cancellation,
        )
        return ModelCallResult(
            understanding.value,
            (*routing.attempts, *understanding.attempts),
        )

    def route_search_system(
        self,
        keyword: str,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchSystemRouting]:
        return self._run(
            ModelRequest(
                task="search_system_routing",
                prompt=build_system_routing_prompt(),
                input_text=keyword,
                timeout_seconds=self.system_routing_timeout_seconds,
                cancellation=cancellation,
            ),
            SearchSystemRouting,
        )

    def understand_search_from_route(
        self,
        keyword: str,
        routing: SearchSystemRouting,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchUnderstanding]:
        selling_points = self.understand_selling_points_from_route(
            keyword,
            routing,
            cancellation=cancellation,
        )
        proof_points = self.understand_proof_points(
            keyword,
            selling_points.value,
            cancellation=cancellation,
        )
        return ModelCallResult(
            proof_points.value,
            (*selling_points.attempts, *proof_points.attempts),
        )

    def understand_selling_points_from_route(
        self,
        keyword: str,
        routing: SearchSystemRouting,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchUnderstanding]:
        system_codes = self._validated_routed_system_codes(routing)
        if not system_codes:
            query_type = (
                "visual_scene_search"
                if routing.route_type == "visual_scene"
                else "no_reliable_intent_search"
            )
            return ModelCallResult(
                SearchUnderstanding(
                    original_query=keyword,
                    normalized_query=keyword.strip(),
                    search_intent=(
                        "查询只包含画面或版式要求"
                        if query_type == "visual_scene_search"
                        else "未识别到可靠业务体系"
                    ),
                    query_type=query_type,
                    expanded_terms=[],
                    matched_business_concepts=[],
                    excluded_concepts=[],
                    search_strategy="不执行卖点硬路由",
                ),
                (),
            )
        call = self._run(
            ModelRequest(
                task="search_intent_understanding",
                prompt=build_selling_point_prompt(
                    system_codes,
                    catalog_text=self._catalog_text_for_systems(system_codes),
                ),
                input_text=(
                    f"第一层候选体系：{', '.join(system_codes)}\n"
                    f"原始查询：{keyword}"
                ),
                timeout_seconds=self.selling_point_timeout_seconds,
                cancellation=cancellation,
            ),
            SearchUnderstanding,
        )
        result = call.value
        try:
            self._validate_routed_concepts(result, system_codes)
        except AppError as exc:
            exc.attempts = call.attempts
            raise
        return ModelCallResult(self._with_scoped_proof_point_hints(result), call.attempts)

    def understand_proof_points(
        self,
        keyword: str,
        selling_points: SearchUnderstanding,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchUnderstanding]:
        concept_codes = self._matched_concept_codes(selling_points)
        if not concept_codes:
            return ModelCallResult(selling_points, ())
        available_proofs = {
            item.concept_code for item in load_proof_point_catalog().points
        }
        concept_codes = tuple(
            code for code in concept_codes if code in available_proofs
        )
        if not concept_codes:
            return ModelCallResult(selling_points, ())
        call = self._run(
            ModelRequest(
                task="search_proof_point_understanding",
                prompt=build_proof_point_prompt(concept_codes),
                input_text=(
                    f"第二层已命中卖点：{', '.join(concept_codes)}\n"
                    f"原始查询：{keyword}"
                ),
                timeout_seconds=self.proof_point_timeout_seconds,
                cancellation=cancellation,
            ),
            SearchProofPointUnderstanding,
        )
        result = call.value
        proof_matches, evidence_matches = self._scoped_proof_point_matches(
            result.matched_proof_points,
            result.matched_evidence_points,
            concept_codes,
        )
        return ModelCallResult(
            selling_points.model_copy(
                update={
                    "matched_proof_points": proof_matches,
                    "matched_evidence_points": evidence_matches,
                    "search_strategy": (
                        result.search_strategy or selling_points.search_strategy
                    ),
                }
            ),
            call.attempts,
        )

    def review_search_candidates(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        candidates: list[dict],
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchCandidateReviewResult]:
        if not candidates:
            return ModelCallResult(SearchCandidateReviewResult(decisions=[]), ())
        payload = {
            "query": keyword,
            "understanding": (
                understanding.model_dump(mode="json") if understanding else None
            ),
            "candidates": candidates,
        }
        return self._run(
            ModelRequest(
                task="search_candidate_review",
                prompt=build_candidate_review_prompt(),
                input_text=json.dumps(payload, ensure_ascii=False),
                timeout_seconds=self.candidate_review_timeout_seconds,
                cancellation=cancellation,
            ),
            SearchCandidateReviewResult,
        )

    def recommend_search_result_reasons(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        candidates: list[dict],
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchResultRecommendationReasonResult]:
        if not candidates:
            return ModelCallResult(
                SearchResultRecommendationReasonResult(reasons=[]),
                (),
            )
        payload = {
            "query": keyword,
            "understanding": (
                understanding.model_dump(mode="json") if understanding else None
            ),
            "candidates": candidates,
        }
        return self._run(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt=build_result_recommendation_reason_prompt(),
                input_text=json.dumps(payload, ensure_ascii=False),
                cancellation=cancellation,
            ),
            SearchResultRecommendationReasonResult,
        )

    def explain_search_route(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        result_count: int,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[SearchRouteExplanationResult]:
        concept_matches = (
            understanding.matched_business_concepts if understanding else []
        )
        matched_selling_points = [item.concept for item in concept_matches]
        if not matched_selling_points:
            return ModelCallResult(SearchRouteExplanationResult(), ())
        payload = {
            "query": keyword,
            "matched_selling_points": [
                {
                    "name": item.concept,
                    "relation": item.relation,
                    "reason": item.reason,
                }
                for item in concept_matches
            ],
            "search_intent": understanding.search_intent if understanding else "",
            "query_type": understanding.query_type if understanding else "",
        }
        return self._run(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt=build_search_route_explanation_prompt(),
                input_text=json.dumps(payload, ensure_ascii=False),
                cancellation=cancellation,
            ),
            SearchRouteExplanationResult,
        )

    def routed_system_codes(
        self,
        routing: SearchSystemRouting,
    ) -> tuple[str, ...]:
        return self._validated_routed_system_codes(routing)

    def _validated_routed_system_codes(
        self,
        routing: SearchSystemRouting,
    ) -> tuple[str, ...]:
        if routing.route_type in {"visual_scene", "no_reliable_system"}:
            return ()
        ordered = sorted(
            routing.candidate_systems,
            key=lambda item: (item.relation != "primary", -item.weight),
        )
        limit = 3 if routing.route_type == "multi_system" else 2
        return tuple(dict.fromkeys(item.code for item in ordered[:limit]))

    def _catalog_text_for_systems(self, system_codes: tuple[str, ...]) -> str:
        catalog = load_taxonomy_catalog()
        active_codes = (
            self.knowledge.concept_codes
            if self.knowledge
            else frozenset(node.code for node in catalog.image_label_nodes)
        )
        runtime_contexts = (
            dict(self.knowledge.concept_prompt_contexts)
            if self.knowledge
            else {}
        )
        runtime_system_codes = (
            dict(self.knowledge.concept_system_codes)
            if self.knowledge
            else {
                concept.code: (concept.parent_code,)
                for concept in catalog.image_label_nodes
                if concept.parent_code
            }
        )
        lines = ["# 第一层候选体系内的当前启用卖点"]
        for system_code in system_codes:
            system = catalog.node_by_code[system_code]
            lines.append(f"\n## {system.code} / {system.name}")
            concept_codes = [
                code
                for code, linked_systems in runtime_system_codes.items()
                if code in active_codes and system_code in linked_systems
            ]
            for concept_code in concept_codes:
                concept = catalog.node_by_code.get(concept_code)
                context = runtime_contexts.get(concept_code)
                if context:
                    lines.append(context)
                    continue
                if concept is None:
                    continue
                lines.append(f"- `{concept.code}` / {concept.name}: {concept.definition}")
                if concept.aliases:
                    lines.append(f"  - 常见表达：{'、'.join(concept.aliases)}")
                if concept.positive_evidence:
                    lines.append(
                        f"  - 正向证据：{'、'.join(concept.positive_evidence)}"
                    )
                if concept.negative_evidence:
                    lines.append(
                        f"  - 排除边界：{'、'.join(concept.negative_evidence)}"
                    )
        lines.append("\n只能返回以上卖点的稳定 code，不得跨出第一层候选体系。")
        return "\n".join(lines)

    def _validate_routed_concepts(
        self,
        result: SearchUnderstanding,
        system_codes: tuple[str, ...],
    ) -> None:
        catalog = load_taxonomy_catalog()
        if self.knowledge:
            active_codes = self.knowledge.concept_codes
            system_by_concept = dict(self.knowledge.concept_system_codes)
            allowed_codes = {
                code
                for code, linked_systems in system_by_concept.items()
                if code in active_codes
                and any(system in linked_systems for system in system_codes)
            }
            display_names = dict(self.knowledge.concept_display_names)
        else:
            allowed_codes = {
                concept.code
                for system_code in system_codes
                for concept in catalog.children_of(system_code)
            }
            display_names = {}
            for code in allowed_codes:
                node = catalog.node_by_code[code]
                parent = catalog.node_by_code.get(node.parent_code or "")
                display_names[code] = (
                    f"{parent.name} > {node.name}" if parent else node.name
                )
        allowed_names = {
            display_names.get(
                code,
                catalog.node_by_code[code].name if code in catalog.node_by_code else code,
            )
            for code in allowed_codes
        }
        invalid = sorted(
            item.concept
            for item in result.matched_business_concepts
            if item.concept not in allowed_names
        )
        if invalid:
            raise AppError(
                "model_response_invalid",
                "第二层模型返回了候选体系之外的卖点",
                status_code=502,
                details={"concepts": invalid, "systems": list(system_codes)},
            )

    def _matched_concept_codes(
        self,
        result: SearchUnderstanding,
    ) -> tuple[str, ...]:
        catalog = load_taxonomy_catalog()
        active_codes = (
            self.knowledge.concept_codes
            if self.knowledge
            else frozenset(node.code for node in catalog.image_label_nodes)
        )
        display_names = (
            dict(self.knowledge.concept_display_names)
            if self.knowledge
            else {
                node.code: (
                    f"{catalog.node_by_code[node.parent_code].name} > {node.name}"
                    if node.parent_code
                    else node.name
                )
                for node in catalog.image_label_nodes
            }
        )
        code_by_name = {
            name: code for code, name in display_names.items() if code in active_codes
        }
        code_by_name.update(
            {
                catalog.node_by_code[code].name: code
                for code in active_codes
                if code in catalog.node_by_code
            }
        )
        codes = []
        for item in result.matched_business_concepts:
            code = (
                item.concept
                if item.concept in active_codes
                else code_by_name.get(item.concept)
            )
            if code and code not in codes:
                codes.append(code)
        return tuple(codes)

    def _with_scoped_proof_point_hints(
        self,
        result: SearchUnderstanding,
    ) -> SearchUnderstanding:
        if not result.matched_proof_points and not result.matched_evidence_points:
            return result
        concept_codes = self._matched_concept_codes(result)
        proof_matches, evidence_matches = self._scoped_proof_point_matches(
            result.matched_proof_points,
            result.matched_evidence_points,
            concept_codes,
        )
        return result.model_copy(
            update={
                "matched_proof_points": proof_matches,
                "matched_evidence_points": evidence_matches,
            }
        )

    @staticmethod
    def _scoped_proof_point_matches(
        proof_points: list[SearchProofPointMatch],
        evidence_points: list[SearchEvidencePointMatch],
        concept_codes: tuple[str, ...],
    ) -> tuple[list[SearchProofPointMatch], list[SearchEvidencePointMatch]]:
        allowed_concepts = set(concept_codes)
        if not allowed_concepts:
            return [], []
        proof_catalog = load_proof_point_catalog().by_code
        evidence_catalog = load_evidence_point_catalog().by_code

        scoped_proofs: list[SearchProofPointMatch] = []
        seen_proofs: set[str] = set()
        for item in proof_points:
            definition = proof_catalog.get(item.code)
            if definition is None or definition.concept_code not in allowed_concepts:
                continue
            if definition.code in seen_proofs:
                continue
            scoped_proofs.append(
                item.model_copy(
                    update={
                        "code": definition.code,
                        "concept_code": definition.concept_code,
                        "name": definition.name,
                        "evidence_terms": list(item.evidence_terms[:3]),
                    }
                )
            )
            seen_proofs.add(definition.code)

        scoped_evidence: list[SearchEvidencePointMatch] = []
        for item in evidence_points:
            definition = evidence_catalog.get(item.code)
            if definition is None or definition.concept_code not in allowed_concepts:
                continue
            proof = proof_catalog.get(definition.proof_point_code)
            if proof is None:
                continue
            if proof.code not in seen_proofs:
                scoped_proofs.append(
                    SearchProofPointMatch(
                        code=proof.code,
                        concept_code=proof.concept_code,
                        name=proof.name,
                        reason=f"由证据表达点反向定位：{definition.name}",
                        weight=item.weight,
                        evidence_terms=[definition.name],
                    )
                )
                seen_proofs.add(proof.code)
            scoped_evidence.append(
                item.model_copy(
                    update={
                        "code": definition.code,
                        "proof_point_code": definition.proof_point_code,
                        "concept_code": definition.concept_code,
                        "name": definition.name,
                    }
                )
            )
        active_proofs = {item.code for item in scoped_proofs}
        return scoped_proofs, [
            item for item in scoped_evidence if item.proof_point_code in active_proofs
        ]

    @staticmethod
    def _validate_proof_point_scope(
        result: SearchProofPointUnderstanding,
        concept_codes: tuple[str, ...],
    ) -> None:
        allowed = set(concept_codes)
        invalid_proofs = sorted(
            item.code
            for item in result.matched_proof_points
            if item.concept_code not in allowed
        )
        proof_codes = {item.code for item in result.matched_proof_points}
        invalid_evidence = sorted(
            item.code
            for item in result.matched_evidence_points
            if item.concept_code not in allowed
            or item.proof_point_code not in proof_codes
        )
        if invalid_proofs or invalid_evidence:
            raise AppError(
                "model_response_invalid",
                "第三层模型返回了已命中卖点之外的证明点",
                status_code=502,
                details={
                    "proof_points": invalid_proofs,
                    "evidence_points": invalid_evidence,
                    "concepts": list(concept_codes),
                },
            )

    def _catalog_text(self) -> str | None:
        return self.knowledge.catalog_text if self.knowledge else None

    def _concept_context(self, concept_code: str) -> str:
        code = concept_code.strip()
        if not code:
            return ""
        allowed_codes = (
            self.knowledge.concept_codes if self.knowledge else BUSINESS_CONCEPT_CODES
        )
        if code not in allowed_codes:
            raise AppError(
                "invalid_business_concept",
                "选择的主要卖点当前不可用",
                status_code=422,
            )
        if self.knowledge:
            display_name = dict(self.knowledge.concept_display_names).get(code)
            if display_name:
                return f"{code} / {display_name}"
        catalog = load_taxonomy_catalog()
        node = catalog.node_by_code.get(code)
        if node is None:
            return code
        parent = catalog.node_by_code.get(node.parent_code or "")
        display_name = f"{parent.name} > {node.name}" if parent else node.name
        return f"{code} / {display_name}"

    def _concept_prompt_context(self, concept_code: str) -> str:
        code = concept_code.strip()
        if not code:
            return ""
        if self.knowledge:
            context = dict(self.knowledge.concept_prompt_contexts).get(code)
            if context:
                return context
        node = load_taxonomy_catalog().node_by_code.get(code)
        if node is None:
            return ""
        lines = [f"- `{node.code}` / {node.name}: {node.definition}"]
        if node.aliases:
            lines.append(f"  - 常见表达：{'、'.join(node.aliases)}")
        if node.positive_evidence:
            lines.append(f"  - 正向证据：{'、'.join(node.positive_evidence)}")
        if node.negative_evidence:
            lines.append(f"  - 排除边界：{'、'.join(node.negative_evidence)}")
        return "\n".join(lines)

    def match_selling_points(
        self,
        copy: str,
    ) -> ModelCallResult[SellingPointMatchResult]:
        return self._run(
            ModelRequest(
                task="copy_selling_point_matching",
                prompt=build_task_prompt("copy_selling_point_matching"),
                input_text=copy,
            ),
            SellingPointMatchResult,
        )

    def _run(
        self,
        request: ModelRequest,
        result_type: type[ResultModel],
    ) -> ModelCallResult[ResultModel]:
        def validate(payload):
            return result_type.model_validate(
                normalize_model_payload(
                    request,
                    payload,
                    concept_display_names=(
                        dict(self.knowledge.concept_display_names)
                        if self.knowledge
                        else None
                    ),
                )
            )

        try:
            return cast(
                ModelCallResult[ResultModel],
                self.provider.generate_validated_json(request, validate),
            )
        except ModelProviderNotConfigured as exc:
            raise AppError(
                "provider_not_configured",
                str(exc),
                status_code=503,
                attempts=exc.attempts,
            ) from exc
        except ModelProviderValidationError as exc:
            if isinstance(exc.cause, ValidationError):
                raise AppError(
                    "model_response_invalid",
                    "模型返回内容不符合项目结构要求",
                    status_code=502,
                    details=exc.cause.errors(),
                    attempts=exc.attempts,
                ) from exc.cause
            raise AppError(
                "model_response_invalid",
                str(exc.cause),
                status_code=502,
                attempts=exc.attempts,
            ) from exc.cause
        except ModelProviderError as exc:
            raise AppError(
                "model_provider_error",
                str(exc),
                status_code=502,
                attempts=exc.attempts,
            ) from exc
        except ValidationError as exc:
            raise AppError(
                "model_response_invalid",
                "模型返回内容不符合项目结构要求",
                status_code=502,
                details=exc.errors(),
                attempts=(),
            ) from exc

    def _validate_image_analysis(self, result: ImageAnalysisResult) -> None:
        if not result.image_summary.strip():
            raise AppError(
                "model_response_invalid",
                "模型未返回有效的图片语义总结",
                status_code=502,
            )

        profile = result.semantic_profile
        visual_facts = [item.strip() for item in profile.visual_facts if item.strip()]
        if not visual_facts:
            raise AppError(
                "model_response_invalid",
                "模型至少需要返回一条可检索的画面事实",
                status_code=502,
            )
        self._validate_profile_items("画面事实", visual_facts, limit=6)
        self._validate_profile_items("场景", profile.scenes, limit=4)
        self._validate_profile_items(
            "素材独有搜索表达",
            profile.asset_search_phrases,
            limit=8,
            max_length=80,
        )

        allowed_codes = (
            self.knowledge.concept_codes if self.knowledge else BUSINESS_CONCEPT_CODES
        )
        allowed_pairs = (
            self.knowledge.concept_pairs if self.knowledge else BUSINESS_CONCEPT_CATALOG
        )
        unknown_concepts = sorted(
            f"{item.system_name} > {item.concept_name}"
            for item in result.concept_suggestions
            if (
                item.concept_code not in allowed_codes
                and (item.system_name.strip(), item.concept_name.strip())
                not in allowed_pairs
            )
        )
        if unknown_concepts:
            raise AppError(
                "unknown_concept_suggestions",
                "模型返回了封闭目录之外的业务概念建议",
                status_code=502,
                details={"concepts": unknown_concepts},
            )

        primary_count = sum(
            item.relation_role == "expresses" for item in result.concept_suggestions
        )
        if primary_count > 1 or len(result.concept_suggestions) > 3:
            raise AppError(
                "model_response_invalid",
                "业务概念建议最多包含一个主要表达和两个可以支持",
                status_code=502,
            )

        self._validate_concept_suggestion_reasons(result)

    def _validate_profile_items(
        self,
        label: str,
        values: list[str],
        *,
        limit: int,
        max_length: int = 120,
    ) -> None:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(cleaned) > limit:
            raise AppError(
                "model_response_invalid",
                f"模型返回的{label}不能超过 {limit} 条",
                status_code=502,
                details={"count": len(cleaned)},
            )
        if len(set(cleaned)) != len(cleaned):
            raise AppError(
                "model_response_invalid",
                f"模型返回了重复的{label}",
                status_code=502,
            )
        if any(len(value) > max_length for value in cleaned):
            raise AppError(
                "model_response_invalid",
                f"{label}应保持简洁、可检索",
                status_code=502,
            )

    def _validate_concept_suggestion_reasons(self, result: ImageAnalysisResult) -> None:
        weak_reasons = [
            f"{item.system_name} > {item.concept_name}"
            for item in result.concept_suggestions
            if not self._has_boundary_reason(item.reason)
        ]
        if weak_reasons:
            raise AppError(
                "model_response_invalid",
                "业务概念建议理由必须说明适配证据和相邻概念排除边界",
                status_code=502,
                details={"conceptSuggestions": weak_reasons},
            )

    def _has_boundary_reason(self, reason: str) -> bool:
        text = reason.strip()
        return bool(text) and any(
            marker in text for marker in SECONDARY_REASON_BOUNDARY_MARKERS
        )
