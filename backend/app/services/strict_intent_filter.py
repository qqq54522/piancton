from __future__ import annotations

from app.models.image import Image
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_models import SearchHit, StrictSearchPolicy


class StrictIntentFilter:
    def __init__(self, semantic_profile: ImageSemanticProfileService | None = None):
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()

    def apply(
        self,
        hits: list[SearchHit],
        policy: StrictSearchPolicy | None,
    ) -> list[SearchHit]:
        if not policy or not policy.enabled:
            return hits
        strict_hits: list[SearchHit] = []
        for hit in hits:
            strict_hit = self._strict_hit(hit, policy)
            if strict_hit is None:
                continue
            strict_hits.append(strict_hit)
        return strict_hits

    def _strict_hit(
        self,
        hit: SearchHit,
        policy: StrictSearchPolicy,
    ) -> SearchHit | None:
        image = hit.image
        searchable_fields = [
            image.title,
            image.image_summary or "",
            " ".join(link.tag.name for link in image.tag_links),
            " ".join(item.tag_name for item in image.content_tags),
            " ".join(item.category_name for item in image.level2_categories),
            " ".join(
                self.semantic_profile.business_label_name(label)
                for label in self.semantic_profile.searchable_business_labels(image)
            ),
            " ".join(
                label.label_code
                for label in self.semantic_profile.searchable_business_labels(image)
            ),
        ]
        excluded_terms = [
            term
            for term in policy.exclude_terms
            if any(_contains_unnegated_concept(field, term) for field in searchable_fields)
        ]
        if excluded_terms:
            return None

        trusted_category_match = self._matches_primary_category(image, policy, trusted=True)
        trusted_label_match = self._matches_primary_label(image, policy, trusted=True)
        pending_category_match = self._matches_primary_category(
            image,
            policy,
            trusted=False,
        )
        pending_label_match = self._matches_primary_label(
            image,
            policy,
            trusted=False,
        )
        pending_match = (
            pending_category_match or pending_label_match
        ) and self._pending_match_has_semantic_support(image, policy)
        summary_match = bool(
            image.image_summary
            and _normalize(policy.primary_label) in _normalize(image.image_summary)
        )
        if not any([trusted_category_match, trusted_label_match, pending_match, summary_match]):
            return None

        reasons = list(hit.reasons)
        reasons.append(f"强意图业务话术匹配：{policy.intent_reason}")
        score_candidates = [score for score in [hit.score] if score is not None]
        if trusted_category_match:
            reasons.append(f"强意图主业务标签匹配：{policy.primary_category}")
            score_candidates.append(0.95)
        if trusted_label_match:
            reasons.append(f"强意图主标签匹配：{policy.primary_label}")
            score_candidates.append(0.92)
        if pending_match:
            reasons.append("待审核 AI 标签有语义证据支持")
            score_candidates.append(0.78)
        if summary_match:
            reasons.append(f"强意图语义总结匹配：{policy.primary_label}")
            score_candidates.append(0.82)
        reasons.append("强意图排除项检查通过")
        return SearchHit(
            image=image,
            score=max(score_candidates) if score_candidates else 0.82,
            reasons=tuple(unique(reasons)),
        )

    def _matches_primary_category(
        self,
        image: Image,
        policy: StrictSearchPolicy,
        *,
        trusted: bool,
    ) -> bool:
        labels = self._labels_by_trust(image, trusted=trusted)
        category_names = [
            item.category_name for item in image.level2_categories
        ] if not trusted and labels else []
        business_label_names = [
            self.semantic_profile.business_label_name(label)
            for label in labels
        ]
        normalized_category = _normalize(policy.primary_category)
        return any(
            _normalize(name) == normalized_category
            for name in [*category_names, *business_label_names]
        )

    def _matches_primary_label(
        self,
        image: Image,
        policy: StrictSearchPolicy,
        *,
        trusted: bool,
    ) -> bool:
        label_names = [link.tag.name for link in image.tag_links] if trusted else []
        business_label_names = [
            label.tag.name
            for label in self._labels_by_trust(image, trusted=trusted)
        ]
        normalized_label = _normalize(policy.primary_label)
        return any(
            _normalize(name) == normalized_label
            for name in [*label_names, *business_label_names]
        )

    def _labels_by_trust(self, image: Image, *, trusted: bool):
        labels = self.semantic_profile.searchable_business_labels(image)
        if trusted:
            return [
                label
                for label in labels
                if self.semantic_profile.label_policy.is_trusted(label)
            ]
        return [
            label
            for label in labels
            if self.semantic_profile.label_policy.is_pending_ai(label)
        ]

    def _pending_match_has_semantic_support(
        self,
        image: Image,
        policy: StrictSearchPolicy,
    ) -> bool:
        normalized_label = _normalize(policy.primary_label)
        normalized_category = _normalize(policy.primary_category)
        searchable_text = " ".join(
            [
                image.image_summary or "",
                " ".join(item.tag_name for item in image.content_tags),
                " ".join(item.category_name for item in image.level2_categories),
            ]
        )
        normalized_text = _normalize(searchable_text)
        if normalized_label and normalized_label in normalized_text:
            return True
        if normalized_category and normalized_category in normalized_text:
            return True
        return any(
            label.reason and label.evidence_level in {"A", "B"}
            for label in self._labels_by_trust(image, trusted=False)
        )


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


NEGATION_MARKERS = (
    "不是",
    "并非",
    "而不是",
    "而非",
    "没有",
    "未体现",
    "不属于",
    "不支持",
    "避免",
    "排除",
)


def _contains_unnegated_concept(text: str, concept: str) -> bool:
    normalized_text = _normalize(text)
    normalized_concept = _normalize(concept)
    if not normalized_text or not normalized_concept:
        return False

    start = 0
    while True:
        index = normalized_text.find(normalized_concept, start)
        if index < 0:
            return False
        if not _is_negated_context(normalized_text, index):
            return True
        start = index + len(normalized_concept)


def _is_negated_context(normalized_text: str, concept_index: int) -> bool:
    context_start = max(0, concept_index - 14)
    context = normalized_text[context_start:concept_index]
    return any(_normalize(marker) in context for marker in NEGATION_MARKERS)
