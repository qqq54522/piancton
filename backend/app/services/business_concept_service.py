from __future__ import annotations

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.business_concept import (
    BusinessConcept,
    ConceptRelation,
    ConceptSystemLink,
)
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.business_concept import (
    BusinessConceptCreate,
    BusinessConceptAssetRead,
    BusinessConceptRead,
    BusinessConceptUpdate,
    ConceptRelationCreate,
    ConceptRelationRead,
)
from app.services.business_concept_serializers import concept_to_read, relation_to_read
from app.services.serializers import image_to_read
from app.services.unit_of_work import UnitOfWork


class BusinessConceptService:
    """Owns concept lifecycle; legacy tags are only validated system references."""

    def __init__(self, db):
        self.concepts = BusinessConceptRepository(db)
        self.tags = TagRepository(db)
        self.uow = UnitOfWork(db)

    def list(self, *, include_inactive: bool = False) -> list[BusinessConceptRead]:
        return [
            concept_to_read(item)
            for item in self.concepts.list(include_inactive=include_inactive)
        ]

    def get(self, concept_id: str) -> BusinessConceptRead:
        return concept_to_read(self._get(concept_id))

    def list_assets(self, concept_id: str) -> list[BusinessConceptAssetRead]:
        self._get(concept_id)
        return [
            BusinessConceptAssetRead(
                image=image_to_read(image),
                relation_role=relation_role,
            )
            for image, relation_role in self.concepts.list_assets(concept_id)
        ]

    def create(self, payload: BusinessConceptCreate) -> BusinessConceptRead:
        if self.concepts.get_by_code(payload.code):
            raise ConflictError("concept_code_exists", "业务概念 code 已存在")
        concept = BusinessConcept(
            code=payload.code,
            name=payload.name.strip(),
            concept_type=payload.concept_type.strip(),
            definition=(payload.definition or "").strip() or None,
            recommendation_text=(payload.recommendation_text or "").strip() or None,
            system_links=self._system_links(payload.system_links),
        )
        self.concepts.add(concept)
        self.uow.commit()
        return concept_to_read(self._get(concept.id))

    def update(self, concept_id: str, payload: BusinessConceptUpdate) -> BusinessConceptRead:
        concept = self._get(concept_id)
        values = payload.model_dump(exclude_unset=True)
        replacement_id = values.get("replaced_by_concept_id")
        if replacement_id:
            if replacement_id == concept.id:
                raise AppError("invalid_concept_replacement", "业务概念不能替代自身")
            self._get(replacement_id)
        if (
            values.get("status") == "merged"
            and not replacement_id
            and not concept.replaced_by_concept_id
        ):
            raise AppError("concept_replacement_required", "合并概念必须指定替代概念")
        for field in (
            "name",
            "concept_type",
            "definition",
            "recommendation_text",
            "status",
            "replaced_by_concept_id",
        ):
            if field in values:
                value = values[field]
                if isinstance(value, str):
                    value = value.strip() or None
                setattr(concept, field, value)
        if payload.system_links is not None:
            concept.system_links[:] = self._system_links(payload.system_links)
        concept.version += 1
        self.concepts.save(concept)
        self.uow.commit()
        return concept_to_read(self._get(concept.id))

    def add_relation(
        self, source_id: str, payload: ConceptRelationCreate
    ) -> ConceptRelationRead:
        self._get(source_id)
        self._get(payload.target_concept_id)
        if source_id == payload.target_concept_id:
            raise AppError("invalid_concept_relation", "概念不能关联自身")
        relation = ConceptRelation(
            source_concept_id=source_id,
            target_concept_id=payload.target_concept_id,
            relation_type=payload.relation_type,
            reason=(payload.reason or "").strip() or None,
        )
        self.concepts.add_relation(relation)
        self.uow.commit()
        return relation_to_read(relation)

    def _system_links(self, inputs) -> list[ConceptSystemLink]:
        ids = [item.system_tag_id for item in inputs]
        tags = self.tags.get_many(ids)
        by_id = {item.id: item for item in tags}
        invalid = [
            tag_id
            for tag_id in ids
            if tag_id not in by_id or by_id[tag_id].status != "active"
        ]
        if invalid:
            raise AppError(
                "invalid_concept_system",
                "概念只能关联启用中的六大体系",
                details=invalid,
            )
        return [
            ConceptSystemLink(
                system_tag=by_id[item.system_tag_id],
                role=item.role,
                weight=item.weight,
                reason=(item.reason or "").strip() or None,
            )
            for item in inputs
        ]

    def _get(self, concept_id: str) -> BusinessConcept:
        concept = self.concepts.get(concept_id)
        if not concept:
            raise NotFoundError("business_concept_not_found", "业务概念不存在")
        return concept
