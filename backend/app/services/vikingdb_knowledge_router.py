from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.runtime_intents import RuntimeIntentCatalog
from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.vikingdb_client import VikingDBClient

MULTI_INTENT_MARKERS = (
    "同时",
    "以及",
    "并且",
    "还有",
    "又",
    "也",
    "还能",
    "之后",
    "再",
    "和",
    "与",
    "、",
    "+",
    "/",
)

EXAM_REVIEW_MARKERS = (
    "考前",
    "口前",
    "临考",
    "考试前",
    "期中",
    "期末",
    "月考",
    "中考",
    "高考",
    "考前突击",
    "考前冲刺",
)

REVIEW_MARKERS = (
    "复习",
    "冲刺",
    "抓重点",
    "划重点",
    "考什么练什么",
    "突击",
)

SHORT_BUSINESS_ENTRY_OVERRIDES = {
    # Clean VikingDB knowledge search returns AI拍题精学 for this one-character
    # business entry, but with a low absolute score. Keep this exact and narrow
    # so generic UI words such as “图”“素材”“标题” do not route to random concepts.
    "拍": "photo_guided_learning",
}

DIRECT_EXPERT_ENTRY_MARKERS = (
    "专家",
    "专家老师",
    "专家团队",
    "专家背书",
    "教研专家",
)

DIRECT_EXPERT_ENTRY_CONTEXT = (
    "洋葱",
    "实力",
    "靠谱",
    "权威",
    "背书",
    "团队",
    "规划",
)

NEGATION_MARKERS = (
    "不要",
    "不需要",
    "不是",
    "不靠",
    "别",
    "排除",
)


@dataclass(frozen=True)
class VikingDBKnowledgeMatch:
    code: str
    display_name: str
    score: float
    raw_id: str


class VikingDBKnowledgeRouter:
    """Fast first-pass router for system/selling-point knowledge in VikingDB.

    VikingDB only decides which reviewed business concept codes are worth
    recalling. The local database remains authoritative for images, status,
    permissions, and accepted concept relations.
    """

    def __init__(
        self,
        *,
        client: VikingDBClient,
        index_name: str,
        runtime_catalog: RuntimeIntentCatalog,
        enabled: bool,
        limit: int = 8,
        min_score: float = 0.34,
        multi_score_ratio: float = 0.9,
        multi_score_gap: float = 0.08,
        max_matches: int = 3,
    ):
        self.client = client
        self.index_name = index_name.strip()
        self.enabled = enabled
        self.limit = max(1, min(limit, 20))
        self.min_score = max(0.0, min(min_score, 1.0))
        self.multi_score_ratio = max(0.0, min(multi_score_ratio, 1.0))
        self.multi_score_gap = max(0.0, multi_score_gap)
        self.max_matches = max(1, min(max_matches, 6))
        self.intent_by_code = {
            intent.code: intent
            for intent in runtime_catalog.intents
            if intent.code and intent.display_name
        }

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.client.configured and self.index_name)

    def route(self, keyword: str) -> SearchUnderstanding | None:
        query = keyword.strip()
        if not query or not self.configured:
            return None
        result = self.client.search_text(
            query,
            index_name=self.index_name,
            limit=self.limit,
            filter_expression={
                "op": "must",
                "field": "doc_type",
                "conds": ["selling_point"],
            },
        )
        matches = self._business_override_matches(query) or self._select_matches(
            query,
            result.matches,
        )
        if not matches:
            return None
        concepts = [
            SearchConceptMatch(
                concept=match.display_name,
                relation="direct",
                reason=(
                    "VikingDB 知识路由命中："
                    f"{match.raw_id}，向量分数 {match.score:.3f}"
                ),
                weight=0.94 if index == 0 else 0.88,
            )
            for index, match in enumerate(matches)
        ]
        if len(concepts) > 1:
            names = "、".join(_short_name(item.concept) for item in concepts)
            query_type = "multi_business_intent_search"
            intent = f"本次需求可能同时涉及：{names}"
            strategy = "VikingDB 先召回多个接近卖点，再回本地数据库取已审核素材"
        else:
            query_type = "business_intent_search"
            intent = f"本次需求主要涉及：{_short_name(concepts[0].concept)}"
            strategy = "VikingDB 先确定卖点，再回本地数据库取已审核素材"
        return SearchUnderstanding(
            original_query=query,
            normalized_query="、".join(_short_name(item.concept) for item in concepts),
            search_intent=intent,
            query_type=query_type,
            expanded_terms=[],
            matched_business_concepts=concepts,
            matched_proof_points=[],
            matched_evidence_points=[],
            excluded_concepts=[],
            search_strategy=strategy,
        )

    def _select_matches(
        self,
        query: str,
        raw_matches: list[dict[str, Any]],
    ) -> list[VikingDBKnowledgeMatch]:
        selling_points = [
            match
            for match in (self._parse_match(item) for item in raw_matches)
            if match is not None
        ]
        if not selling_points:
            return []
        top = selling_points[0]
        if top.score < self.min_score:
            return []
        selected = [top]
        if not _looks_like_multi_intent(query) and len(selling_points) > 1:
            runner_up = selling_points[1]
            if runner_up.score < top.score * 0.94:
                return selected
        for match in selling_points[1:]:
            if len(selected) >= self.max_matches:
                break
            if match.score < top.score * self.multi_score_ratio:
                continue
            if top.score - match.score > self.multi_score_gap:
                continue
            selected.append(match)
        return selected

    def _parse_match(self, item: dict[str, Any]) -> VikingDBKnowledgeMatch | None:
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
        doc_type = str(fields.get("doc_type") or item.get("doc_type") or "")
        if doc_type != "selling_point":
            return None
        code = str(fields.get("concept_code") or item.get("concept_code") or "")
        intent = self.intent_by_code.get(code)
        if intent is None:
            return None
        raw_score = item.get("score", item.get("ann_score", 0.0))
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        return VikingDBKnowledgeMatch(
            code=code,
            display_name=intent.display_name,
            score=score,
            raw_id=str(item.get("id") or fields.get("doc_id") or code),
        )

    def _business_override_matches(
        self,
        query: str,
    ) -> list[VikingDBKnowledgeMatch]:
        short_code = SHORT_BUSINESS_ENTRY_OVERRIDES.get(query.strip())
        if short_code:
            intent = self.intent_by_code.get(short_code)
            if intent is not None:
                return [
                    VikingDBKnowledgeMatch(
                        code=short_code,
                        display_name=intent.display_name,
                        score=0.99,
                        raw_id=f"business_override:short_entry:{query.strip()}",
                    )
                ]
        if _looks_like_direct_expert_entry(query):
            intent = self.intent_by_code.get("expert_planning")
            if intent is not None:
                return [
                    VikingDBKnowledgeMatch(
                        code="expert_planning",
                        display_name=intent.display_name,
                        score=0.99,
                        raw_id="business_override:direct_expert_entry",
                    )
                ]
        if not _looks_like_exam_review(query):
            return []
        intent = self.intent_by_code.get("focused_excellence")
        if intent is None:
            return []
        return [
            VikingDBKnowledgeMatch(
                code="focused_excellence",
                display_name=intent.display_name,
                score=0.99,
                raw_id="business_override:exam_review_to_focused_excellence",
            )
        ]


def _looks_like_multi_intent(query: str) -> bool:
    return any(marker in query for marker in MULTI_INTENT_MARKERS)


def _looks_like_exam_review(query: str) -> bool:
    return any(marker in query for marker in EXAM_REVIEW_MARKERS) and any(
        marker in query for marker in REVIEW_MARKERS
    )


def _looks_like_direct_expert_entry(query: str) -> bool:
    compact = _compact_query(query)
    if len(compact) > 14 or any(marker in compact for marker in NEGATION_MARKERS):
        return False
    if not any(marker in compact for marker in DIRECT_EXPERT_ENTRY_MARKERS):
        return False
    has_business_context = any(
        marker in compact for marker in DIRECT_EXPERT_ENTRY_CONTEXT
    )
    return compact == "专家" or has_business_context


def _compact_query(query: str) -> str:
    ignored = set(" \t\r\n，。！？、,.!?")
    return "".join(char for char in query.strip() if char not in ignored)


def _short_name(value: str) -> str:
    return value.rsplit(">", 1)[-1].strip()
