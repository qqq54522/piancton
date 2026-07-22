import pytest

from app.ai.contracts import ModelRequest
from app.ai.normalizer import normalize_model_payload
from app.domain.proof_points import load_proof_point_catalog
from app.schemas.ai import (
    SearchConceptMatch,
    SearchProofPointMatch,
    SearchUnderstanding,
)
from app.services.query_understanding_service import QueryUnderstandingService


def test_proof_point_catalog_loads_all_six_systems_and_56_points():
    catalog = load_proof_point_catalog()

    assert len(catalog.points) == 56
    assert {item.system_code for item in catalog.points} == {
        "sync_school",
        "sync_exam",
        "sync_cultivation",
        "sync_planning",
        "sync_self_study",
        "sync_companion",
    }
    assert all(item.concept_code and item.search_terms for item in catalog.points)


def test_local_understanding_adds_specific_proof_but_not_generic_selling_point():
    service = QueryUnderstandingService()

    specific = service.understand_locally("做错的题自动收集归类到错题本")
    specific = service.present_recognized_concepts(
        "做错的题自动收集归类到错题本", specific, []
    )
    generic = service.understand_locally("AI错题本")
    generic = service.present_recognized_concepts("AI错题本", generic, [])

    assert specific is not None
    assert [item.code for item in specific.matched_proof_points] == [
        "pp_selfstudy_error_photo_capture"
    ]
    assert specific.matched_proof_points[0].concept_code == "ai_error_book"
    assert generic is not None
    assert generic.matched_proof_points == []


def test_parent_delivery_detail_beats_generic_report_proof():
    service = QueryUnderstandingService()
    understanding = service.understand_locally("微信学习周报")
    understanding = service.present_recognized_concepts(
        "微信学习周报", understanding, []
    )

    assert understanding is not None
    assert [item.code for item in understanding.matched_proof_points] == [
        "pp_companion_report_parent_delivery"
    ]


def test_error_book_source_detail_establishes_parent_before_proof_point():
    service = QueryUnderstandingService()
    understanding = service.understand_locally("错题后再练3-5道同类题")
    understanding = service.present_recognized_concepts(
        "错题后再练3-5道同类题", understanding, []
    )

    assert understanding is not None
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步自学体系 > AI错题本"]
    assert [item.code for item in understanding.matched_proof_points] == [
        "pp_selfstudy_error_variant_recommendation"
    ]


@pytest.mark.parametrize(
    "query",
    [
        "找那种几分钟就能讲明白一个知识点的图",
        "有没有一节课不长，但一个点能讲透的",
    ],
)
def test_short_animation_micro_lesson_detail_establishes_proof_point(query: str):
    service = QueryUnderstandingService()
    understanding = service.understand_locally(query)
    understanding = service.present_recognized_concepts(query, understanding, [])

    assert understanding is not None
    assert [
        item.concept for item in understanding.matched_business_concepts
    ] == ["同步校内体系 > 动画精讲"]
    assert [item.code for item in understanding.matched_proof_points] == [
        "pp_animation_pedagogy_design"
    ]


def test_unseen_detail_requests_scoped_proof_completion_but_generic_lookup_does_not():
    class Provider:
        configured = True

    class ScopedAi:
        provider = Provider()
        knowledge = None

        def route_search_system(self, _keyword: str):
            raise AssertionError("父卖点已确认，不应重新调用体系路由")

        def understand_search_from_route(self, keyword: str, routing):
            assert [item.code for item in routing.candidate_systems] == ["sync_school"]
            return SearchUnderstanding(
                original_query=keyword,
                normalized_query="动画精讲",
                search_intent="短时、单点讲透",
                query_type="business_intent_search",
                matched_business_concepts=[
                    SearchConceptMatch(
                        concept="animation_explanation",
                        relation="direct",
                        reason="动画讲解",
                        weight=0.98,
                    )
                ],
                matched_proof_points=[
                    SearchProofPointMatch(
                        code="pp_animation_pedagogy_design",
                        concept_code="animation_explanation",
                        name="官方产品定位与教研方法论",
                        reason="别拖太久、每回只消化一个小点",
                        weight=0.96,
                        evidence_terms=["5-8 分钟动画微课"],
                    )
                ],
            )

    service = QueryUnderstandingService(ai_service=ScopedAi())
    query = "要动画讲解的，别拖太久，每回只消化一个小点"
    local = service.understand_locally(query)
    generic = service.understand_locally("帮我找动画精讲图片")

    assert local is not None
    assert local.matched_proof_points == []
    assert service.needs_proof_point_completion(query, local)
    assert service.should_use_model(query, local)
    assert generic is not None
    assert not service.needs_proof_point_completion("帮我找动画精讲图片", generic)
    assert not service.should_use_model("帮我找动画精讲图片", generic)

    model = service.complete_proof_points_with_model(query, local)
    merged = service.arbitrate_model_understanding(local, model)

    assert merged is not None
    assert [item.concept for item in merged.matched_business_concepts] == [
        "同步校内体系 > 动画精讲"
    ]
    assert [item.code for item in merged.matched_proof_points] == [
        "pp_animation_pedagogy_design"
    ]


def test_model_proof_points_are_canonicalized_and_unknown_codes_are_dropped():
    payload = normalize_model_payload(
        ModelRequest(task="search_intent_understanding", prompt=""),
        {
            "query_type": "business_intent_search",
            "matched_business_concepts": [],
            "matched_proof_points": [
                {
                    "code": "pp_selfstudy_error_photo_capture",
                    "concept_code": "wrong_parent",
                    "name": "模型自造名称",
                    "reason": "明确描述错题归档",
                    "weight": 0.93,
                    "evidence_terms": ["拍照上传错题", "模型自造线索"],
                },
                {
                    "code": "pp_invented",
                    "concept_code": "ai_error_book",
                    "name": "不存在",
                    "reason": "模型自造",
                    "weight": 0.99,
                },
            ],
        },
    )

    assert payload["matched_proof_points"] == [
        {
            "code": "pp_selfstudy_error_photo_capture",
            "concept_code": "ai_error_book",
            "name": "线下错题拍照上传与归档",
            "reason": "明确描述错题归档",
            "weight": 0.93,
            "evidence_terms": ["拍照上传错题"],
        }
    ]
