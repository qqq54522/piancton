from __future__ import annotations

from typing import Literal

from app.models.image import Image
from app.schemas.image import ScoredImage
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.serializers import image_to_read


class SearchScorer:
    def __init__(self, semantic_profile: ImageSemanticProfileService | None = None):
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()

    def build_scored_image(
        self,
        image: Image,
        needle: str,
        external_score: float | None,
        external_reasons: list[str],
    ) -> ScoredImage:
        tag_names = [link.tag.name for link in image.tag_links]
        content_tag_names = [item.tag_name for item in image.content_tags]
        category_names = [item.category_name for item in image.level2_categories]
        business_labels = [
            label for label in image.business_labels if label.review_status != "rejected"
        ]
        business_label_names = [
            self.semantic_profile.business_label_name(label) for label in business_labels
        ]
        business_label_codes = [label.label_code for label in business_labels]

        title = image.title.lower()
        exact_title = bool(needle and (needle in title or title in needle))
        summary = image.image_summary.lower() if image.image_summary else ""
        summary_match = bool(
            needle
            and summary
            and (needle in summary or summary in needle)
        )
        matched_tags = self._matching_names(needle, tag_names + content_tag_names)
        matched_categories = self._matching_names(
            needle,
            category_names + business_label_names + business_label_codes,
        )

        reasons = list(external_reasons)
        if exact_title:
            reasons.append("标题匹配")
        if matched_tags:
            reasons.append("标签匹配")
        if matched_categories:
            reasons.append("业务标签匹配")
        if summary_match:
            reasons.append("图片摘要匹配")
        if not reasons:
            reasons.append("搜索索引匹配")

        score_candidates = [
            score
            for score in (
                external_score,
                1.0 if exact_title else None,
                0.9 if summary_match else None,
                0.86 if matched_categories else None,
                0.8 if matched_tags else None,
            )
            if score is not None
        ]
        score = max(score_candidates) if score_candidates else 0.65
        score = max(0.0, min(score, 1.0))

        return ScoredImage(
            image=image_to_read(image),
            match_level=self.match_level(score),
            final_score=score,
            match_reasons=unique(reasons),
            matched_level1_tags=matched_tags,
            matched_level2_categories=matched_categories,
        )

    def match_level(self, score: float) -> Literal["S", "A", "B", "C"]:
        if score >= 0.95:
            return "S"
        if score >= 0.8:
            return "A"
        if score >= 0.65:
            return "B"
        return "C"

    def _matching_names(self, needle: str, names: list[str]) -> list[str]:
        if not needle:
            return []
        return unique([name for name in names if needle in name.lower()])
