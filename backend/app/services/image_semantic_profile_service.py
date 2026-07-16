from __future__ import annotations

import json
from typing import Any

from app.models.image import Image
from app.schemas.ai import ImageAnalysisResult, ImageSemanticProfile
from app.services.query_expansion_service import unique


class ImageSemanticProfileService:
    def rerank_document(self, image: Image) -> str:
        profile = self.profile_from_image(image)
        group = image.asset_group
        concept_links = [
            link
            for link in (group.concept_links if group else [])
            if link.review_status != "rejected" and link.relation_role != "excludes"
        ]
        accepted_concepts = [
            link.concept
            for link in concept_links
            if link.review_status == "accepted"
        ]
        pending_concepts = [
            link.concept
            for link in concept_links
            if link.review_status == "pending"
        ]
        parts = [
            f"标题：{image.title}",
            f"语义总结：{image.image_summary}" if image.image_summary else "",
            self._profile_document(
                profile,
                search_phrases=self.semantic_search_phrases(image, profile=profile),
            ),
            "隐形标签：" + "、".join(item.tag_name for item in image.content_tags),
            "已确认业务概念："
            + "、".join(
                dict.fromkeys(
                    value
                    for concept in accepted_concepts
                    for value in (concept.name, concept.code)
                )
            ),
            "已确认概念搜索表达："
            + "、".join(
                dict.fromkeys(
                    phrase.phrase
                    for concept in accepted_concepts
                    for phrase in concept.search_phrases
                    if phrase.review_status == "accepted"
                )
            ),
            "AI待审核概念："
            + "、".join(dict.fromkeys(concept.name for concept in pending_concepts)),
            "素材独有搜索表达："
            + "、".join(
                phrase.phrase
                for phrase in (group.search_phrases if group else [])
                if phrase.review_status == "accepted"
            ),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def profile_completeness(self, image: Image) -> int:
        score = 0
        if image.title.strip():
            score += 1
        if image.semantic_profile_json:
            score += 1
        if image.image_summary and image.image_summary.strip():
            score += 1
        if image.content_tags:
            score += 1
        if image.asset_group and any(
            link.review_status == "accepted"
            for link in image.asset_group.concept_links
        ):
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
        return ImageSemanticProfile(
            schema_version=2,
            visual_facts=self._clean_list(
                [*profile.visual_facts] or [result.image_summary],
                limit=12,
            ),
            ocr_text=self._clean_list(profile.ocr_text, limit=30),
            subjects=self._clean_list(profile.subjects, limit=12),
            scenes=self._clean_list(profile.scenes, limit=12),
            actions=self._clean_list(profile.actions, limit=12),
            visual_style=self._clean_list(profile.visual_style, limit=12),
            visible_product_features=self._clean_list(
                profile.visible_product_features, limit=15
            ),
            asset_search_phrases=self._clean_list(
                [*profile.asset_search_phrases, *result.recommended_search_words], limit=20
            ),
            negative_visual_concepts=self._clean_list(
                profile.negative_visual_concepts, limit=12
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
        if not any([image.image_summary, image.content_tags]):
            return None
        return ImageSemanticProfile(
            schema_version=2,
            visual_facts=self._clean_list(
                [
                    image.image_summary or "",
                    *(item.tag_name for item in image.content_tags[:6]),
                ],
                limit=6,
            ),
            ocr_text=self._clean_list(
                [item.tag_name for item in image.content_tags if item.dimension == "文字"],
                limit=30,
            ),
            subjects=self._clean_list(
                [
                    item.tag_name
                    for item in image.content_tags
                    if item.dimension in {"人物", "物体"}
                ],
                limit=12,
            ),
            scenes=self._clean_list(
                [item.tag_name for item in image.content_tags if item.dimension == "场景"],
                limit=12,
            ),
            actions=self._clean_list(
                [item.tag_name for item in image.content_tags if item.dimension == "动作"],
                limit=12,
            ),
            visual_style=self._clean_list(
                [
                    item.tag_name
                    for item in image.content_tags
                    if item.dimension in {"视觉风格", "颜色"}
                ],
                limit=12,
            ),
            visible_product_features=self._clean_list(
                [item.tag_name for item in image.content_tags if item.dimension == "产品功能"],
                limit=15,
            ),
            asset_search_phrases=self._clean_list(
                [
                    *(
                        [
                            item.phrase
                            for item in image.asset_group.search_phrases
                            if item.review_status != "rejected"
                        ]
                        if image.asset_group
                        else []
                    ),
                ],
                limit=20,
            ),
            negative_visual_concepts=self._clean_list(
                [],
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
                *profile.ocr_text,
                *profile.subjects,
                *profile.scenes,
                *profile.actions,
                *profile.visual_style,
                *profile.visible_product_features,
                *self.semantic_search_phrases(image, profile=profile),
                *profile.negative_visual_concepts,
            ]
        )

    def semantic_search_phrases(
        self,
        image: Image,
        *,
        profile: ImageSemanticProfile | None = None,
    ) -> list[str]:
        resolved = profile or self.profile_from_image(image)
        if not resolved:
            return []
        rejected = {
            item.phrase.strip().casefold()
            for item in (
                image.asset_group.search_phrases
                if image.asset_group
                else []
            )
            if item.review_status == "rejected"
        }
        return [
            phrase
            for phrase in resolved.asset_search_phrases
            if phrase.strip().casefold() not in rejected
        ]

    def business_intent_from_image(self, image: Image) -> str:
        group = image.asset_group
        if not group:
            return ""
        accepted = [
            link
            for link in group.concept_links
            if link.review_status == "accepted"
            and link.relation_role in {"expresses", "supports"}
        ]
        primary = [link for link in accepted if link.relation_role == "expresses"]
        selected = primary or accepted
        if selected:
            return selected[0].concept.name
        return ""

    def _profile_document(
        self,
        profile: ImageSemanticProfile | None,
        *,
        search_phrases: list[str] | None = None,
    ) -> str:
        if not profile:
            return ""
        parts = [
            "画像事实：" + "、".join(profile.visual_facts),
            "OCR文字：" + "、".join(profile.ocr_text),
            "主体：" + "、".join(profile.subjects),
            "场景：" + "、".join(profile.scenes),
            "动作：" + "、".join(profile.actions),
            "视觉风格：" + "、".join(profile.visual_style),
            "可见产品功能：" + "、".join(profile.visible_product_features),
            "素材搜索表达："
            + "、".join(
                profile.asset_search_phrases
                if search_phrases is None
                else search_phrases
            ),
            "画面排除边界：" + "、".join(profile.negative_visual_concepts),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def _clean_list(self, values: list[Any], *, limit: int) -> list[str]:
        cleaned = [
            str(value).strip()
            for value in values
            if str(value or "").strip()
        ]
        return unique(cleaned)[:limit]
