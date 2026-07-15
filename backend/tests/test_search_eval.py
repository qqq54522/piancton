from collections import Counter

from app.domain.business_intents import load_business_intents
from app.domain.search_eval import expected_display_name, load_search_eval_cases
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.services.query_understanding_service import QueryUnderstandingService


def test_search_eval_cases_have_15_30_50_cumulative_batches():
    catalog = load_search_eval_cases()

    assert len(catalog.cases_for_batch(1)) == 15
    assert len(catalog.cumulative_cases(1)) == 15
    assert len(catalog.cumulative_cases(2)) == 30
    assert len(catalog.cumulative_cases(3)) == 50
    assert [case.id for case in catalog.cases[:3]] == ["SE001", "SE002", "SE003"]


def test_search_eval_cases_cover_six_systems_and_taxonomy_labels():
    catalog = load_search_eval_cases()
    taxonomy = load_taxonomy_catalog()
    system_counts = Counter(case.expected_system_code for case in catalog.cases)
    label_codes = {case.expected_label_code for case in catalog.cases}

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

    for case in catalog.cases:
        understanding = service.understand_locally(case.query)

        assert understanding is not None, case.id
        assert understanding.matched_business_concepts[0].concept == expected_display_name(
            case
        ), case.id
