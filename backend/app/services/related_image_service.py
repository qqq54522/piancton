from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal

from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.volc_ai_search_client import (
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

logger = logging.getLogger(__name__)

RecommendationPurpose = Literal[
    "same_selling_point",
    "visual_similar",
    "same_channel",
    "personalized",
]
RecommendationSource = Literal[
    "business_relations",
    "semantic_profile",
    "channel",
    "ai_search",
]


@dataclass(frozen=True)
class ImageRecommendationSection:
    purpose: RecommendationPurpose
    title: str
    description: str
    source: RecommendationSource
    images: list[Image]
    browse_channel: str | None = None


class RelatedImageService:
    """Builds purpose-specific detail recommendations without changing business facts."""

    def __init__(
        self,
        repo: ImageRepository,
        semantic_profile: ImageSemanticProfileService | None = None,
        *,
        ai_search_client: VolcAiSearchClient | None = None,
        ai_search_recommend_enabled: bool = False,
    ):
        self.repo = repo
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()
        self.ai_search_client = ai_search_client
        self.ai_search_recommend_enabled = ai_search_recommend_enabled

    def related_images(self, image: Image, limit: int = 8) -> list[Image]:
        """Legacy list kept for designer UI and older clients."""
        sections = self.recommendation_sections(image, limit=limit)
        related: list[Image] = []
        for section in sections:
            if section.purpose not in {"same_selling_point", "visual_similar"}:
                continue
            related.extend(section.images)
        return _dedupe_images(related)[:limit]

    def recommendation_sections(
        self,
        image: Image,
        *,
        user_id: str = "",
        personalize: bool = False,
        limit: int = 8,
    ) -> list[ImageRecommendationSection]:
        per_section_limit = max(1, min(limit, 12))
        candidate_limit = max(per_section_limit * 12, 64)
        candidates = [
            item
            for item in self._candidate_images(image, candidate_limit)
            if self._can_recommend(image, item)
        ]
        used_ids = {image.id}
        if image.asset_group:
            used_ids.update(item.id for item in image.asset_group.images)

        same_selling_point = self._rank_same_selling_point(
            image,
            candidates,
            per_section_limit,
        )
        used_ids.update(item.id for item in same_selling_point)

        # Reserve personalized results before filling the broader local pools, so
        # a small library does not make the AI Search section disappear entirely.
        personalized = self._personalized_images(
            image,
            user_id=user_id,
            enabled=personalize,
            excluded_ids=used_ids,
            limit=per_section_limit,
        )
        used_ids.update(item.id for item in personalized)

        visual_similar = self._rank_visual_similar(
            image,
            [item for item in candidates if item.id not in used_ids],
            per_section_limit,
        )
        used_ids.update(item.id for item in visual_similar)

        channels = _split_channels(image.channel)
        primary_channel = channels[0] if channels else ""
        same_channel = self._same_channel_images(
            image,
            primary_channel,
            used_ids,
            per_section_limit,
        )
        used_ids.update(item.id for item in same_channel)

        sections = [
            ImageRecommendationSection(
                purpose="same_selling_point",
                title="同卖点可替换",
                description="与当前素材支撑同一卖点，适合换一种表达。",
                source="business_relations",
                images=same_selling_point,
            ),
            ImageRecommendationSection(
                purpose="visual_similar",
                title="相似画面与主题",
                description="画面或语义更接近，但不代表它们属于同一卖点。",
                source="semantic_profile",
                images=visual_similar,
            ),
            ImageRecommendationSection(
                purpose="same_channel",
                title=f"{primary_channel}适配素材" if primary_channel else "同渠道素材",
                description="保持使用位置一致，继续比较其它内容方向。",
                source="channel",
                images=same_channel,
                browse_channel=primary_channel or None,
            ),
        ]
        if personalized:
            sections.append(
                ImageRecommendationSection(
                    purpose="personalized",
                    title="为你推荐",
                    description="由火山推荐结合你的查看、点击和下载行为持续调整。",
                    source="ai_search",
                    images=personalized,
                )
            )
        return [section for section in sections if section.images]

    def _candidate_images(self, image: Image, limit: int) -> list[Image]:
        candidates_by_id: dict[str, Image] = {}
        concept_ids = self._concept_ids(image)
        for candidate in self.repo.search_by_concept_ids(concept_ids, limit=limit):
            candidates_by_id[candidate.id] = candidate
        for term in self._candidate_terms(image):
            for candidate in self.repo.search(term, limit):
                candidates_by_id[candidate.id] = candidate
            if len(candidates_by_id) >= limit:
                break
        if len(candidates_by_id) < limit:
            for candidate in self.repo.list_published_current(limit=limit):
                candidates_by_id[candidate.id] = candidate
        return list(candidates_by_id.values())

    def _candidate_terms(self, image: Image) -> list[str]:
        links = self._concept_links(image)
        return unique(
            [
                *(link.concept.name for link in links),
                *(link.concept.code for link in links),
                *self._semantic_terms(image),
            ]
        )

    def _rank_same_selling_point(
        self,
        source: Image,
        candidates: list[Image],
        limit: int,
    ) -> list[Image]:
        source_roles = {
            link.concept_id: link.relation_role
            for link in self._accepted_business_links(source)
        }
        if not source_roles:
            return []
        scored: list[tuple[Image, float]] = []
        for candidate in candidates:
            candidate_roles = {
                link.concept_id: link.relation_role
                for link in self._accepted_business_links(candidate)
            }
            shared = set(source_roles) & set(candidate_roles)
            if not shared:
                continue
            score = max(
                _business_relation_weight(source_roles[item])
                + _business_relation_weight(candidate_roles[item])
                for item in shared
            )
            scored.append((candidate, score))
        scored.sort(
            key=lambda item: (
                item[1],
                self.semantic_profile.profile_completeness(item[0]),
                item[0].created_at,
            ),
            reverse=True,
        )
        return [candidate for candidate, _score in scored[:limit]]

    def _rank_visual_similar(
        self,
        source: Image,
        candidates: list[Image],
        limit: int,
    ) -> list[Image]:
        scored = [
            (candidate, self._visual_similarity_score(source, candidate))
            for candidate in candidates
        ]
        scored = [(candidate, score) for candidate, score in scored if score > 0]
        scored.sort(
            key=lambda item: (
                item[1],
                self.semantic_profile.profile_completeness(item[0]),
                item[0].created_at,
            ),
            reverse=True,
        )
        return [candidate for candidate, _score in scored[:limit]]

    def _same_channel_images(
        self,
        source: Image,
        channel: str,
        excluded_ids: set[str],
        limit: int,
    ) -> list[Image]:
        if not channel:
            return []
        return [
            candidate
            for candidate in self.repo.list_published_current(limit=max(limit * 10, 50))
            if candidate.id not in excluded_ids
            and self._can_recommend(source, candidate)
            and channel in _split_channels(candidate.channel)
        ][:limit]

    def _personalized_images(
        self,
        source: Image,
        *,
        user_id: str,
        enabled: bool,
        excluded_ids: set[str],
        limit: int,
    ) -> list[Image]:
        client = self.ai_search_client
        if not (
            enabled
            and user_id
            and self.ai_search_recommend_enabled
            and client is not None
            and client.recommend_configured
        ):
            return []
        try:
            image_ids = client.recommend_items(
                user_id=user_id,
                parent_item_id=source.id,
                page_size=max(limit * 3, 12),
            )
        except VolcAiSearchClientError:
            logger.warning("AI Search detail recommendation failed", exc_info=True)
            return []
        return [
            candidate
            for candidate in self.repo.get_many_by_ids(image_ids)
            if candidate.id not in excluded_ids and self._can_recommend(source, candidate)
        ][:limit]

    def _visual_similarity_score(self, source: Image, candidate: Image) -> float:
        source_semantics = set(self._semantic_terms(source))
        candidate_semantics = set(self._semantic_terms(candidate))
        score = min(len(source_semantics & candidate_semantics) * 0.24, 0.72)
        source_group = source.asset_group
        candidate_group = candidate.asset_group
        if (
            source_group
            and candidate_group
            and source_group.style_label
            and source_group.style_label == candidate_group.style_label
        ):
            score += 0.18
        if (
            source_group
            and candidate_group
            and source_group.is_scene_image is not None
            and source_group.is_scene_image == candidate_group.is_scene_image
        ):
            score += 0.08
        if source.aspect_ratio and candidate.aspect_ratio:
            ratio_gap = abs(source.aspect_ratio - candidate.aspect_ratio)
            if ratio_gap <= 0.12:
                score += 0.12
            elif ratio_gap <= 0.35:
                score += 0.05
        return score

    def _can_recommend(self, image: Image, candidate: Image) -> bool:
        return bool(
            candidate.id != image.id
            and candidate.deleted_at is None
            and candidate.is_current
            and (
                candidate.asset_group is None
                or candidate.asset_group.publish_status == "published"
            )
            and (
                image.asset_group_id is None
                or candidate.asset_group_id != image.asset_group_id
            )
        )

    def _concept_links(self, image: Image):
        return [
            link
            for link in (image.asset_group.concept_links if image.asset_group else [])
            if link.review_status != "rejected" and link.relation_role != "excludes"
        ]

    def _accepted_business_links(self, image: Image):
        return [
            link
            for link in (image.asset_group.concept_links if image.asset_group else [])
            if link.review_status == "accepted"
            and link.relation_role in {"expresses", "supports"}
        ]

    def _concept_ids(self, image: Image) -> list[str]:
        return list(dict.fromkeys(link.concept_id for link in self._concept_links(image)))

    def _semantic_terms(self, image: Image) -> list[str]:
        group = image.asset_group
        return unique(
            [
                *self.semantic_profile.profile_terms(image),
                *(
                    item.phrase
                    for item in (group.search_phrases if group else [])
                    if item.review_status == "accepted"
                ),
            ]
        )


def _business_relation_weight(role: str) -> float:
    return 1.0 if role == "expresses" else 0.72


def _split_channels(value: str | None) -> list[str]:
    return [item.strip() for item in re.split(r"[、,，/／]", value or "") if item.strip()]


def _dedupe_images(images: list[Image]) -> list[Image]:
    seen: set[str] = set()
    result: list[Image] = []
    for image in images:
        if image.id in seen:
            continue
        seen.add(image.id)
        result.append(image)
    return result
