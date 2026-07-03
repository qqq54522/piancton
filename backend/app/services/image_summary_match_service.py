from __future__ import annotations

from app.core.errors import AppError
from app.schemas.ai import ImageSummaryMatchItem, SearchUnderstanding
from app.services.ai_service import AiService
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_models import SearchHit


class ImageSummaryMatchService:
    """AI裁判：用图片语义总结二次判断强业务意图候选图。"""

    def __init__(
        self,
        ai_service: AiService | None,
        semantic_profile: ImageSemanticProfileService | None = None,
    ):
        self.ai_service = ai_service
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()

    def judge(
        self,
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if not self._should_judge(understanding, hits):
            return hits
        assert understanding is not None
        candidate_limit = min(len(hits), max(limit, 20))
        candidates = [
            hit for hit in hits[:candidate_limit] if (hit.image.image_summary or "").strip()
        ]
        if not candidates:
            return hits

        try:
            result = self.ai_service.match_image_summaries(  # type: ignore[union-attr]
                self._payload(keyword, understanding, candidates)
            )
        except AppError:
            return hits

        match_by_id = {item.image_id: item for item in result.matches}
        judged: list[SearchHit] = []
        for hit in hits[:candidate_limit]:
            match = match_by_id.get(hit.image.id)
            if match is None:
                judged.append(hit)
                continue
            next_hit = self._apply_match(hit, match)
            if next_hit is not None:
                judged.append(next_hit)
        judged.extend(hits[candidate_limit:])
        return judged

    def _should_judge(
        self,
        understanding: SearchUnderstanding | None,
        hits: list[SearchHit],
    ) -> bool:
        if not hits or not understanding:
            return False
        if understanding.query_type != "business_intent_search":
            return False
        if not understanding.normalized_query.strip():
            return False
        if not self.ai_service or not self.ai_service.provider.configured:
            return False
        return callable(getattr(self.ai_service, "match_image_summaries", None))

    def _payload(
        self,
        keyword: str,
        understanding: SearchUnderstanding,
        hits: list[SearchHit],
    ) -> dict:
        return {
            "query": keyword,
            "normalized_intent": understanding.normalized_query,
            "search_intent": understanding.search_intent,
            "target_categories": [
                item.category for item in understanding.matched_level2_categories
            ],
            "exclude_tags": understanding.exclude_tags,
            "candidates": [
                {
                    "image_id": hit.image.id,
                    "title": hit.image.title,
                    "business_labels": [
                        self.semantic_profile.business_label_name(label)
                        for label in self.semantic_profile.searchable_business_labels(hit.image)
                    ],
                    "image_summary": hit.image.image_summary or "",
                    "semantic_profile": (
                        profile.model_dump(mode="json")
                        if (profile := self.semantic_profile.profile_from_image(hit.image))
                        else None
                    ),
                    "content_tags": [item.tag_name for item in hit.image.content_tags],
                }
                for hit in hits
            ],
        }

    def _apply_match(
        self,
        hit: SearchHit,
        match: ImageSummaryMatchItem,
    ) -> SearchHit | None:
        if match.level == "X" or not match.matched:
            return None
        reasons = [*hit.reasons, f"语义总结裁判{match.level}：{match.reason}"]
        if match.negative_reason:
            reasons.append(f"语义总结边界：{match.negative_reason}")
        return SearchHit(
            image=hit.image,
            score=self._score_for_match(match),
            reasons=tuple(unique(reasons)),
        )

    def _score_for_match(self, match: ImageSummaryMatchItem) -> float:
        score = max(0.0, min(match.score, 1.0))
        if match.level == "S":
            return max(score, 0.95)
        if match.level == "A":
            return min(max(score, 0.8), 0.94)
        if match.level == "B":
            return min(max(score, 0.65), 0.79)
        return min(max(score, 0.4), 0.64)
