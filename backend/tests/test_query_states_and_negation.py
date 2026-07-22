from app.domain.query_negation import is_term_negated
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import (
    BusinessConcept,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import Image
from app.models.tag import Tag
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.services.intent_catalog_service import IntentCatalogService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_routing_service import SearchConceptRoutingService
from app.services.search_models import SearchHit
from app.services.search_service import SearchService


def test_query_negation_only_flips_explicitly_rejected_terms():
    assert is_term_negated("不需要真人老师督学", "真人老师督学")
    assert is_term_negated("不需要真人老师督学", "真人老师")
    assert is_term_negated("无需整理错题", "整理错题")
    assert not is_term_negated("拍题后不要直接给答案", "拍题")
    assert not is_term_negated("AI拍照后即可为你点拨思路，不会立即出答案", "不会立即出答案")
    assert not is_term_negated("不需要错题本，要拍题讲解", "拍题讲解")
    assert not is_term_negated("不需要家长的真人老师督学", "真人老师督学")
    assert not is_term_negated("需要真人老师帮忙监督", "真人老师")


def test_shared_entry_word_is_exploratory_not_confirmed_multi():
    understanding = QueryUnderstandingService().understand_locally("AI拍照")

    assert understanding is not None
    assert understanding.query_type == "exploratory_business_intent_search"
    assert "你可能在找" in understanding.search_intent
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"AI错题本", "AI拍题精学", "极速预习复习", "AI私教答疑"}
    assert all(
        item.relation == "direct"
        for item in understanding.matched_business_concepts
    )


def test_shared_photo_entry_is_narrowed_by_context_specific_evidence():
    understanding = QueryUnderstandingService().understand_locally(
        "AI拍照后即可为你点拨思路，不会立即出答案"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]


def test_objectless_photo_explain_combination_stays_exploratory():
    # D079：拍照入口没有拍摄对象、只有讲解目的时，保持拍题精学/极速预习复习
    # 探索型组合，不硬选唯一卖点，也不落入全库兜底。
    for query in (
        "拍一下，AI马上给你讲解",
        "一键拍照，AI 即刻为你提供思路点拨与详细解析，拒绝直接给答案",
    ):
        understanding = QueryUnderstandingService().understand_locally(query)

        assert understanding is not None, query
        assert understanding.query_type == "exploratory_business_intent_search"
        assert "你可能在找" in understanding.search_intent
        assert {
            item.concept.rsplit(">", 1)[-1].strip()
            for item in understanding.matched_business_concepts
        } == {"AI拍题精学", "极速预习复习"}
        assert all(
            item.relation == "direct" and item.weight >= 0.85
            for item in understanding.matched_business_concepts
        )


def test_animation_course_quality_phrase_is_a_trusted_animation_intent():
    understanding = QueryUnderstandingService().understand_locally("体现动画课很好")

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "动画精讲"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["动画精讲"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_photo_guided_flow_keeps_fallback_animation_subordinate():
    query = "孩子拍一拍不会的题，AI先问步骤、讲思路，不懂再推对应知识点动画课，学会为止"
    understanding = QueryUnderstandingService().understand_locally(query)

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI拍题精学"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_learning_outcome_visibility_keeps_report_and_quiz_as_shared_candidates():
    understanding = QueryUnderstandingService().understand_locally(
        "随时能看到学习成果"
    )

    assert understanding is not None
    assert understanding.query_type == "exploratory_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"课后小测", "学情报告反馈"}
    assert all(
        item.relation == "direct" and item.weight >= 0.85
        for item in understanding.matched_business_concepts
    )


def test_level_matched_virtual_class_is_trusted_ai_learning_plan():
    query = "动态组建一个与你水平相匹配的虚拟班级，安排个性化的学习节奏与内容"
    understanding = QueryUnderstandingService().understand_locally(query)

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI定制学习方案"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI定制学习方案"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_heuristic_questioning_phrase_is_a_trusted_photo_guided_intent():
    # D078：该话术是拍题精学“苏格拉底式提问”的方法论表达，覆盖 D072 的旧归属。
    understanding = QueryUnderstandingService().understand_locally(
        "通过启发式提问，还原思考过程，帮你从‘解一题’到‘通一类’"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI拍题精学"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI拍题精学"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.85


def test_explicit_ai_tutor_outweighs_generic_weakness_neighbor_terms():
    understanding = QueryUnderstandingService().understand_locally(
        "量身打造一对一AI私教，24小时答疑解惑，精准定位知识薄弱点"
    )

    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert understanding.normalized_query == "AI私教答疑"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["AI私教答疑"]
    assert understanding.matched_business_concepts[0].relation == "direct"
    assert understanding.matched_business_concepts[0].weight >= 0.95


def test_weak_ambiguous_entry_keeps_equal_neighboring_candidates():
    understanding = QueryUnderstandingService().understand_locally("复习")

    assert understanding is not None
    assert understanding.query_type == "ambiguous_business_intent_search"
    assert {
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    } == {"极速预习复习", "AI错题本"}
    assert all(
        item.relation == "related"
        for item in understanding.matched_business_concepts
    )


def test_pure_negative_query_produces_excluded_concepts_only():
    understanding = QueryUnderstandingService().understand_locally("不需要真人老师督学")

    assert understanding is not None
    assert understanding.query_type == "no_reliable_intent_search"
    assert understanding.matched_business_concepts == []
    assert "同步伴学体系 > 真人老师督学" in understanding.excluded_concepts


def test_negated_concept_is_excluded_while_positive_concept_stays():
    understanding = QueryUnderstandingService().understand_locally(
        "不需要真人老师督学，想看学情报告"
    )

    assert understanding is not None
    assert understanding.normalized_query == "学情报告反馈"
    assert "同步伴学体系 > 真人老师督学" in understanding.excluded_concepts
    matched_names = [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ]
    assert "真人老师督学" not in matched_names


def test_negation_phrase_in_seed_vocabulary_still_matches_positively():
    understanding = QueryUnderstandingService().understand_locally("拍题后不要直接给答案")

    assert understanding is not None
    assert understanding.normalized_query == "AI拍题精学"
    assert understanding.query_type in {
        "business_intent_search",
        "multi_business_intent_search",
        "exploratory_business_intent_search",
    }


def _concept_hit(code: str, name: str, relation_role: str = "expresses") -> SearchHit:
    concept = BusinessConcept(code=code, name=name)
    image = Image(
        title=f"{name}素材",
        file_name=f"{code}.png",
        storage_key=f"{code}.png",
        thumbnail_storage_key=f"{code}-thumb.png",
        media_type="image/png",
        size_bytes=100,
        uploader="designer",
        asset_group=AssetGroup(
            title=f"{name}素材组",
            created_by="designer",
            concept_links=[
                AssetConceptLink(
                    concept=concept,
                    relation_role=relation_role,
                    origin="manual",
                    review_status="accepted",
                )
            ],
        ),
    )
    return SearchHit(image=image, score=0.9, reasons=("测试",))


def test_routing_drops_assets_expressing_query_excluded_concepts():
    excluded_hit = _concept_hit("human_teacher_supervision", "真人老师督学")
    kept_hit = _concept_hit("learning_report", "学情报告反馈")
    understanding = QueryUnderstandingService().understand_locally(
        "不需要真人老师督学，想看学情报告"
    )
    assert understanding is not None

    outcome = SearchConceptRoutingService().route(
        [excluded_hit, kept_hit],
        [],
        keyword="不需要真人老师督学，想看学情报告",
        understanding=understanding,
    )

    titles = [hit.image.title for hit in outcome.hits]
    assert "真人老师督学素材" not in titles
    assert "学情报告反馈素材" in titles


def test_runtime_catalog_prefers_database_names_and_reviewed_phrases(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="animation_explanation",
            name="动画讲解精学",
            system_links=[ConceptSystemLink(system_tag=system)],
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="孩子看动画就能听懂",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                ),
                ConceptSearchPhrase(
                    phrase="动画精讲",
                    phrase_type="official",
                    origin="source_document",
                    review_status="rejected",
                ),
            ],
        )
        new_concept = BusinessConcept(
            code="parent_worry_free",
            name="家长省心陪学",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="家长不用天天盯着孩子",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                ),
                ConceptSearchPhrase(
                    phrase="星图",
                    phrase_type="alias",
                    origin="manual",
                    review_status="accepted",
                ),
            ],
        )
        db.add_all([system, concept, new_concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    by_code = {intent.code: intent for intent in catalog.intents}
    merged = by_code["animation_explanation"]
    assert merged.name == "动画讲解精学"
    assert merged.display_name == "同步校内体系 > 动画讲解精学"
    assert "孩子看动画就能听懂" in merged.pain_points
    assert "动画精讲" not in merged.phrases

    added = by_code["parent_worry_free"]
    assert added.name == "家长省心陪学"
    assert "家长不用天天盯着孩子" in added.pain_points
    assert "星图" in added.exact_only_phrases

    service = QueryUnderstandingService(runtime_catalog=catalog)
    exact = service.understand_locally("星图")
    assert exact is not None
    assert exact.normalized_query == "家长省心陪学"
    assert exact.matched_business_concepts[0].relation == "direct"

    sentence = service.understand_locally("我想找星图风格的素材")
    assert sentence is None or all(
        "家长省心陪学" not in item.concept
        for item in sentence.matched_business_concepts
    )


def test_runtime_catalog_prefers_core_system_over_support_order(db_factory):
    with db_factory() as db:
        support_system = Tag(
            code="sync_exam",
            name="同步考点体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        core_system = Tag(
            code="sync_self_study",
            name="同步自学体系",
            color="#22C55E",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="ai_error_book",
            name="AI错题本",
            system_links=[
                ConceptSystemLink(
                    system_tag=support_system,
                    role="support",
                ),
                ConceptSystemLink(
                    system_tag=core_system,
                    role="core",
                ),
            ],
        )
        db.add_all([support_system, core_system, concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    merged = next(item for item in catalog.intents if item.code == "ai_error_book")
    assert merged.display_name == "同步自学体系 > AI错题本"


def test_static_exact_mode_is_not_upgraded_by_database_seed_phrase(db_factory):
    with db_factory() as db:
        system = Tag(
            code="sync_school",
            name="同步校内体系",
            color="#6366F1",
            node_type="system",
            assignable=False,
            status="active",
        )
        concept = BusinessConcept(
            code="instant_quiz",
            name="课后小测",
            system_links=[
                ConceptSystemLink(system_tag=system, role="core"),
            ],
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="正确率",
                    phrase_type="official",
                    origin="source_document",
                    review_status="accepted",
                )
            ],
        )
        db.add_all([system, concept])
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    merged = next(item for item in catalog.intents if item.code == "instant_quiz")
    assert "正确率" in merged.exact_only_phrases
    assert "正确率" not in merged.phrases

    understanding = QueryUnderstandingService(runtime_catalog=catalog).understand_locally(
        "每周学习报告汇总时长、正确率和薄弱点给家长"
    )
    assert understanding is not None
    assert understanding.query_type == "business_intent_search"
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["学情报告反馈"]


def test_rejected_old_method_phrase_does_not_override_transfer_intent(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(
            code="universal_method",
            name="万能解法",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="一道题学会一类题",
                    phrase_type="official",
                    origin="source_document",
                    review_status="rejected",
                )
            ],
        )
        db.add(concept)
        db.commit()

        catalog = IntentCatalogService(BusinessConceptRepository(db)).runtime_catalog()

    understanding = QueryUnderstandingService(runtime_catalog=catalog).understand_locally(
        "一道题学会一类题"
    )
    assert understanding is not None
    assert [
        item.concept.rsplit(">", 1)[-1].strip()
        for item in understanding.matched_business_concepts
    ] == ["举一反三"]


def test_search_service_understands_database_only_concepts(db_factory):
    with db_factory() as db:
        concept = BusinessConcept(
            code="parent_worry_free",
            name="家长省心陪学",
            search_phrases=[
                ConceptSearchPhrase(
                    phrase="家长不用天天盯着孩子",
                    phrase_type="pain",
                    origin="manual",
                    review_status="accepted",
                )
            ],
        )
        db.add(concept)
        db.commit()

        service = SearchService(db)
        understanding = service.query_understanding.understand_locally(
            "家长不用天天盯着孩子"
        )

    assert understanding is not None
    assert understanding.normalized_query == "家长省心陪学"
    assert understanding.matched_business_concepts[0].relation == "direct"
