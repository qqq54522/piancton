from __future__ import annotations

from app.domain.runtime_intents import RuntimeIntent, RuntimeIntentCatalog
from app.services.viking_knowledge_service_client import (
    VikingKnowledgeServiceChatResult,
)
from app.services.viking_knowledge_service_router import VikingKnowledgeServiceRouter


class FakeKnowledgeClient:
    configured = True

    def __init__(self, result: VikingKnowledgeServiceChatResult):
        self.result = result

    def chat(self, query: str) -> VikingKnowledgeServiceChatResult:
        return self.result


def test_knowledge_service_router_turns_answer_into_single_selling_point():
    router = VikingKnowledgeServiceRouter(
        client=FakeKnowledgeClient(
            VikingKnowledgeServiceChatResult(
                query="动画讲明白抽象知识",
                response={},
                generated_answer=(
                    "判断结果：属于同步校内体系下的动画精讲。"
                    "原因是用户强调用动画把抽象知识讲明白。"
                ),
                reasoning_content="",
                result_list=[],
            )
        ),
        runtime_catalog=_catalog(),
        enabled=True,
    )

    result = router.route("动画讲明白抽象知识")

    assert result is not None
    assert result.query_type == "business_intent_search"
    assert [item.concept for item in result.matched_business_concepts] == [
        "同步校内体系 > 动画精讲"
    ]
    assert "知识库服务" in result.search_strategy


def test_knowledge_service_router_keeps_real_multi_selling_point_answers():
    router = VikingKnowledgeServiceRouter(
        client=FakeKnowledgeClient(
            VikingKnowledgeServiceChatResult(
                query="拍题以后还要学一题会一类",
                response={},
                generated_answer=(
                    "判断结果：同时涉及 AI拍题精学 和 举一反三。"
                    "前者对应拍题后的分步引导，后者对应一题带一类题。"
                ),
                reasoning_content="",
                result_list=[],
            )
        ),
        runtime_catalog=_catalog(),
        enabled=True,
    )

    result = router.route("拍题以后还要学一题会一类")

    assert result is not None
    assert result.query_type == "multi_business_intent_search"
    assert [item.concept for item in result.matched_business_concepts] == [
        "同步自学体系 > AI拍题精学",
        "同步考点体系 > 举一反三",
    ]


def test_knowledge_service_router_blocks_non_business_answers():
    router = VikingKnowledgeServiceRouter(
        client=FakeKnowledgeClient(
            VikingKnowledgeServiceChatResult(
                query="退款多少钱",
                response={},
                generated_answer="这不是业务卖点检索问题，当前知识库不适合返回卖点。",
                reasoning_content="",
                result_list=[],
            )
        ),
        runtime_catalog=_catalog(),
        enabled=True,
    )

    result = router.route("退款多少钱")

    assert result is not None
    assert result.query_type == "no_reliable_intent_search"
    assert result.matched_business_concepts == []


def test_knowledge_service_router_ignores_negated_selling_points():
    router = VikingKnowledgeServiceRouter(
        client=FakeKnowledgeClient(
            VikingKnowledgeServiceChatResult(
                query="拍题后讲步骤",
                response={},
                generated_answer="这不是动画精讲，而是 AI拍题精学。",
                reasoning_content="",
                result_list=[],
            )
        ),
        runtime_catalog=_catalog(),
        enabled=True,
    )

    result = router.route("拍题后讲步骤")

    assert result is not None
    assert [item.concept for item in result.matched_business_concepts] == [
        "同步自学体系 > AI拍题精学"
    ]


def test_knowledge_service_router_can_use_retrieved_chunks_when_answer_is_empty():
    router = VikingKnowledgeServiceRouter(
        client=FakeKnowledgeClient(
            VikingKnowledgeServiceChatResult(
                query="一题带一类题",
                response={},
                generated_answer="",
                reasoning_content="",
                result_list=[
                    {
                        "content": (
                            "体系：同步考点体系。\n"
                            "核心卖点：举一反三。\n"
                            "定义：理解原理，通过一道题理解一类题。"
                        )
                    }
                ],
            )
        ),
        runtime_catalog=_catalog(),
        enabled=True,
    )

    result = router.route("一题带一类题")

    assert result is not None
    assert result.normalized_query == "举一反三"


def _catalog() -> RuntimeIntentCatalog:
    return RuntimeIntentCatalog(
        version="test",
        intents=(
            RuntimeIntent(
                code="animation_explanation",
                name="动画精讲",
                display_name="同步校内体系 > 动画精讲",
                phrases=("动画讲透知识点",),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=("抽象知识听不懂",),
                must_have_concepts=("动画", "讲明白"),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="photo_guided_learning",
                name="AI拍题精学",
                display_name="同步自学体系 > AI拍题精学",
                phrases=("拍题精学",),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=("不会题",),
                must_have_concepts=("拍题", "分步引导"),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
            RuntimeIntent(
                code="transfer_practice",
                name="举一反三",
                display_name="同步考点体系 > 举一反三",
                phrases=("一题带一类题",),
                exact_only_phrases=(),
                interpretation_patterns=(),
                pain_points=("换题不会",),
                must_have_concepts=("举一反三", "同类题"),
                nice_to_have_concepts=(),
                exclude_concepts=(),
            ),
        ),
    )
