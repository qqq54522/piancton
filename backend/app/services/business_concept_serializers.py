from __future__ import annotations

from typing import Literal, cast

from app.models.business_concept import BusinessConcept, ConceptRelation
from app.schemas.business_concept import (
    BusinessConceptRead,
    ConceptRelationRead,
    ConceptSearchPhraseRead,
    ConceptSystemLinkRead,
)


def concept_to_read(concept: BusinessConcept) -> BusinessConceptRead:
    return BusinessConceptRead(
        id=concept.id,
        code=concept.code,
        name=concept.name,
        concept_type=concept.concept_type,
        definition=concept.definition,
        recommendation_text=concept.recommendation_text,
        status=concept.status,
        version=concept.version,
        replaced_by_concept_id=concept.replaced_by_concept_id,
        system_links=[
            ConceptSystemLinkRead(
                system_tag_id=item.system_tag_id,
                system_name=item.system_tag.name,
                role=cast(
                    Literal["core", "support", "evidence", "related"], item.role
                ),
                weight=item.weight,
                reason=item.reason,
                status=item.status,
            )
            for item in concept.system_links
        ],
        search_phrases=[
            ConceptSearchPhraseRead.model_validate(item)
            for item in concept.search_phrases
        ],
        created_at=concept.created_at,
        updated_at=concept.updated_at,
    )


def relation_to_read(relation: ConceptRelation) -> ConceptRelationRead:
    return ConceptRelationRead(
        id=relation.id,
        source_concept_id=relation.source_concept_id,
        target_concept_id=relation.target_concept_id,
        relation_type=cast(
            Literal[
                "broader_than",
                "narrower_than",
                "supports",
                "similar_to",
                "distinguishes_from",
                "conflicts_with",
            ],
            relation.relation_type,
        ),
        reason=relation.reason,
        status=relation.status,
    )
