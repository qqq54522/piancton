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
    CONTENT_TAG_DIMENSIONS,
    SECONDARY_LABEL_CATALOG,
    SECONDARY_LABEL_CODES,
)
from app.schemas.ai import (
    ImageAnalysisResult,
    ProviderStatus,
    SearchUnderstanding,
    SellingPointMatchResult,
)

ResultModel = TypeVar("ResultModel", bound=BaseModel)


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
        if not 18 <= len(tag_names) <= 22:
            raise AppError(
                "model_response_invalid",
                "模型必须返回 18 到 22 个隐形内容标签",
                status_code=502,
                details={"contentTagCount": len(tag_names)},
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

        unknown_labels = sorted(
            f"{item.system} > {item.label}"
            for item in result.secondary_labels
            if (
                item.label_code not in SECONDARY_LABEL_CODES
                and (item.system.strip(), item.label.strip()) not in SECONDARY_LABEL_CATALOG
            )
        )
        if unknown_labels:
            raise AppError(
                "unknown_secondary_labels",
                "模型返回了封闭目录之外的自动匹配标签",
                status_code=502,
                details={"labels": unknown_labels},
            )

        primary_count = sum(item.role == "primary" for item in result.secondary_labels)
        if primary_count > 1 or len(result.secondary_labels) > 3:
            raise AppError(
                "model_response_invalid",
                "自动匹配最多包含一个主标签和两个副标签",
                status_code=502,
            )
