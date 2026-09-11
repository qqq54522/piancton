from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.domain.runtime_intents import RuntimeIntent, RuntimeIntentCatalog
from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.query_expansion_service import unique
from app.services.viking_knowledge_service_client import VikingKnowledgeServiceClient

NON_BUSINESS_ANSWER_MARKERS = (
    "不是业务卖点",
    "不属于业务卖点",
    "不属于我们的卖点",
    "不属于卖点",
    "不是卖点检索",
    "不是业务卖点检索问题",
    "当前知识库不适合返回卖点",
    "当前资料无法可靠判断",
    "无法可靠判断",
    "无法判断为",
    "不适合返回卖点",
)

MULTI_ANSWER_MARKERS = (
    "多个卖点",
    "多个核心卖点",
    "同时涉及",
    "同时命中",
    "分别属于",
    "还涉及",
    "也涉及",
    "以及",
    "并且",
    "和",
    "与",
)


@dataclass(frozen=True)
class VikingKnowledgeServiceMatch:
    code: str
    display_name: str
    score: float
    reason: str


class VikingKnowledgeServiceRouter:
    """Routes natural-language search through the published Knowledge Base service."""

    def __init__(
        self,
        *,
        client: VikingKnowledgeServiceClient,
        runtime_catalog: RuntimeIntentCatalog,
        enabled: bool,
        max_matches: int = 4,
    ):
        self.client = client
        self.enabled = enabled
        self.max_matches = max(1, min(max_matches, 6))
        self.intents = tuple(
            intent
            for intent in runtime_catalog.intents
            if intent.code and intent.name and intent.display_name
        )
        self.intent_by_code = {intent.code: intent for intent in self.intents}

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.client.configured and self.intents)

    def route(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.configured:
            return None
        result = self.client.chat(query)
        answer_text = _primary_answer_text(
            result.generated_answer,
            result.reasoning_content,
        )
        if _looks_non_business(answer_text):
            return SearchUnderstanding(
                original_query=query,
                normalized_query=query,
                search_intent="知识库判断：这不是当前卖点图库检索问题",
                query_type="no_reliable_intent_search",
                expanded_terms=[],
                matched_business_concepts=[],
                matched_proof_points=[],
                matched_evidence_points=[],
                excluded_concepts=[],
                search_strategy="VikingDB 知识库服务已判断无可靠卖点，不返回卖点图库",
            )
        matches = self._select_matches(
            query,
            answer_text,
            result.result_list if not result.generated_answer.strip() else [],
        )
        if not matches:
            return None
        concepts = [
            SearchConceptMatch(
                concept=match.display_name,
                relation="direct",
                reason=match.reason,
                weight=0.96 if index == 0 else max(0.86, match.score),
            )
            for index, match in enumerate(matches)
        ]
        names = "、".join(_short_name(match.display_name) for match in matches)
        is_multi = len(concepts) > 1
        return SearchUnderstanding(
            original_query=query,
            normalized_query=names,
            search_intent=(
                f"知识库判断本次需求同时涉及：{names}"
                if is_multi
                else f"知识库判断本次需求主要涉及：{names}"
            ),
            query_type=(
                "multi_business_intent_search"
                if is_multi
                else "business_intent_search"
            ),
            expanded_terms=[],
            matched_business_concepts=concepts,
            matched_proof_points=[],
            matched_evidence_points=[],
            excluded_concepts=[],
            search_strategy=(
                "VikingDB 知识库服务先判断卖点并给出依据，"
                "再回本地数据库按已审核素材关系返回图库"
            ),
        )

    def _select_matches(
        self,
        query: str,
        answer_text: str,
        result_list: list[dict[str, Any]],
    ) -> list[VikingKnowledgeServiceMatch]:
        explicit_matches = self._select_explicit_answer_matches(answer_text)
        if explicit_matches:
            return explicit_matches[: self.max_matches]
        scored: list[tuple[float, RuntimeIntent, str]] = []
        for intent in self.intents:
            score, reason = self._score_intent(intent, answer_text, result_list)
            if score > 0:
                scored.append((score, intent, reason))
        if not scored:
            return []
        scored.sort(key=lambda item: item[0], reverse=True)
        top_score = scored[0][0]
        if top_score < 2.0:
            return []
        allow_multi = _looks_multi(query) or _looks_multi(answer_text)
        selected = []
        for score, intent, reason in scored:
            if len(selected) >= self.max_matches:
                break
            if selected and not allow_multi:
                break
            if selected and score < max(2.0, top_score * 0.64):
                continue
            selected.append(
                VikingKnowledgeServiceMatch(
                    code=intent.code,
                    display_name=intent.display_name,
                    score=min(1.0, 0.72 + score / 20),
                    reason=reason,
                )
            )
        return selected

    def _score_intent(
        self,
        intent: RuntimeIntent,
        answer_text: str,
        result_list: list[dict[str, Any]],
    ) -> tuple[float, str]:
        if _answer_negates_intent(answer_text, intent):
            return 0.0, ""
        answer = _normalize(answer_text)
        answer_hits = [
            term
            for term in _explicit_intent_terms(intent)
            if _is_strong_explicit_term(term, intent) and _normalize(term) in answer
        ]
        score = 0.0
        if answer_hits:
            score += 3.0 + min(2.0, len(answer_hits) * 0.4)
        top_result_hit = ""
        for index, item in enumerate(result_list[:4]):
            content = _normalize(_result_text(item))
            if not content:
                continue
            result_hits = [
                term
                for term in _intent_terms(intent)
                if len(_normalize(term)) >= 2 and _normalize(term) in content
            ]
            if not result_hits:
                continue
            score += max(0.5, 2.2 - index * 0.45)
            if not top_result_hit:
                top_result_hit = result_hits[0]
        reasons = []
        if answer_hits:
            reasons.append(f"知识库回答提到“{answer_hits[0]}”")
        if top_result_hit:
            reasons.append(f"参考片段命中“{top_result_hit}”")
        return score, "；".join(unique(reasons)) or "知识库服务命中卖点资料"

    def _select_explicit_answer_matches(
        self,
        answer_text: str,
    ) -> list[VikingKnowledgeServiceMatch]:
        segment = _explicit_selling_point_segment(answer_text)
        if not segment:
            return []
        normalized_segment = _normalize(segment)
        scored: list[tuple[int, RuntimeIntent, str]] = []
        for intent in self.intents:
            if _answer_negates_intent(segment, intent):
                continue
            hits = [
                term
                for term in _explicit_intent_terms(intent)
                if _is_strong_explicit_term(term, intent)
                and _normalize(term) in normalized_segment
            ]
            if not hits:
                continue
            first_position = min(normalized_segment.find(_normalize(term)) for term in hits)
            scored.append((first_position, intent, hits[0]))
        scored.sort(key=lambda item: item[0])
        return [
            VikingKnowledgeServiceMatch(
                code=intent.code,
                display_name=intent.display_name,
                score=0.98 if index == 0 else 0.92,
                reason=f"知识库最终答案明确列出“{hit}”",
            )
            for index, (_position, intent, hit) in enumerate(scored)
        ]


def _intent_terms(intent: RuntimeIntent) -> tuple[str, ...]:
    return tuple(
        unique(
            [
                intent.code,
                intent.name,
                intent.display_name,
                *intent.phrases,
                *intent.pain_points,
                *intent.must_have_concepts,
            ]
        )
    )


def _explicit_intent_terms(intent: RuntimeIntent) -> tuple[str, ...]:
    return tuple(
        unique(
            [
                intent.code,
                intent.name,
                intent.display_name,
                *intent.phrases,
                *intent.exact_only_phrases,
                *intent.interpretation_patterns,
            ]
        )
    )


def _is_strong_explicit_term(term: str, intent: RuntimeIntent) -> bool:
    normalized = _normalize(term)
    if not normalized:
        return False
    if normalized in {
        _normalize(intent.code),
        _normalize(intent.name),
        _normalize(intent.display_name),
    }:
        return True
    return len(normalized) >= 4


def _looks_non_business(text: str) -> bool:
    normalized = _normalize(text)
    return any(_normalize(marker) in normalized for marker in NON_BUSINESS_ANSWER_MARKERS)


def _looks_multi(text: str) -> bool:
    return any(marker in text for marker in MULTI_ANSWER_MARKERS)


def _answer_negates_intent(text: str, intent: RuntimeIntent) -> bool:
    normalized = _normalize(text)
    for term in (intent.name, intent.display_name, intent.code):
        key = _normalize(term)
        if not key:
            continue
        if any(marker in normalized for marker in (f"不是{key}", f"不属于{key}", f"并非{key}")):
            return True
    return False


def _primary_answer_text(generated_answer: str, reasoning_content: str) -> str:
    if generated_answer.strip():
        return generated_answer
    return reasoning_content


def _explicit_selling_point_segment(text: str) -> str:
    normalized_text = text.strip()
    if not normalized_text:
        return ""
    match = re.search(
        r"核心卖点\s*[:：]\s*(.+?)(?=\n\s*-?\s*(?:判断置信度|为什么这样判断|卖点定义|相关证明点)\s*[:：]|$)",
        normalized_text,
        flags=re.DOTALL,
    )
    if not match:
        return ""
    segment = match.group(1)
    stop_match = re.search(r"(?:判断置信度|为什么这样判断|卖点定义|相关证明点)\s*[:：]", segment)
    if stop_match:
        segment = segment[: stop_match.start()]
    return segment.strip(" -—：:\n\t")


def _result_text(item: dict[str, Any]) -> str:
    fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
    candidates = [
        item.get("content"),
        item.get("text"),
        item.get("chunk_content"),
        item.get("document_content"),
        fields.get("content"),
        fields.get("text"),
        fields.get("chunk_content"),
        fields.get("document_content"),
    ]
    return "\n".join(str(value) for value in candidates if isinstance(value, str))


def _normalize(value: str) -> str:
    ignored = set(" \t\r\n，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


def _short_name(value: str) -> str:
    return value.rsplit(">", 1)[-1].strip()
