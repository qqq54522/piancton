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
            schema_version=3,
            visual_facts=self._clean_list(
                [*profile.visual_facts] or [result.image_summary],
                limit=6,
            ),
            scenes=self._clean_list(profile.scenes, limit=4),
            asset_search_phrases=self._clean_list(
                profile.asset_search_phrases,
                limit=8,
            ),
        )

    def profile_from_image(self, image: Image) -> ImageSemanticProfile | None:
        if image.semantic_profile_json:
            try:
                payload = json.loads(image.semantic_profile_json)
                if isinstance(payload, dict):
                    return self._profile_from_payload(payload, image.image_summary)
            except (TypeError, ValueError, json.JSONDecodeError):
                pass
        return self.fallback_profile_from_image(image)

    def fallback_profile_from_image(self, image: Image) -> ImageSemanticProfile | None:
        group = image.asset_group
        ai_phrases = [
            item.phrase
            for item in (group.search_phrases if group else [])
            if item.origin == "ai" and item.review_status != "rejected"
        ]
        if not any([image.image_summary, ai_phrases]):
            return None
        return ImageSemanticProfile(
            schema_version=3,
            visual_facts=self._clean_list(
                [image.image_summary or ""],
                limit=6,
            ),
            scenes=[],
            asset_search_phrases=self._clean_list(
                ai_phrases,
                limit=8,
            ),
        )

    def profile_terms(self, image: Image) -> list[str]:
        profile = self.profile_from_image(image)
        if not profile:
            return []
        return unique(
            [
                *profile.visual_facts,
                *profile.scenes,
                *self.semantic_search_phrases(image, profile=profile),
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
            "画面事实：" + "、".join(profile.visual_facts),
            "场景：" + "、".join(profile.scenes),
            "素材搜索表达："
            + "、".join(
                profile.asset_search_phrases
                if search_phrases is None
                else search_phrases
            ),
        ]
        return "\n".join(part for part in parts if part.strip() and not part.endswith("："))

    def _profile_from_payload(
        self,
        payload: dict[str, Any],
        image_summary: str | None,
    ) -> ImageSemanticProfile:
        visual_facts = payload.get("visual_facts")
        scenes = payload.get("scenes")
        asset_search_phrases = payload.get("asset_search_phrases")
        return ImageSemanticProfile(
            schema_version=3,
            visual_facts=self._clean_list(
                visual_facts if isinstance(visual_facts, list) else [image_summary or ""],
                limit=6,
            ),
            scenes=self._clean_list(
                scenes if isinstance(scenes, list) else [],
                limit=4,
            ),
            asset_search_phrases=self._clean_list(
                asset_search_phrases if isinstance(asset_search_phrases, list) else [],
                limit=8,
            ),
        )

    def _clean_list(self, values: list[Any], *, limit: int) -> list[str]:
        cleaned = [
            str(value).strip()
            for value in values
            if str(value or "").strip()
        ]
        return unique(cleaned)[:limit]
