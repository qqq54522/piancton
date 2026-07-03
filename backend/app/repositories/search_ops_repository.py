from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.image import Image, ImageBusinessLabel, ImageTag
from app.models.tag import Tag


class SearchOpsRepository:
    """Read-only aggregate queries backing the search operations dashboard.

    Keeps the search-ops SQLAlchemy access out of the service layer so the
    analytics service only orchestrates aggregation over plain ORM rows.
    """

    def __init__(self, db: Session):
        self.db = db

    def pending_ai_labels(self, *, limit: int = 50) -> list[ImageBusinessLabel]:
        stmt = (
            select(ImageBusinessLabel)
            .join(Image, Image.id == ImageBusinessLabel.image_id)
            .where(
                Image.deleted_at.is_(None),
                ImageBusinessLabel.origin == "ai",
                ImageBusinessLabel.review_status == "pending",
            )
            .options(
                selectinload(ImageBusinessLabel.image),
                selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent),
            )
            .order_by(
                ImageBusinessLabel.confidence.desc().nullslast(),
                ImageBusinessLabel.created_at.desc(),
            )
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def assignable_tags(self) -> list[Tag]:
        stmt = (
            select(Tag)
            .where(Tag.assignable.is_(True), Tag.status == "active")
            .options(selectinload(Tag.parent))
            .order_by(Tag.sort_order.asc(), Tag.name.asc())
        )
        return list(self.db.scalars(stmt).all())

    def image_counts_by_tag(self) -> dict[str, int]:
        rows = self.db.execute(
            select(ImageTag.tag_id, func.count(func.distinct(ImageTag.image_id)))
            .join(Image, Image.id == ImageTag.image_id)
            .where(Image.deleted_at.is_(None))
            .group_by(ImageTag.tag_id)
        ).all()
        return {tag_id: int(count) for tag_id, count in rows}

    def active_business_labels(self) -> list[ImageBusinessLabel]:
        stmt = (
            select(ImageBusinessLabel)
            .join(Image, Image.id == ImageBusinessLabel.image_id)
            .where(Image.deleted_at.is_(None))
            .options(selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent))
        )
        return list(self.db.scalars(stmt).all())
