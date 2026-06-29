from __future__ import annotations

from dataclasses import dataclass

from app.core.errors import AppError
from app.domain.business_intents import (
    BusinessIntent,
    BusinessIntentCatalog,
    load_business_intents,
    target_display_name,
    target_label,
)
from app.domain.search_policy import SearchPolicyCatalog, load_search_policy
from app.schemas.ai import SearchCategoryMatch, SearchUnderstanding
from app.services.ai_service import AiService


@dataclass(frozen=True)
class IntentMatch:
    intent: BusinessIntent
    confidence: float
    reasons: tuple[str, ...]


LOCAL_TRUST_THRESHOLD = 0.85
AMBIGUOUS_CONFIDENCE_GAP = 0.05
UNCERTAIN_FALLBACK_CONFIDENCE = 0.74


class QueryUnderstandingService:
    def __init__(
        self,
        ai_service: AiService | None = None,
        catalog: BusinessIntentCatalog | None = None,
        search_policy: SearchPolicyCatalog | None = None,
    ):
        self.ai_service = ai_service
        self.catalog = catalog or load_business_intents()
        self.search_policy = search_policy or load_search_policy()

    def understand(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        matches = self._local_matches(query)
        if matches and self._should_trust_local(query, matches):
            return self._understanding_from_match(query, matches[0])

        ai_understanding = self._understand_with_ai(query)
        if ai_understanding:
            return ai_understanding

        if matches:
            return self._understanding_from_match(
                query,
                matches[0],
                confidence=min(matches[0].confidence, UNCERTAIN_FALLBACK_CONFIDENCE),
                fallback_reason="本地意图不确定，AI 不可用，使用本地弱兜底",
            )
        return None

    def understand_locally(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        matches = self._local_matches(query)
        if not matches:
            return None
        return self._understanding_from_match(query, matches[0])

    def _local_matches(self, query: str) -> list[IntentMatch]:
        return sorted(
            (
                match
                for intent in self.catalog.intents
                if (match := self._match_intent(query, intent)) is not None
            ),
            key=lambda item: item.confidence,
            reverse=True,
        )

    def _should_trust_local(self, query: str, matches: list[IntentMatch]) -> bool:
        if not matches:
            return False
        top = matches[0]
        if top.confidence < LOCAL_TRUST_THRESHOLD:
            return False
        if len(matches) == 1:
            return not (
                self._is_ambiguous_query(query)
                and top.confidence < 0.95
            )
        second = matches[1]
        confidence_gap = top.confidence - second.confidence
        if self._is_ambiguous_query(query) and confidence_gap <= 0.15:
            return False
        return confidence_gap > AMBIGUOUS_CONFIDENCE_GAP

    def _understand_with_ai(self, query: str) -> SearchUnderstanding | None:
        if not self.ai_service or not self.ai_service.provider.configured:
            return None
        try:
            return self.ai_service.understand_search(query)
        except AppError:
            return None

    def _understanding_from_match(
        self,
        query: str,
        match: IntentMatch,
        *,
        confidence: float | None = None,
        fallback_reason: str | None = None,
    ) -> SearchUnderstanding:
        weight = match.confidence if confidence is None else confidence
        reasons = list(match.reasons)
        if fallback_reason:
            reasons.append(fallback_reason)
        label = target_label(match.intent)
        return SearchUnderstanding(
            original_query=query,
            normalized_query=label.name,
            search_intent=f"用户在找“{match.intent.name}”相关素材",
            query_type="business_intent_search",
            expanded_level1_tags=[],
            matched_level2_categories=[
                SearchCategoryMatch(
                    category=target_display_name(match.intent),
                    relation="direct",
                    reason="；".join(reasons),
                    weight=weight,
                )
            ],
            exclude_tags=list(match.intent.exclude_concepts),
            search_strategy=f"优先按{match.intent.name}对应业务标签召回",
        )

    def _match_intent(
        self,
        keyword: str,
        intent: BusinessIntent,
    ) -> IntentMatch | None:
        needle = _normalize(keyword)
        if not needle:
            return None
        weighted_groups = [
            (intent.phrases, 0.95, "功能表达命中"),
            (intent.pain_points, 0.9, "家长痛点命中"),
            (intent.must_have_concepts, 0.82, "必须概念命中"),
            (intent.nice_to_have_concepts, 0.72, "辅助概念命中"),
        ]
        scores: list[float] = []
        reasons: list[str] = []
        for terms, score, reason_prefix in weighted_groups:
            matched = _matched_terms(needle, terms)
            if not matched:
                continue
            scores.append(score)
            reasons.append(f"{reason_prefix}：{'、'.join(matched[:3])}")
        if not scores:
            return None
        if _matched_terms(needle, intent.exclude_concepts):
            scores = [min(score, 0.62) for score in scores]
            reasons.append("命中排除概念，降低置信度")
        return IntentMatch(
            intent=intent,
            confidence=max(scores),
            reasons=tuple(reasons),
        )

    def _is_ambiguous_query(self, query: str) -> bool:
        needle = _normalize(query)
        return any(
            _normalize(term) in needle
            for term in self.search_policy.ambiguous_terms
            if _normalize(term)
        )


def _matched_terms(needle: str, terms: tuple[str, ...]) -> list[str]:
    matched: list[str] = []
    for term in terms:
        normalized = _normalize(term)
        if len(normalized) < 2:
            continue
        if normalized in needle or (len(needle) >= 4 and needle in normalized):
            matched.append(term)
    return matched


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)
