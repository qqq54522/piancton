from collections import Counter

from app.domain.business_intents import load_business_intents
from app.domain.search_eval import (
    display_name_for_label,
    expected_display_name,
    load_search_eval_cases,
)
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.services.query_understanding_service import QueryUnderstandingService


def test_search_eval_cases_have_cumulative_batches():
    catalog = load_search_eval_cases()

    assert len(catalog.cases_for_batch(1)) == 15
    assert len(catalog.cumulative_cases(1)) == 15
    assert len(catalog.cumulative_cases(2)) == 30
    assert len(catalog.cumulative_cases(3)) == 50
    assert len(catalog.cumulative_cases(4)) == 75
    assert len(catalog.cumulative_cases(5)) == 103
    assert [case.id for case in catalog.cases[:3]] == ["SE001", "SE002", "SE003"]


def test_search_eval_cases_cover_six_systems_and_taxonomy_labels():
    catalog = load_search_eval_cases()
    taxonomy = load_taxonomy_catalog()
    system_counts = Counter(
        case.expected_system_code
        for case in catalog.cases
        if case.expected_system_code
    )
    label_codes = {
        case.expected_label_code
        for case in catalog.cases
        if case.expected_label_code
    }

    assert set(system_counts) == {
        "sync_school",
        "sync_exam",
        "sync_cultivation",
        "sync_planning",
        "sync_self_study",
        "sync_companion",
    }
    assert all(count >= 3 for count in system_counts.values())
    assert label_codes == {node.code for node in taxonomy.image_label_nodes}
    assert expected_display_name(catalog.cases[0]) == "同步自学体系 > AI错题本"


def test_every_business_intent_has_search_eval_coverage():
    intents = load_business_intents()
    eval_cases = load_search_eval_cases()
    covered_label_codes = {case.expected_label_code for case in eval_cases.cases}

    assert {
        intent.target_label_code for intent in intents.intents
    }.issubset(covered_label_codes)


def test_search_eval_queries_map_to_expected_local_business_intents():
    service = QueryUnderstandingService()
    catalog = load_search_eval_cases()

    for case in catalog.cumulative_cases(3):
        understanding = service.understand_locally(case.query)

        assert understanding is not None, case.id
        if case.expected_query_type:
            assert understanding.query_type == case.expected_query_type, case.id
            continue
        assert understanding.matched_business_concepts[0].concept == expected_display_name(
            case
        ), case.id


def test_batch4_query_states_cover_multi_exploratory_ambiguous_visual_negation():
    catalog = load_search_eval_cases()
    batch4 = catalog.cases_for_batch(4)
    state_counts = Counter(case.expected_query_type for case in batch4)

    assert len(batch4) == 25
    assert state_counts["multi_business_intent_search"] == 4
    assert state_counts["exploratory_business_intent_search"] == 5
    assert state_counts["ambiguous_business_intent_search"] == 5
    assert state_counts["visual_scene_search"] == 5
    assert state_counts["no_reliable_intent_search"] + state_counts[
        "business_intent_search"
    ] == 6


def test_batch4_local_understanding_matches_expected_query_states():
    service = QueryUnderstandingService()
    catalog = load_search_eval_cases()

    for case in catalog.cases_for_batch(4):
        understanding = service.understand_locally(case.query)

        if case.expected_query_type == "visual_scene_search":
            # 纯画面查询没有可靠卖点，本地不产出理解，交给全局画面召回。
            assert understanding is None, case.id
            continue

        assert understanding is not None, case.id
        assert understanding.query_type == case.expected_query_type, case.id

        matched = {
            item.concept for item in understanding.matched_business_concepts
        }
        for code in case.expected_concept_codes:
            assert display_name_for_label(code) in matched, f"{case.id}:{code}"

        for code in case.expected_excluded_concept_codes:
            assert display_name_for_label(code) in understanding.excluded_concepts, (
                f"{case.id}:{code}"
            )
            assert display_name_for_label(code) not in matched, f"{case.id}:{code}"


def test_batch5_cross_system_calibration_matches_local_understanding():
    service = QueryUnderstandingService()
    catalog = load_search_eval_cases()
    batch5 = catalog.cases_for_batch(5)

    assert len(batch5) == 28
    assert Counter(case.expected_query_type for case in batch5) == {
        "business_intent_search": 20,
        "multi_business_intent_search": 4,
        "exploratory_business_intent_search": 2,
        "ambiguous_business_intent_search": 2,
    }

    for case in batch5:
        understanding = service.understand_locally(case.query)

        assert understanding is not None, case.id
        assert understanding.query_type == case.expected_query_type, case.id

        matched = {
            item.concept for item in understanding.matched_business_concepts
        }
        for code in case.expected_concept_codes:
            assert display_name_for_label(code) in matched, f"{case.id}:{code}"

        for code in case.expected_excluded_concept_codes:
            expected = display_name_for_label(code)
            assert expected in understanding.excluded_concepts, f"{case.id}:{code}"
            assert expected not in matched, f"{case.id}:{code}"
