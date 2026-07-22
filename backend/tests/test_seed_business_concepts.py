import sys
from pathlib import Path

from sqlalchemy import select

from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.business_concept import BusinessConcept
from app.models.tag import Tag

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.seed_business_concepts import sync_business_concepts  # noqa: E402


def _seed_system_tags(db):
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


def test_seed_does_not_overwrite_manual_concept_edits(db_factory):
    with db_factory() as db:
        _seed_system_tags(db)
        sync_business_concepts(db)
        db.commit()

        concept = db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.code == "animation_explanation"
            )
        )
        assert concept is not None
        concept.name = "动画讲解精学"
        concept.definition = "设计师手工维护的定义。"
        rejected_phrase = next(
            item for item in concept.search_phrases if item.phrase == "动画精讲"
        )
        rejected_phrase.review_status = "rejected"
        db.commit()

        created, updated, _phrases, _relations = sync_business_concepts(db)
        db.commit()

        refreshed = db.scalar(
            select(BusinessConcept).where(
                BusinessConcept.code == "animation_explanation"
            )
        )

    assert created == 0
    assert updated == 0
    assert refreshed.name == "动画讲解精学"
    assert refreshed.definition == "设计师手工维护的定义。"
    assert (
        next(
            item
            for item in refreshed.search_phrases
            if item.phrase == "动画精讲"
        ).review_status
        == "rejected"
    )


def test_seed_is_idempotent_for_phrases_and_relations(db_factory):
    with db_factory() as db:
        _seed_system_tags(db)
        first = sync_business_concepts(db)
        db.commit()
        second = sync_business_concepts(db)
        db.commit()

    assert first[0] > 0
    assert second == (0, 0, 0, 0)
