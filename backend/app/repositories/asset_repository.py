from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import AssetConceptLink, AssetGroup, AssetSearchPhrase, AssetSourceLink
from app.models.image import Image

ASSET_LOAD_OPTIONS = (
    selectinload(AssetGroup.images),
    selectinload(AssetGroup.concept_links).selectinload(AssetConceptLink.concept),
    selectinload(AssetGroup.search_phrases),
    selectinload(AssetGroup.source_links),
)


class AssetRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, asset_group_id: str) -> AssetGroup | None:
        return self.db.scalar(
            select(AssetGroup)
            .where(AssetGroup.id == asset_group_id)
            .options(*ASSET_LOAD_OPTIONS)
        )

    def get_for_image(self, image: Image) -> AssetGroup | None:
        if image.asset_group_id:
            return self.get(image.asset_group_id)
        return None

    def list(self) -> list[AssetGroup]:
        return list(
            self.db.scalars(
                select(AssetGroup)
                .options(*ASSET_LOAD_OPTIONS)
                .order_by(AssetGroup.updated_at.desc(), AssetGroup.id.desc())
            ).all()
        )

    def get_concept_link(self, group_id: str, link_id: str) -> AssetConceptLink | None:
        return self.db.scalar(
            select(AssetConceptLink)
            .where(AssetConceptLink.id == link_id, AssetConceptLink.asset_group_id == group_id)
            .options(selectinload(AssetConceptLink.concept))
        )

    def get_source_link(self, group_id: str, link_id: str) -> AssetSourceLink | None:
        return self.db.scalar(
            select(AssetSourceLink).where(
                AssetSourceLink.id == link_id,
                AssetSourceLink.asset_group_id == group_id,
            )
        )

    def add(self, value):
        self.db.add(value)
        self.db.flush()
        return value

    def save(self, value) -> None:
        self.db.add(value)
        self.db.flush()

    def delete(self, value) -> None:
        self.db.delete(value)
        self.db.flush()

    def replace_pending_ai_links(
        self, group: AssetGroup, links: list[AssetConceptLink]
    ) -> None:
        removed = [
            item
            for item in group.concept_links
            if item.origin == "ai" and item.review_status == "pending"
        ]
        group.concept_links[:] = [item for item in group.concept_links if item not in removed]
        for item in removed:
            self.db.delete(item)
        self.db.flush()
        protected = {
            (item.concept_id, item.relation_role)
            for item in group.concept_links
            if item.origin in {"manual", "ai"}
            and item.review_status in {"accepted", "rejected"}
        }
        group.concept_links.extend(
            item for item in links if (item.concept_id, item.relation_role) not in protected
        )
        self.db.flush()

    def replace_pending_ai_phrases(
        self, group: AssetGroup, phrases: list[AssetSearchPhrase]
    ) -> None:
        removed = [
            item
            for item in group.search_phrases
            if item.origin == "ai" and item.review_status == "pending"
        ]
        group.search_phrases[:] = [item for item in group.search_phrases if item not in removed]
        for item in removed:
            self.db.delete(item)
        self.db.flush()
        protected = {
            item.phrase
            for item in group.search_phrases
            if item.review_status in {"accepted", "rejected"}
        }
        group.search_phrases.extend(item for item in phrases if item.phrase not in protected)
        self.db.flush()
