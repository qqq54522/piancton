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
from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.ai_service import AiService
from app.services.search_models import ConceptMatch


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
            return self._understanding_from_matches(query, matches)

        ai_understanding = self._understand_with_ai(query)
        if ai_understanding:
            return ai_understanding

        if matches:
            return self._understanding_from_matches(
                query,
                matches,
                confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
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
        if self._should_trust_local(query, matches):
            return self._understanding_from_matches(query, matches)
        return self._understanding_from_matches(
            query,
            matches,
            confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
            fallback_reason="本地意图仍需消歧，不进入高置信卖点主通道",
        )

    def should_use_model(
        self,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
    ) -> bool:
        if not self.ai_service or not self.ai_service.provider.configured:
            return False
        if local_understanding is None:
            return True
        matches = self._local_matches(keyword.strip())
        return not self._should_trust_local(keyword, matches)

    def understand_with_model(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.ai_service or not self.ai_service.provider.configured:
            return None
        return self.ai_service.understand_search(query)

    def weak_local_fallback(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query:
            return None
        matches = self._local_matches(query)
        if not matches:
            return None
        return self._understanding_from_matches(
            query,
            matches,
            confidence_cap=UNCERTAIN_FALLBACK_CONFIDENCE,
            fallback_reason="本地意图不确定，模型不可用，使用本地弱兜底",
        )

    def present_recognized_concepts(
        self,
        keyword: str,
        understanding: SearchUnderstanding | None,
        concept_matches: list[ConceptMatch],
    ) -> SearchUnderstanding | None:
        """Expose the validated concept candidates used by recall to the result UI."""
        if understanding is None and not concept_matches:
            return None
        existing = list(understanding.matched_business_concepts) if understanding else []
        existing_keys = {_concept_key(item.concept) for item in existing}
        additions = concept_matches
        if understanding is not None:
            additions = []
        elif len(concept_matches) > 1:
            # Multiple raw database matches are alternatives until query understanding
            # confirms that the sentence genuinely expresses several selling points.
            return None
        for match in additions:
            key = _concept_key(match.name)
            if key in existing_keys:
                continue
            existing.append(
                SearchConceptMatch(
                    concept=match.name,
                    relation="direct" if match.score >= 0.9 else "related",
                    reason="；".join(match.reasons) or "本地卖点识别",
                    weight=match.score,
                )
            )
            existing_keys.add(key)

        if not existing:
            return understanding
        existing.sort(key=lambda item: item.weight, reverse=True)
        concept_names = [_display_concept_name(item.concept) for item in existing]
        confirmed_multi = bool(
            understanding
            and understanding.query_type == "multi_business_intent_search"
        )
        if confirmed_multi:
            intent_summary = f"本次需求可能同时涉及：{'、'.join(concept_names[:4])}"
            query_type = "multi_business_intent_search"
            strategy = "按多个候选卖点并行召回，再由素材独有表达和画面语义区分"
        else:
            intent_summary = (
                understanding.search_intent
                if understanding and understanding.search_intent
                else f"本次需求主要涉及：{concept_names[0]}"
            )
            unresolved_multiple = len(concept_names) > 1
            query_type = (
                "ambiguous_business_intent_search"
                if unresolved_multiple
                else understanding.query_type
                if understanding
                else "business_intent_search"
            )
            strategy = (
                "多个候选尚未确认可以同时成立，不执行多卖点硬路由"
                if unresolved_multiple
                else understanding.search_strategy
                if understanding and understanding.search_strategy
                else "优先按已确认卖点关系召回"
            )
        return SearchUnderstanding(
            original_query=understanding.original_query if understanding else keyword,
            normalized_query=(
                understanding.normalized_query
                if understanding and understanding.normalized_query.strip()
                else concept_names[0]
            ),
            search_intent=intent_summary,
            query_type=query_type,
            expanded_terms=list(understanding.expanded_terms) if understanding else [],
            matched_business_concepts=existing,
            excluded_concepts=list(understanding.excluded_concepts) if understanding else [],
            search_strategy=strategy,
        )

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
        if top.confidence >= 0.9 and second.confidence >= 0.9:
            return True
        return confidence_gap > AMBIGUOUS_CONFIDENCE_GAP

    def _understand_with_ai(self, query: str) -> SearchUnderstanding | None:
        if not self.ai_service or not self.ai_service.provider.configured:
            return None
        try:
            return self.ai_service.understand_search(query)
        except AppError:
            return None

    def _understanding_from_matches(
        self,
        query: str,
        matches: list[IntentMatch],
        *,
        confidence_cap: float | None = None,
        fallback_reason: str | None = None,
    ) -> SearchUnderstanding:
        selected = _candidate_intent_matches(matches)
        primary = selected[0]
        label = target_label(primary.intent)
        concept_matches: list[SearchConceptMatch] = []
        excluded: list[str] = []
        for match in selected:
            weight = match.confidence
            if confidence_cap is not None:
                weight = min(weight, confidence_cap)
            reasons = list(match.reasons)
            if fallback_reason:
                reasons.append(fallback_reason)
            concept_matches.append(
                SearchConceptMatch(
                    concept=target_display_name(match.intent),
                    relation="direct" if weight >= LOCAL_TRUST_THRESHOLD else "related",
                    reason="；".join(reasons),
                    weight=weight,
                )
            )
            excluded.extend(match.intent.exclude_concepts)
        names = [target_label(match.intent).name for match in selected]
        confirmed_multi = len(names) > 1 and confidence_cap is None
        uncertain = confidence_cap is not None
        return SearchUnderstanding(
            original_query=query,
            normalized_query=label.name,
            search_intent=(
                f"用户可能同时在找“{'、'.join(names)}”相关素材"
                if confirmed_multi
                else f"当前只能判断可能涉及“{'、'.join(names)}”，仍需消歧"
                if uncertain
                else f"用户在找“{primary.intent.name}”相关素材"
            ),
            query_type=(
                "multi_business_intent_search"
                if confirmed_multi
                else "ambiguous_business_intent_search"
                if uncertain
                else "business_intent_search"
            ),
            expanded_terms=[],
            matched_business_concepts=concept_matches,
            excluded_concepts=list(dict.fromkeys(excluded)),
            search_strategy=(
                f"按{'、'.join(names)}多个候选卖点并行召回"
                if confirmed_multi
                else "不执行卖点硬路由，继续使用图片话术和画面语义兜底"
                if uncertain
                else f"优先按{primary.intent.name}对应业务概念召回"
            ),
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


def _candidate_intent_matches(matches: list[IntentMatch]) -> list[IntentMatch]:
    if not matches:
        return []
    top_confidence = matches[0].confidence
    return [
        match
        for index, match in enumerate(matches)
        if index == 0
        or (
            match.confidence >= 0.9
            and top_confidence - match.confidence <= 0.18
        )
    ][:4]


def _display_concept_name(value: str) -> str:
    return value.rsplit(">", 1)[-1].strip()


def _concept_key(value: str) -> str:
    return _normalize(_display_concept_name(value))


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)
