from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.contracts import (
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.normalizer import normalize_model_payload
from app.ai.skill_loader import build_task_prompt
from app.core.config import get_settings
from app.core.errors import AppError
from app.domain.ai_taxonomy import (
    BUSINESS_CONCEPT_CATALOG,
    BUSINESS_CONCEPT_CODES,
    CONTENT_TAG_DIMENSIONS,
)
from app.schemas.ai import (
    ImageAnalysisResult,
    ProviderStatus,
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

    def __init__(self, provider: ModelProvider):
        self.provider = provider

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
                prompt=build_task_prompt("image_content_analysis"),
                image_path=image_path,
            ),
            ImageAnalysisResult,
        )
        self._validate_image_analysis(result)
        return result

    def understand_search(self, keyword: str) -> SearchUnderstanding:
        return self._run(
            ModelRequest(
                task="search_intent_understanding",
                prompt=build_task_prompt("search_intent_understanding"),
                input_text=keyword,
            ),
            SearchUnderstanding,
        )

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
            return result_type.model_validate(normalize_model_payload(request, payload))
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

        tag_names = [item.tag.strip() for item in result.content_tags if item.tag.strip()]
        if not tag_names:
            raise AppError(
                "model_response_invalid",
                "模型至少需要返回一个有检索价值的客观内容标签",
                status_code=502,
            )
        if len(set(tag_names)) != len(tag_names):
            raise AppError(
                "model_response_invalid",
                "模型返回了重复的隐形内容标签",
                status_code=502,
            )

        unknown_dimensions = sorted(
            {
                item.dimension
                for item in result.content_tags
                if item.dimension and item.dimension not in CONTENT_TAG_DIMENSIONS
            }
        )
        if unknown_dimensions:
            raise AppError(
                "model_response_invalid",
                "模型返回了未知的隐形标签维度",
                status_code=502,
                details={"dimensions": unknown_dimensions},
            )

        coverage = {item.dimension for item in result.content_tags if item.dimension}
        profile = result.semantic_profile
        if profile.visual_facts:
            coverage.add("画面事实")
        if profile.ocr_text:
            coverage.add("OCR")
        if any([profile.subjects, profile.scenes, profile.actions, profile.visual_style]):
            coverage.add("结构化视觉")
        if len(coverage) < 2:
            raise AppError(
                "model_response_invalid",
                "图片分析需要覆盖至少两个客观语义维度",
                status_code=502,
                details={"coveredDimensions": sorted(coverage)},
            )

        unknown_concepts = sorted(
            f"{item.system_name} > {item.concept_name}"
            for item in result.concept_suggestions
            if (
                item.concept_code not in BUSINESS_CONCEPT_CODES
                and (item.system_name.strip(), item.concept_name.strip())
                not in BUSINESS_CONCEPT_CATALOG
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

        self._validate_recommended_search_words(result)
        self._validate_concept_suggestion_reasons(result)

    def _validate_recommended_search_words(self, result: ImageAnalysisResult) -> None:
        words = [word.strip() for word in result.recommended_search_words if word.strip()]
        if len(words) > 12:
            raise AppError(
                "model_response_invalid",
                "模型返回的素材搜索短语不能超过 12 个",
                status_code=502,
                details={"recommendedSearchWordCount": len(words)},
            )
        if len(set(words)) != len(words):
            raise AppError(
                "model_response_invalid",
                "模型返回了重复的推荐搜索词",
                status_code=502,
            )
        if any(len(word) > 40 for word in words):
            raise AppError(
                "model_response_invalid",
                "推荐搜索词应保持为可检索的短词或短语",
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
