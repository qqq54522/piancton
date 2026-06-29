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
        for term in self._candidate_terms(image):
            for candidate in self.repo.search(term, limit):
                candidates_by_id[candidate.id] = candidate
            if len(candidates_by_id) >= limit:
                break
        if len(candidates_by_id) < limit:
            tag_ids = [link.tag_id for link in image.tag_links]
            for candidate in self.repo.list(
                None,
                tag_ids,
                None,
                None,
                None,
                limit,
                "createdAt",
            ):
                candidates_by_id[candidate.id] = candidate
        return list(candidates_by_id.values())

    def _candidate_terms(self, image: Image) -> list[str]:
        labels = self.semantic_profile.searchable_business_labels(image)
        trusted_labels = [
            label
            for label in labels
            if self.semantic_profile.label_policy.is_trusted(label)
        ]
        pending_labels = [
            label
            for label in labels
            if self.semantic_profile.label_policy.is_pending_ai(label)
        ]
        content_tags = sorted(
            image.content_tags,
            key=lambda item: item.confidence,
            reverse=True,
        )
        return unique(
            [
                *self._label_terms(trusted_labels),
                *self._label_terms(pending_labels),
                *(link.tag.name for link in image.tag_links),
                *(item.category_name for item in image.level2_categories),
                *(item.tag_name for item in content_tags[:8]),
            ]
        )

    def _label_terms(self, labels) -> list[str]:
        terms: list[str] = []
        for label in labels:
            terms.extend(
                [
                    label.label_code,
                    label.tag.name,
                    self.semantic_profile.business_label_name(label),
                ]
            )
        return terms

    def _similarity_score(self, source: Image, candidate: Image) -> float:
        source_labels = self.semantic_profile.searchable_business_labels(source)
        candidate_labels = self.semantic_profile.searchable_business_labels(candidate)
        source_label_codes = {label.label_code for label in source_labels}
        candidate_label_codes = {label.label_code for label in candidate_labels}
        shared_codes = source_label_codes & candidate_label_codes
        score = 0.0
        if shared_codes:
            candidate_weight = max(
                self.semantic_profile.label_policy.label_weight(label)
                for label in candidate_labels
                if label.label_code in shared_codes
            )
            score += 1.0 * candidate_weight

        source_systems = {
            label.tag.parent.code
            for label in source_labels
            if label.tag.parent and label.tag.parent.code
        }
        candidate_systems = {
            label.tag.parent.code
            for label in candidate_labels
            if label.tag.parent and label.tag.parent.code
        }
        if source_systems & candidate_systems:
            score += 0.18

        source_tag_ids = {link.tag_id for link in source.tag_links}
        candidate_tag_ids = {link.tag_id for link in candidate.tag_links}
        if source_tag_ids & candidate_tag_ids:
            score += 0.32

        source_content = {item.tag_name for item in source.content_tags}
        candidate_content = {item.tag_name for item in candidate.content_tags}
        shared_content_count = len(source_content & candidate_content)
        score += min(shared_content_count * 0.04, 0.28)

        source_categories = {item.name for item in source.categories}
        candidate_categories = {item.name for item in candidate.categories}
        if source_categories & candidate_categories:
            score += 0.08
        return score
