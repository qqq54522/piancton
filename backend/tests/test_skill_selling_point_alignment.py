import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.domain.business_intents import load_business_intents
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase
from app.models.tag import Tag
from app.services.query_understanding_service import QueryUnderstandingService

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.seed_business_concepts import sync_business_concepts  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "skills" / "understand-image-search-intent"
MAP_PATH = SKILL_DIR / "references" / "selling-point-map.json"
PHRASE_GOVERNANCE_PATH = (
    SKILL_DIR / "references" / "public-phrase-governance.json"
)


def _load_map() -> dict:
    return json.loads(MAP_PATH.read_text(encoding="utf-8"))


def _load_phrase_governance() -> dict:
    return json.loads(PHRASE_GOVERNANCE_PATH.read_text(encoding="utf-8"))


def _mapped_points() -> list[tuple[dict, dict]]:
    return [
        (system, point)
        for system in _load_map()["systems"]
        for point in system["sellingPoints"]
    ]


def _seed_system_tags(db) -> None:
    for node in load_taxonomy_catalog().system_nodes:
        db.add(
            Tag(
                code=node.code,
                name=node.name,
                color=node.color,
                node_type="system",
                assignable=False,
                status="active",
            )
        )
    db.flush()


def test_simplified_catalog_maps_one_to_one_to_skill_references():
    mapping = _load_map()
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code
    mapped = _mapped_points()
    mapped_codes = [point["code"] for _system, point in mapped]

    assert len(mapping["systems"]) == 6
    assert len(mapped_codes) == 16
    assert len(mapped_codes) == len(set(mapped_codes))
    assert set(mapped_codes) == {node.code for node in catalog.image_label_nodes}

    for system, point in mapped:
        assert node_by_code[system["code"]].name == system["displayName"]
        reference = (SKILL_DIR / "references" / system["reference"]).read_text(
            encoding="utf-8"
        )
        node = node_by_code[point["code"]]
        assert node.name == point["displayName"]
        assert node.parent_code == system["code"]
        assert f"`{point['code']}`" in reference
        assert point["skillName"] in reference


def test_seeded_database_catalog_keeps_the_same_stable_mapping(db_factory):
    expected = {point["code"]: (system, point) for system, point in _mapped_points()}
    with db_factory() as db:
        _seed_system_tags(db)
        sync_business_concepts(db)
        db.commit()
        concepts = db.scalars(select(BusinessConcept)).all()

        assert {concept.code for concept in concepts} == set(expected)
        for concept in concepts:
            system, point = expected[concept.code]
            assert concept.status == "active"
            assert concept.name == point["displayName"]
            assert {
                link.system_tag.code
                for link in concept.system_links
                if link.status == "active" and link.role == "core"
            } == {system["code"]}


def test_public_phrase_layer_can_only_reference_the_frozen_selling_points():
    governance = _load_phrase_governance()
    mapped_codes = {point["code"] for _system, point in _mapped_points()}
    catalog = load_business_intents()
    intent_by_label = {
        intent.target_label_code: intent for intent in catalog.intents
    }
    additions = governance["approvedAdditions"]

    assert governance["limits"]["allowNewSystemOrSellingPoint"] is False
    assert governance["limits"]["evaluationExamplesArePublicPhrases"] is False
    assert len(additions) == 16
    assert {item["code"] for item in additions} == mapped_codes
    assert len({item["code"] for item in additions}) == len(additions)
    assert len({item["phrase"] for item in additions}) == len(additions)

    for item in additions:
        assert item["phraseType"] == "official"
        assert item["phrase"] in intent_by_label[item["code"]].phrases

    for entry in governance["sharedEntries"]:
        assert set(entry["candidateCodes"]).issubset(mapped_codes)
        assert len(entry["candidateCodes"]) > 1

    approved_phrases = {item["phrase"] for item in additions}
    for entry in governance["interpretationSignals"]:
        assert entry["code"] in mapped_codes
        assert set(entry["signals"]).isdisjoint(approved_phrases)

    for entry in governance["explorationSignals"]:
        assert set(entry["candidateCodes"]).issubset(mapped_codes)
        assert len(entry["candidateCodes"]) > 1
        assert entry["entryTerms"]
        assert entry["purposeTerms"]


def test_public_phrase_examples_cover_three_business_familiarity_levels():
    governance = _load_phrase_governance()
    mapped_codes = {point["code"] for _system, point in _mapped_points()}
    cases = governance["evaluationCases"]

    assert len(cases) == 48
    for level in ("expert", "informed", "novice"):
        level_cases = [item for item in cases if item["level"] == level]
        assert len(level_cases) == 16
        assert {item["expectedCode"] for item in level_cases} == mapped_codes


def test_three_level_public_phrase_examples_keep_the_expected_selling_point():
    governance = _load_phrase_governance()
    node_by_code = load_taxonomy_catalog().node_by_code
    service = QueryUnderstandingService()

    assert f"skill-{governance['version']}" in service.catalog.version
    for case in governance["evaluationCases"]:
        understanding = service.understand_locally(case["query"])
        assert understanding is not None, case["id"]
        expected_name = node_by_code[case["expectedCode"]].name
        matched_names = {
            match.concept.rsplit(">", 1)[-1].strip()
            for match in understanding.matched_business_concepts
        }
        assert expected_name in matched_names, (
            case["id"],
            understanding.query_type,
            matched_names,
        )


def test_seed_rejects_old_phrases_that_conflict_with_skill_boundaries(db_factory):
    old_phrases = {"一道题会一类题", "一道题学会一类题"}
    with db_factory() as db:
        _seed_system_tags(db)
        sync_business_concepts(db)
        universal = db.scalar(
            select(BusinessConcept).where(BusinessConcept.code == "universal_method")
        )
        transfer = db.scalar(
            select(BusinessConcept).where(BusinessConcept.code == "transfer_practice")
        )
        assert universal is not None
        assert transfer is not None
        universal.search_phrases.extend(
            ConceptSearchPhrase(
                phrase=phrase,
                phrase_type="alias",
                origin="source_document",
                review_status="accepted",
            )
            for phrase in old_phrases
        )
        db.commit()

        created, updated, phrase_count, relation_count = sync_business_concepts(db)
        db.commit()

        assert (created, phrase_count, relation_count) == (0, 0, 0)
        assert updated == 1
        assert {
            item.phrase
            for item in universal.search_phrases
            if item.review_status == "rejected"
        }.issuperset(old_phrases)
        assert any(
            item.phrase == "一道题会一类题"
            and item.review_status == "accepted"
            for item in transfer.search_phrases
        )

        assert sync_business_concepts(db) == (0, 0, 0, 0)
