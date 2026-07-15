from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import ConceptSystemLink
from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_with_counts(self):
        tags = list(
            self.db.scalars(
                select(Tag)
                .where(Tag.node_type == "system", Tag.status == "active")
                .order_by(Tag.sort_order, Tag.name)
            ).all()
        )
        system_rows = self.db.execute(
            select(
                ConceptSystemLink.system_tag_id,
                func.count(func.distinct(AssetConceptLink.asset_group_id)),
            )
            .join(
                AssetConceptLink,
                AssetConceptLink.concept_id == ConceptSystemLink.concept_id,
            )
            .join(AssetGroup, AssetGroup.id == AssetConceptLink.asset_group_id)
            .where(
                AssetGroup.publish_status == "published",
                AssetConceptLink.review_status != "rejected",
                AssetConceptLink.relation_role != "excludes",
                ConceptSystemLink.status == "active",
            )
            .group_by(ConceptSystemLink.system_tag_id)
        ).all()
        system_counts = {tag_id: int(count) for tag_id, count in system_rows}

        return [
            (
                tag,
                None,
                system_counts.get(tag.id, 0),
            )
            for tag in tags
        ]

    def get(self, tag_id: str) -> Optional[Tag]:
        return self.db.scalar(
            select(Tag).where(Tag.id == tag_id, Tag.node_type == "system")
        )

    def get_by_code(self, code: str) -> Optional[Tag]:
        return self.db.scalar(
            select(Tag).where(Tag.code == code, Tag.node_type == "system")
        )

    def get_many(self, tag_ids: list[str]) -> list[Tag]:
        if not tag_ids:
            return []
        tags_by_id = {
            tag.id: tag
            for tag in self.db.scalars(
                select(Tag).where(Tag.id.in_(tag_ids), Tag.node_type == "system")
            ).all()
        }
        return [tags_by_id[tag_id] for tag_id in tag_ids if tag_id in tags_by_id]
