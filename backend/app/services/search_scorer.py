from __future__ import annotations

from typing import Literal

from app.models.image import Image
from app.schemas.image import ScoredImage, SearchResultConceptMatch
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_asset_presenter import SearchAssetPresenter
from app.services.serializers import image_to_read


class SearchScorer:
    def __init__(
        self,
        asset_presenter: SearchAssetPresenter | None = None,
    ):
        self.asset_presenter = asset_presenter or SearchAssetPresenter()
        self.semantic_profile = ImageSemanticProfileService()

    def build_scored_image(
        self,
        image: Image,
        needle: str,
        external_score: float | None,
        external_reasons: list[str],
        query_concept_ids: set[str] | None = None,
    ) -> ScoredImage:
        semantic_terms = self.semantic_profile.profile_terms(image)
        concept_links = [
            link
            for link in (image.asset_group.concept_links if image.asset_group else [])
            if link.review_status != "rejected" and link.relation_role != "excludes"
        ]

        title = image.title.lower()
        exact_title = bool(needle and (needle in title or title in needle))
        summary = image.image_summary.lower() if image.image_summary else ""
        summary_match = bool(needle and summary and (needle in summary or summary in needle))
        matched_content = self._matching_names(needle, semantic_terms)
        matched_concepts = self._matching_concepts(needle, concept_links)

        reasons = list(external_reasons)
        if exact_title:
            reasons.append("标题匹配")
        if matched_content:
            reasons.append("素材语义匹配")
        if matched_concepts:
            reasons.append("业务概念匹配")
        if summary_match:
            reasons.append("图片摘要匹配")
        if not reasons:
            reasons.append("搜索索引匹配")

        concept_score = self._concept_score(needle, concept_links)
        score_candidates = [
            score
            for score in (
                external_score,
                1.0 if exact_title else None,
                0.9 if summary_match else None,
                concept_score,
                0.8 if matched_content else None,
            )
            if score is not None
        ]
        score = max(score_candidates) if score_candidates else 0.65
        score = max(0.0, min(score, 1.0))

        asset = self.asset_presenter.present(image)
        matched_query_concepts = self._matched_query_concepts(
            concept_links,
            query_concept_ids or set(),
        )
        return ScoredImage(
            image=image_to_read(image),
            match_level=self.match_level(score),
            final_score=score,
            match_reasons=unique(reasons),
            matched_content_terms=matched_content,
            matched_business_concepts=matched_concepts,
            asset_group_id=asset.group_id,
            asset_title=asset.title,
            available_variants=list(asset.variants),
            expressed_concepts=list(asset.expressed_concepts),
            supported_concepts=list(asset.supported_concepts),
            matched_query_concepts=matched_query_concepts,
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

    def _matching_concepts(self, needle: str, links) -> list[str]:
        if not needle:
            return []
        matched: list[str] = []
        for link in links:
            names = [
                link.concept.code,
                link.concept.name,
                *(
                    phrase.phrase
                    for phrase in link.concept.search_phrases
                    if phrase.review_status == "accepted"
                ),
            ]
            if any(needle in name.lower() for name in names if name):
                matched.append(link.concept.name)
        return unique(matched)

    def _concept_score(self, needle: str, links) -> float | None:
        if not needle:
            return None
        scores: list[float] = []
        for link in links:
            names = [
                link.concept.code,
                link.concept.name,
                *(
                    phrase.phrase
                    for phrase in link.concept.search_phrases
                    if phrase.review_status == "accepted"
                ),
            ]
            if not any(needle in name.lower() for name in names if name):
                continue
            if link.review_status == "accepted" and link.origin in {"manual", "migrated"}:
                scores.append(0.96 if link.relation_role == "expresses" else 0.9)
            elif link.review_status == "accepted":
                scores.append(0.85)
            else:
                scores.append(0.72)
        return max(scores) if scores else None

    def _matched_query_concepts(
        self,
        links,
        query_concept_ids: set[str],
    ) -> list[SearchResultConceptMatch]:
        if not query_concept_ids:
            return []
        role_priority = {"expresses": 3, "supports": 2, "visual_related": 1}
        selected = {}
        for link in links:
            if (
                link.concept_id not in query_concept_ids
                or link.review_status != "accepted"
                or link.relation_role not in role_priority
            ):
                continue
            current = selected.get(link.concept_id)
            current_rank = (
                int(current.origin in {"manual", "migrated"}),
                role_priority[current.relation_role],
            ) if current else (-1, -1)
            candidate_rank = (
                int(link.origin in {"manual", "migrated"}),
                role_priority[link.relation_role],
            )
            if candidate_rank > current_rank:
                selected[link.concept_id] = link
        ordered = sorted(
            selected.values(),
            key=lambda link: role_priority[link.relation_role],
            reverse=True,
        )
        return [
            SearchResultConceptMatch(
                concept_code=link.concept.code,
                concept_name=link.concept.name,
                relation_role=link.relation_role,
            )
            for link in ordered
        ]
