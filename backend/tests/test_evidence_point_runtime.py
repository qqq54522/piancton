from app.ai.contracts import ModelRequest
from app.ai.normalizer import normalize_model_payload
from app.domain.evidence_points import load_evidence_point_catalog
from app.services.query_understanding_service import QueryUnderstandingService


def test_evidence_point_catalog_loads_green_source_expressions():
    catalog = load_evidence_point_catalog()

    assert len(catalog.points) == 58
    assert {item.system_code for item in catalog.points} == {
        "sync_school",
        "sync_exam",
        "sync_cultivation",
        "sync_planning",
        "sync_self_study",
        "sync_companion",
    }
    short_lesson = catalog.by_code["ep_school_short_animation_lesson"]
    assert short_lesson.proof_point_code == "pp_animation_pedagogy_design"
    assert short_lesson.concept_code == "animation_explanation"


def test_evidence_expression_can_establish_its_parent_proof_point():
    query = "孩子会听懂但不会做，想找讲完还有例题和变式训练的"
    service = QueryUnderstandingService()
    understanding = service.present_recognized_concepts(
        query,
        service.understand_locally(query),
        [],
    )

    assert understanding is not None
    assert [item.concept for item in understanding.matched_business_concepts] == [
        "同步考点体系 > 举一反三"
    ]
    assert [item.code for item in understanding.matched_proof_points] == [
        "pp_exam_transfer_variant_practice"
    ]
    assert [item.code for item in understanding.matched_evidence_points] == [
        "ep_exam_variant_expansion"
    ]


def test_model_evidence_points_are_canonicalized_and_unknown_codes_are_dropped():
    payload = normalize_model_payload(
        ModelRequest(task="search_intent_understanding", prompt=""),
        {
            "matched_business_concepts": [],
            "matched_evidence_points": [
                {
                    "code": "ep_exam_variant_expansion",
                    "proof_point_code": "invented_parent",
                    "concept_code": "invented_concept",
                    "name": "模型自造名称",
                    "reason": "语义匹配",
                    "weight": 0.94,
                },
                {"code": "ep_invented", "weight": 1},
            ],
        },
    )

    assert payload["matched_evidence_points"] == [
        {
            "code": "ep_exam_variant_expansion",
            "proof_point_code": "pp_exam_transfer_variant_practice",
            "concept_code": "transfer_practice",
            "name": "讲完例题后进行同类变式拓展",
            "reason": "语义匹配",
            "weight": 0.94,
        }
    ]


def test_manual_all_proof_points_stops_automatic_proof_completion():
    class Provider:
        configured = True

    class Ai:
        provider = Provider()

    service = QueryUnderstandingService(ai_service=Ai())
    understanding = service.explicit_understanding(
        "动态组建虚拟班级并安排个性化学习节奏",
        concept_code="ai_learning_plan",
        proof_point_code=None,
        evidence_point_code=None,
    )

    assert understanding is not None
    assert understanding.matched_proof_points == []
    assert not service.needs_proof_point_completion(
        understanding.original_query,
        understanding,
    )
    assert not service.should_use_model(understanding.original_query, understanding)
