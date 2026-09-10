from __future__ import annotations

from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.search_knowledge_fallback_router import SearchKnowledgeFallbackRouter


class _FakeRouter:
    configured = True

    def __init__(self, result):
        self.result = result
        self.called = 0

    def route(self, keyword: str):
        self.called += 1
        return self.result


def test_fallback_router_keeps_primary_selling_point_result():
    primary = _FakeRouter(_understanding("AI拍题精学"))
    fallback = _FakeRouter(_understanding("举一反三"))
    router = SearchKnowledgeFallbackRouter(primary=primary, fallback=fallback)

    result = router.route("拍题精学")

    assert result is primary.result
    assert primary.called == 1
    assert fallback.called == 0


def test_fallback_router_keeps_primary_non_business_result():
    primary = _FakeRouter(
        SearchUnderstanding(
            original_query="退款多少钱",
            normalized_query="退款多少钱",
            search_intent="知识库判断：这不是当前卖点图库检索问题",
            query_type="no_reliable_intent_search",
            expanded_terms=[],
            matched_business_concepts=[],
            matched_proof_points=[],
            matched_evidence_points=[],
            excluded_concepts=[],
            search_strategy="知识库已判断无可靠卖点",
        )
    )
    fallback = _FakeRouter(_understanding("专项培优"))
    router = SearchKnowledgeFallbackRouter(primary=primary, fallback=fallback)

    result = router.route("退款多少钱")

    assert result is primary.result
    assert fallback.called == 0


def test_fallback_router_uses_vector_route_when_primary_has_no_match():
    primary = _FakeRouter(None)
    fallback = _FakeRouter(_understanding("专项培优"))
    router = SearchKnowledgeFallbackRouter(primary=primary, fallback=fallback)

    result = router.route("学有余力进一步提升")

    assert result is not None
    assert [item.concept for item in result.matched_business_concepts] == ["专项培优"]
    assert "知识库服务未产出可信卖点" in result.search_strategy


def _understanding(concept: str) -> SearchUnderstanding:
    return SearchUnderstanding(
        original_query=concept,
        normalized_query=concept,
        search_intent=f"命中：{concept}",
        query_type="business_intent_search",
        expanded_terms=[],
        matched_business_concepts=[
            SearchConceptMatch(
                concept=concept,
                relation="direct",
                reason="test",
                weight=0.94,
            )
        ],
        matched_proof_points=[],
        matched_evidence_points=[],
        excluded_concepts=[],
        search_strategy="VikingDB 先确定卖点，再回本地数据库取已审核素材",
    )
