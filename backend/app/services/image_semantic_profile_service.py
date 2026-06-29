from __future__ import annotations

import json
from typing import Any

from app.models.image import Image, ImageBusinessLabel
from app.schemas.ai import ImageAnalysisResult, ImageSemanticProfile
from app.services.business_label_policy import BusinessLabelPolicy
from app.services.query_expansion_service import unique


class ImageSemanticProfileService:
    def __init__(self, label_policy: BusinessLabelPolicy | None = None):
        self.label_policy = label_policy or BusinessLabelPolicy()

    def rerank_document(self, image: Image) -> str:
        profile = self.profile_from_image(image)
        parts = [
            f"标题：{image.title}",
            f"语义总结：{image.image_summary}" if image.image_summary else "",
            self._profile_document(profile),
            "隐形标签：" + "、".join(item.tag_name for item in image.content_tags),
            "业务标签："
            + "、".join(
                self.business_label_name(label)
                for label in image.business_labels
                if label.review_status != "rejected"
            ),
            "人工标签：" + "、".join(link.tag.name for link in image.tag_links),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def business_label_name(self, label: ImageBusinessLabel) -> str:
        return self.label_policy.display_name(label)

    def searchable_business_labels(self, image: Image) -> list[ImageBusinessLabel]:
        return [
            label for label in image.business_labels if self.label_policy.is_searchable(label)
        ]

    def profile_completeness(self, image: Image) -> int:
        score = 0
        if image.title.strip():
            score += 1
        if image.tag_links:
            score += 1
        if image.image_summary and image.image_summary.strip():
            score += 1
        if image.content_tags:
            score += 1
        if self.searchable_business_labels(image):
            score += 1
        if image.embedding:
            score += 1
        return score

    def profile_json_from_analysis(self, result: ImageAnalysisResult) -> str:
        profile = self.profile_from_analysis(result)
        return json.dumps(
            profile.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def profile_from_analysis(self, result: ImageAnalysisResult) -> ImageSemanticProfile:
        profile = result.semantic_profile
        business_intent = profile.business_intent.strip() or self._analysis_business_intent(result)
        return ImageSemanticProfile(
            visual_facts=self._clean_list(
                [*profile.visual_facts] or [result.image_summary],
                limit=6,
            ),
            business_intent=business_intent,
            search_phrases=self._clean_list(
                [*profile.search_phrases, *result.recommended_search_words],
                limit=12,
            ),
            exclusion_boundaries=self._clean_list(
                [*profile.exclusion_boundaries, *result.negative_tags],
                limit=10,
            ),
        )

    def profile_from_image(self, image: Image) -> ImageSemanticProfile | None:
        if image.semantic_profile_json:
            try:
                payload = json.loads(image.semantic_profile_json)
                return ImageSemanticProfile.model_validate(payload)
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return self.fallback_profile_from_image(image)

    def fallback_profile_from_image(self, image: Image) -> ImageSemanticProfile | None:
        if not any([image.image_summary, image.content_tags, image.business_labels]):
            return None
        return ImageSemanticProfile(
            visual_facts=self._clean_list(
                [
                    image.image_summary or "",
                    *(item.tag_name for item in image.content_tags[:6]),
                ],
                limit=6,
            ),
            business_intent=self._image_business_intent(image),
            search_phrases=self._clean_list(
                [
                    *(item.tag_name for item in image.content_tags if item.dimension == "业务卖点"),
                    *(item.tag_name for item in image.content_tags[:8]),
                ],
                limit=12,
            ),
            exclusion_boundaries=self._clean_list(
                [
                    label.reason or ""
                    for label in self.searchable_business_labels(image)
                    if label.reason
                ],
                limit=6,
            ),
        )

    def profile_terms(self, image: Image) -> list[str]:
        profile = self.profile_from_image(image)
        if not profile:
            return []
        return unique(
            [
                *profile.visual_facts,
                profile.business_intent,
                *profile.search_phrases,
                *profile.exclusion_boundaries,
            ]
        )

    def _analysis_business_intent(self, result: ImageAnalysisResult) -> str:
        labels = [
            item for item in result.secondary_labels if item.role == "primary"
        ] or result.secondary_labels[:1]
        if not labels:
            return ""
        label = labels[0]
        return f"{label.system} > {label.label}" if label.system.strip() else label.label

    def _image_business_intent(self, image: Image) -> str:
        labels = self.searchable_business_labels(image)
        primary = [
            label for label in labels if label.role == "primary"
        ] or labels[:1]
        if primary:
            return self.business_label_name(primary[0])
        if image.level2_categories:
            return image.level2_categories[0].category_name
        return ""

    def _profile_document(self, profile: ImageSemanticProfile | None) -> str:
        if not profile:
            return ""
        parts = [
            "画像事实：" + "、".join(profile.visual_facts),
            f"画像业务意图：{profile.business_intent}" if profile.business_intent else "",
            "画像适配搜索：" + "、".join(profile.search_phrases),
            "画像排除边界：" + "、".join(profile.exclusion_boundaries),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def _clean_list(self, values: list[Any], *, limit: int) -> list[str]:
        cleaned = [
            str(value).strip()
            for value in values
            if str(value or "").strip()
        ]
        return unique(cleaned)[:limit]
