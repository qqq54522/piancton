from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import (
    BusinessConcept,
    ConceptRelation,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.image import Image

CONCEPT_LOAD_OPTIONS = (
    selectinload(BusinessConcept.system_links).selectinload(ConceptSystemLink.system_tag),
    selectinload(BusinessConcept.search_phrases),
    selectinload(BusinessConcept.replacement),
)


class BusinessConceptRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, *, include_inactive: bool = False) -> list[BusinessConcept]:
        stmt = select(BusinessConcept).options(*CONCEPT_LOAD_OPTIONS)
        if not include_inactive:
            stmt = stmt.where(BusinessConcept.status == "active")
        return list(
            self.db.scalars(
                stmt.order_by(BusinessConcept.name, BusinessConcept.code)
            ).all()
        )

    def get(self, concept_id: str) -> BusinessConcept | None:
        return self.db.scalar(
            select(BusinessConcept)
            .where(BusinessConcept.id == concept_id)
            .options(*CONCEPT_LOAD_OPTIONS)
        )

    def get_by_code(self, code: str) -> BusinessConcept | None:
        return self.db.scalar(
            select(BusinessConcept)
            .where(BusinessConcept.code == code)
            .options(*CONCEPT_LOAD_OPTIONS)
        )

    def get_many_by_codes(self, codes: list[str]) -> list[BusinessConcept]:
        if not codes:
            return []
        rows = list(
            self.db.scalars(
                select(BusinessConcept)
                .where(BusinessConcept.code.in_(codes))
                .options(*CONCEPT_LOAD_OPTIONS)
            ).all()
        )
        by_code = {row.code: row for row in rows}
        return [by_code[code] for code in codes if code in by_code]

    def get_many_by_ids(self, concept_ids: list[str]) -> list[BusinessConcept]:
        if not concept_ids:
            return []
        rows = list(
            self.db.scalars(
                select(BusinessConcept)
                .where(
                    BusinessConcept.id.in_(concept_ids),
                    BusinessConcept.status == "active",
                )
                .options(*CONCEPT_LOAD_OPTIONS)
            ).all()
        )
        by_id = {row.id: row for row in rows}
        return [by_id[concept_id] for concept_id in concept_ids if concept_id in by_id]

    def list_assets(
        self,
        concept_id: str,
        *,
        limit: int = 200,
    ) -> list[tuple[Image, str]]:
        stmt = (
            select(Image, AssetConceptLink.relation_role)
            .join(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .join(
                AssetConceptLink,
                AssetConceptLink.asset_group_id == AssetGroup.id,
            )
            .where(
                AssetConceptLink.concept_id == concept_id,
                AssetConceptLink.review_status == "accepted",
                AssetConceptLink.relation_role.in_(("expresses", "supports")),
                AssetGroup.publish_status == "published",
                Image.deleted_at.is_(None),
                Image.is_current.is_(True),
            )
            .options(
                selectinload(Image.asset_group).selectinload(AssetGroup.images),
            )
            .order_by(desc(Image.created_at), desc(Image.id))
            .limit(limit)
        )
        return [(image, str(role)) for image, role in self.db.execute(stmt).all()]

    def get_phrase(self, concept_id: str, phrase_id: str) -> ConceptSearchPhrase | None:
        return self.db.scalar(
            select(ConceptSearchPhrase).where(
                ConceptSearchPhrase.id == phrase_id,
                ConceptSearchPhrase.concept_id == concept_id,
            )
        )

    def add(self, concept: BusinessConcept) -> BusinessConcept:
        self.db.add(concept)
        self.db.flush()
        return concept

    def save(self, value) -> None:
        self.db.add(value)
        self.db.flush()

    def add_relation(self, relation: ConceptRelation) -> ConceptRelation:
        self.db.add(relation)
        self.db.flush()
        return relation
