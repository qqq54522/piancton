from app.domain.business_intents import (
    BusinessIntent,
    BusinessIntentCatalog,
    load_business_intents,
    render_business_intents_for_prompt,
    target_display_name,
)
from app.domain.search_policy import SearchPolicyCatalog
from app.schemas.ai import SearchConceptMatch, SearchUnderstanding
from app.services.query_understanding_service import QueryUnderstandingService


def test_business_intents_catalog_covers_all_systems():
    catalog = load_business_intents()

    assert len(catalog.intents) == 16
    assert {intent.target_system_code for intent in catalog.intents} == {
        "sync_school",
        "sync_exam",
        "sync_cultivation",
        "sync_planning",
        "sync_self_study",
        "sync_companion",
    }
    assert {
        "同步自学体系 > AI错题本",
        "同步自学体系 > AI拍题精学",
        "同步培养体系 > 专家规划",
    }.issubset({target_display_name(intent) for intent in catalog.intents})


def test_business_intents_render_prompt_material():
    rendered = render_business_intents_for_prompt()

    assert "业务意图目录" in rendered
    assert "ai_error_book_intent / AI错题本" in rendered
    assert "photo_guided_learning_intent / AI拍题精学" in rendered
    assert "expert_planning_intent / 专家规划" in rendered
    assert "learning_report_intent / 学情报告反馈" in rendered
    assert "目标标签：同步培养体系 > 专家规划" in rendered


def test_query_understanding_maps_core_intent_queries_locally():
    service = QueryUnderstandingService()
    cases = [
        ("错题本", "AI错题本", "同步自学体系 > AI错题本"),
        ("上传错题", "AI错题本", "同步自学体系 > AI错题本"),
        ("整理错题费功夫又容易忘", "AI错题本", "同步自学体系 > AI错题本"),
        ("体现拍题精学", "AI拍题精学", "同步自学体系 > AI拍题精学"),
        ("孩子拍题只抄答案考试不会", "AI拍题精学", "同步自学体系 > AI拍题精学"),
        ("专家规划", "专家规划", "同步培养体系 > 专家规划"),
        ("体现专家规划", "专家规划", "同步培养体系 > 专家规划"),
        ("出卷人编教材的人设计课程", "专家规划", "同步培养体系 > 专家规划"),
        ("孩子听不懂老师讲课", "动画精讲", "同步校内体系 > 动画精讲"),
        ("和学校课程一致", "同步校内", "同步校内体系 > 同步校内"),
        ("离中考还有一个月怎么规划", "AI定制学习方案", "同步规划体系 > AI定制学习方案"),
        ("孩子叫不动管不住一管就吵架", "真人老师督学", "同步伴学体系 > 真人老师督学"),
        ("家长想知道孩子每天学了什么", "学情报告反馈", "同步伴学体系 > 学情报告反馈"),
    ]

    for query, normalized_query, category in cases:
        understanding = service.understand(query)
        assert understanding is not None
        assert understanding.normalized_query == normalized_query
        assert understanding.matched_business_concepts[0].concept == category
        assert understanding.matched_business_concepts[0].relation == "direct"


def test_embedded_variant_training_prefers_transfer_practice_over_quiz():
    service = QueryUnderstandingService()
    queries = (
        "孩子会听懂但不会做，想找讲完还有例题和变式训练的",
        "孩子说听懂了但不知道真会不会，想找讲完例题后的变式训练",
        "讲完一道例题，再做同类题训练，直到换个条件也会做",
    )

    for query in queries:
        understanding = service.understand_locally(query)

        assert understanding is not None
        assert understanding.query_type == "business_intent_search"
        assert [
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        ] == ["举一反三"]
        assert understanding.matched_business_concepts[0].relation == "direct"


def test_embedded_variant_training_keeps_error_book_when_error_context_is_explicit():
    understanding = QueryUnderstandingService().understand_locally(
        "把孩子不会做的个人错题整理起来，再推荐同类题训练"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI错题本"]


def test_quiz_pain_without_variant_training_still_maps_to_instant_quiz():
    understanding = QueryUnderstandingService().understand_locally(
        "孩子说听懂了但不知道真会不会"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.matched_business_concepts[0].concept.endswith("> 课后小测")


def test_context_specific_photo_query_does_not_expand_shared_entry_candidates():
    understanding = QueryUnderstandingService().understand_locally(
        "AI拍照后即可为你点拨思路，不会立即出答案"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert all(
        item.relation == "direct"
        for item in understanding.matched_business_concepts
    )


def test_exact_shared_photo_entry_stays_exploratory():
    understanding = QueryUnderstandingService().understand_locally("AI拍照")

    assert understanding is not None
    assert understanding.query_type == "exploratory_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"AI错题本", "AI拍题精学", "极速预习复习", "AI私教答疑"}


def test_query_understanding_falls_back_to_ai_when_local_intent_does_not_match():
    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str):
            assert keyword == "听课费劲"
            return "ai-result"

    service = QueryUnderstandingService(ai_service=FakeAiService())

    assert service.understand("听课费劲") == "ai-result"


def test_query_understanding_keeps_decisive_local_match_without_ai():
    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str):
            raise AssertionError(f"不应该调用 AI：{keyword}")

    service = QueryUnderstandingService(ai_service=FakeAiService())

    understanding = service.understand("错题本")

    assert understanding is not None
    assert understanding.normalized_query == "AI错题本"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_query_understanding_uses_ai_for_weak_local_match():
    ai_result = _ai_understanding("AI判断结果")

    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str):
            assert keyword == "只说一个模糊词"
            return ai_result

    service = QueryUnderstandingService(
        ai_service=FakeAiService(),
        catalog=_test_catalog(
            BusinessIntent(
                code="weak_intent",
                name="弱命中",
                target_system_code="sync_self_study",
                target_label_code="ai_error_book",
                phrases=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=("模糊词",),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            )
        ),
    )

    assert service.understand("只说一个模糊词") == ai_result


def test_query_understanding_uses_ai_for_configured_ambiguous_terms():
    ai_result = _ai_understanding("AI消歧后的规划")

    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str):
            assert keyword == "需要规划"
            return ai_result

    service = QueryUnderstandingService(
        ai_service=FakeAiService(),
        catalog=_test_catalog(
            BusinessIntent(
                code="planning_intent",
                name="学习规划",
                target_system_code="sync_planning",
                target_label_code="ai_learning_plan",
                phrases=(),
                pain_points=("需要规划",),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            )
        ),
        search_policy=SearchPolicyCatalog(
            version="test",
            ambiguous_terms=("规划",),
        ),
    )

    assert service.understand("需要规划") == ai_result


def test_query_understanding_uses_ai_for_ambiguous_local_matches():
    ai_result = _ai_understanding("AI消歧结果")

    class FakeProvider:
        configured = True

    class FakeAiService:
        provider = FakeProvider()

        def understand_search(self, keyword: str):
            assert keyword == "体现规划"
            return ai_result

    service = QueryUnderstandingService(
        ai_service=FakeAiService(),
        catalog=_test_catalog(
            BusinessIntent(
                code="plan_intent",
                name="学习规划",
                target_system_code="sync_planning",
                target_label_code="ai_learning_plan",
                phrases=("规划",),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            ),
            BusinessIntent(
                code="expert_intent",
                name="专家规划",
                target_system_code="sync_cultivation",
                target_label_code="expert_planning",
                phrases=("规划",),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            ),
        ),
    )

    assert service.understand("体现规划") == ai_result


def test_local_ambiguous_matches_are_not_presented_as_confirmed_multi_intent():
    service = QueryUnderstandingService(
        catalog=_test_catalog(
            BusinessIntent(
                code="plan_intent",
                name="学习规划",
                target_system_code="sync_planning",
                target_label_code="ai_learning_plan",
                phrases=("规划",),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            ),
            BusinessIntent(
                code="expert_intent",
                name="专家规划",
                target_system_code="sync_cultivation",
                target_label_code="expert_planning",
                phrases=("规划",),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=(),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            ),
        ),
        search_policy=SearchPolicyCatalog(
            version="test",
            ambiguous_terms=("规划",),
        ),
    )

    understanding = service.understand_locally("体现规划")

    assert understanding is not None
    assert understanding.query_type == "ambiguous_business_intent_search"
    assert all(
        item.relation == "related" and item.weight < 0.85
        for item in understanding.matched_business_concepts
    )


def test_model_alternatives_require_explicit_multi_intent_before_hard_routing():
    understanding = SearchUnderstanding(
        original_query="需要规划",
        normalized_query="学习规划",
        search_intent="模型返回两个备选",
        query_type="business_intent_search",
        matched_business_concepts=[
            SearchConceptMatch(
                concept="同步规划体系 > 学习规划",
                relation="direct",
                reason="候选一",
                weight=0.92,
            ),
            SearchConceptMatch(
                concept="同步培养体系 > 专家规划",
                relation="direct",
                reason="候选二",
                weight=0.91,
            ),
        ],
    )

    presented = QueryUnderstandingService().present_recognized_concepts(
        "需要规划",
        understanding,
        [],
    )

    assert presented is not None
    assert presented.query_type == "ambiguous_business_intent_search"
    assert "不执行多卖点硬路由" in presented.search_strategy


def test_query_understanding_uses_weak_local_fallback_when_ai_unavailable():
    service = QueryUnderstandingService(
        catalog=_test_catalog(
            BusinessIntent(
                code="weak_intent",
                name="弱命中",
                target_system_code="sync_self_study",
                target_label_code="ai_error_book",
                phrases=(),
                pain_points=(),
                must_have_concepts=(),
                nice_to_have_concepts=("模糊词",),
                exclude_concepts=(),
                result_policy="strict_allow_few_results",
            )
        ),
    )

    understanding = service.understand("只说一个模糊词")

    assert understanding is not None
    match = understanding.matched_business_concepts[0]
    assert understanding.normalized_query == "AI错题本"
    assert match.weight < 0.85
    assert "本地弱兜底" in match.reason


def _test_catalog(*intents: BusinessIntent) -> BusinessIntentCatalog:
    return BusinessIntentCatalog(version="test", intents=tuple(intents))


def _ai_understanding(normalized_query: str) -> SearchUnderstanding:
    return SearchUnderstanding(
        original_query="",
        normalized_query=normalized_query,
        search_intent="AI 搜索理解",
        query_type="business_intent_search",
        expanded_terms=[],
        matched_business_concepts=[
            SearchConceptMatch(
                concept="同步自学体系 > AI错题本",
                relation="direct",
                reason="AI 判断",
                weight=0.91,
            )
        ],
        excluded_concepts=[],
        search_strategy="AI 消歧",
    )
