from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import AssetConceptLink, AssetGroup, AssetSourceLink
from app.models.business_concept import BusinessConcept, ConceptSystemLink
from app.models.image import Image


class SearchOpsRepository:
    """Read-only aggregates for concept-based search operations."""

    def __init__(self, db: Session):
        self.db = db

    def pending_ai_concept_links(self, *, limit: int = 50) -> list[AssetConceptLink]:
        stmt = (
            select(AssetConceptLink)
            .join(AssetGroup, AssetGroup.id == AssetConceptLink.asset_group_id)
            .where(
                AssetGroup.publish_status == "published",
                AssetConceptLink.origin == "ai",
                AssetConceptLink.review_status == "pending",
            )
            .options(
                selectinload(AssetConceptLink.asset_group),
                selectinload(AssetConceptLink.concept)
                .selectinload(BusinessConcept.system_links)
                .selectinload(ConceptSystemLink.system_tag),
            )
            .order_by(
                AssetConceptLink.confidence.desc().nullslast(),
                AssetConceptLink.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def active_concepts(self) -> list[BusinessConcept]:
        stmt = (
            select(BusinessConcept)
            .where(BusinessConcept.status == "active")
            .options(
                selectinload(BusinessConcept.system_links).selectinload(
                    ConceptSystemLink.system_tag
                )
            )
            .order_by(BusinessConcept.name.asc())
        )
        return list(self.db.scalars(stmt).all())

    def asset_counts_by_concept(self) -> dict[str, int]:
        rows = self.db.execute(
            select(
                AssetConceptLink.concept_id,
                func.count(func.distinct(AssetConceptLink.asset_group_id)),
            )
            .join(AssetGroup, AssetGroup.id == AssetConceptLink.asset_group_id)
            .where(
                AssetGroup.publish_status == "published",
                AssetConceptLink.review_status != "rejected",
                AssetConceptLink.relation_role != "excludes",
            )
            .group_by(AssetConceptLink.concept_id)
        ).all()
        return {concept_id: int(count) for concept_id, count in rows}

    def active_concept_links(self) -> list[AssetConceptLink]:
        stmt = (
            select(AssetConceptLink)
            .join(AssetGroup, AssetGroup.id == AssetConceptLink.asset_group_id)
            .where(AssetGroup.publish_status == "published")
        )
        return list(self.db.scalars(stmt).all())

    def published_asset_groups(self) -> list[AssetGroup]:
        stmt = (
            select(AssetGroup)
            .where(AssetGroup.publish_status == "published")
            .options(
                selectinload(AssetGroup.images),
                selectinload(AssetGroup.concept_links),
                selectinload(AssetGroup.search_phrases),
                selectinload(AssetGroup.source_links),
            )
            .order_by(AssetGroup.updated_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def recent_source_links(self, *, limit: int = 20) -> list[AssetSourceLink]:
        stmt = (
            select(AssetSourceLink)
            .join(AssetGroup, AssetGroup.id == AssetSourceLink.asset_group_id)
            .where(AssetGroup.publish_status == "published")
            .options(selectinload(AssetSourceLink.asset_group))
            .order_by(AssetSourceLink.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def total_download_count(self) -> int:
        value = self.db.scalar(
            select(func.coalesce(func.sum(Image.download_count), 0)).where(
                Image.deleted_at.is_(None)
            )
        )
        return int(value or 0)
