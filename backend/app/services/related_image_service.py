from __future__ import annotations

from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique


class RelatedImageService:
    """Ranks detail-page recommendations by business intent and semantic profile."""

    def __init__(
        self,
        repo: ImageRepository,
        semantic_profile: ImageSemanticProfileService | None = None,
    ):
        self.repo = repo
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()

    def related_images(self, image: Image, limit: int = 8) -> list[Image]:
        candidates = self._candidate_images(image, max(limit * 8, 32))
        scored = [
            (candidate, self._similarity_score(image, candidate))
            for candidate in candidates
            if candidate.id != image.id
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
            for candidate in self.repo.list(
                None,
                None,
                None,
                limit,
                "createdAt",
            ):
                candidates_by_id[candidate.id] = candidate
        return list(candidates_by_id.values())

    def _candidate_terms(self, image: Image) -> list[str]:
        links = self._concept_links(image)
        content_tags = sorted(
            image.content_tags,
            key=lambda item: item.confidence,
            reverse=True,
        )
        return unique(
            [
                *(link.concept.name for link in links),
                *(link.concept.code for link in links),
                *(item.tag_name for item in content_tags[:8]),
            ]
        )

    def _similarity_score(self, source: Image, candidate: Image) -> float:
        source_links = self._concept_links(source)
        candidate_links = self._concept_links(candidate)
        source_concepts = {link.concept_id for link in source_links}
        candidate_concepts = {link.concept_id for link in candidate_links}
        shared_concepts = source_concepts & candidate_concepts
        score = 0.0
        if shared_concepts:
            trusted = any(
                link.concept_id in shared_concepts
                and link.review_status == "accepted"
                and link.origin in {"manual", "migrated"}
                for link in candidate_links
            )
            score += 1.0 if trusted else 0.72

        source_systems = {
            system.system_tag_id
            for link in source_links
            for system in link.concept.system_links
            if system.status == "active"
        }
        candidate_systems = {
            system.system_tag_id
            for link in candidate_links
            for system in link.concept.system_links
            if system.status == "active"
        }
        if source_systems & candidate_systems:
            score += 0.18

        source_content = {item.tag_name for item in source.content_tags}
        candidate_content = {item.tag_name for item in candidate.content_tags}
        shared_content_count = len(source_content & candidate_content)
        score += min(shared_content_count * 0.04, 0.28)

        if source.channel and source.channel == candidate.channel:
            score += 0.08
        return score

    def _concept_links(self, image: Image):
        return [
            link
            for link in (image.asset_group.concept_links if image.asset_group else [])
            if link.review_status != "rejected" and link.relation_role != "excludes"
        ]

    def _concept_ids(self, image: Image) -> list[str]:
        return list(dict.fromkeys(link.concept_id for link in self._concept_links(image)))
