from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.contracts import (
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.knowledge import AiKnowledge
from app.ai.normalizer import normalize_model_payload
from app.ai.skill_loader import (
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
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.schemas.ai import (
    AssetSearchPhraseSuggestion,
    ImageAnalysisResult,
    ProviderStatus,
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
    ):
        # D027：knowledge 携带数据库当前启用卖点；缺省时回退静态种子目录。
        self.provider = provider
        self.knowledge = knowledge
        self.system_routing_timeout_seconds = system_routing_timeout_seconds
        self.selling_point_timeout_seconds = selling_point_timeout_seconds

    def provider_status(self) -> ProviderStatus:
        return ProviderStatus(
            provider=self.provider.name,
            configured=self.provider.configured,
            model_name=get_settings().model_name,
        )

    def analyze_image(self, image_path: Path) -> ImageAnalysisResult:
        result = self._run(
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
        self._validate_image_analysis(result)
        return result

    def generate_asset_search_phrases(
        self,
        image_path: Path,
        *,
        count: int,
        title: str = "",
        concept_code: str = "",
        image_media_type: str | None = None,
    ) -> AssetSearchPhraseSuggestion:
        if count < 2 or count > 5:
            raise AppError(
                "invalid_phrase_count",
                "AI 素材独有话术数量必须在 2～5 条之间",
                status_code=422,
            )
        concept_context = self._concept_context(concept_code)
        concept_prompt_context = self._concept_prompt_context(concept_code)
        context = [
            f"严格生成数量：{count} 条",
            (
                "输出角色：正在素材库中找图的业务人员，"
                "优先模拟不知道标准卖点名的业务小白"
            ),
            f"素材名称：{title.strip()}" if title.strip() else "",
            f"已选主要卖点：{concept_context}" if concept_context else "",
            (
                f"已选卖点业务边界：\n{concept_prompt_context}"
                if concept_prompt_context
                else ""
            ),
        ]
        result = self._run(
            ModelRequest(
                task="asset_search_phrase_generation",
                prompt=build_task_prompt("asset_search_phrase_generation"),
                input_text="\n".join(item for item in context if item),
                image_path=image_path,
                image_media_type=image_media_type,
            ),
            AssetSearchPhraseSuggestion,
        )
        cleaned = list(
            dict.fromkeys(item.strip() for item in result.phrases if item.strip())
        )
        self._validate_profile_items(
            "素材独有搜索表达",
            cleaned,
            limit=count,
            max_length=80,
        )
        if len(cleaned) != count:
            raise AppError(
                "model_response_invalid",
                f"模型需要返回正好 {count} 条素材独有话术",
                status_code=502,
                details={"expected": count, "actual": len(cleaned)},
            )
        return result.model_copy(update={"phrases": cleaned})

    def understand_search(self, keyword: str) -> SearchUnderstanding:
        routing = self.route_search_system(keyword)
        return self.understand_search_from_route(keyword, routing)

    def route_search_system(self, keyword: str) -> SearchSystemRouting:
        return self._run(
            ModelRequest(
                task="search_system_routing",
                prompt=build_system_routing_prompt(),
                input_text=keyword,
                timeout_seconds=self.system_routing_timeout_seconds,
            ),
            SearchSystemRouting,
        )

    def understand_search_from_route(
        self,
        keyword: str,
        routing: SearchSystemRouting,
    ) -> SearchUnderstanding:
        system_codes = self._validated_routed_system_codes(routing)
        if not system_codes:
            query_type = (
                "visual_scene_search"
                if routing.route_type == "visual_scene"
                else "no_reliable_intent_search"
            )
            return SearchUnderstanding(
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
            )
        result = self._run(
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
            ),
            SearchUnderstanding,
        )
        self._validate_routed_concepts(result, system_codes)
        return result

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
            display_names = {
                code: (
                    f"{catalog.node_by_code[catalog.node_by_code[code].parent_code].name}"
                    f" > {catalog.node_by_code[code].name}"
                )
                for code in allowed_codes
            }
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

    def match_selling_points(self, copy: str) -> SellingPointMatchResult:
        return self._run(
            ModelRequest(
                task="copy_selling_point_matching",
                prompt=build_task_prompt("copy_selling_point_matching"),
                input_text=copy,
            ),
            SellingPointMatchResult,
        )

    def _run(self, request: ModelRequest, result_type: type[ResultModel]) -> ResultModel:
        try:
            payload = self.provider.generate_json(request)
        except ModelProviderNotConfigured as exc:
            raise AppError(
                "provider_not_configured",
                str(exc),
                status_code=503,
            ) from exc
        except ModelProviderError as exc:
            raise AppError(
                "model_provider_error",
                str(exc),
                status_code=502,
            ) from exc
        try:
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
        except ValidationError as exc:
            raise AppError(
                "model_response_invalid",
                "模型返回内容不符合项目结构要求",
                status_code=502,
                details=exc.errors(),
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
