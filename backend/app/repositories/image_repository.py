from __future__ import annotations

from datetime import datetime
from typing import Optional, cast

from sqlalchemy import and_, desc, func, literal, or_, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.domain.search_query_expansion import expand_search_terms
from app.models.image import (
    AnalysisRun,
    ContentTag,
    Image,
    ImageBusinessLabel,
    ImageCategory,
    ImageLevel2Category,
    ImageTag,
)
from app.models.tag import Tag

IMAGE_LOAD_OPTIONS = (
    selectinload(Image.tag_links).selectinload(ImageTag.tag).selectinload(Tag.parent),
    selectinload(Image.categories),
    selectinload(Image.content_tags),
    selectinload(Image.level2_categories),
    selectinload(Image.business_labels).selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent),
    selectinload(Image.analysis_runs),
)


class ImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, image_id: str) -> Optional[Image]:
        stmt = (
            select(Image)
            .where(Image.id == image_id, Image.deleted_at.is_(None))
            .options(*IMAGE_LOAD_OPTIONS)
        )
        return self.db.scalar(stmt)

    def get_any(self, image_id: str) -> Optional[Image]:
        return self.db.scalar(
            select(Image).where(Image.id == image_id).options(*IMAGE_LOAD_OPTIONS)
        )

    def list(
        self,
        keyword: Optional[str],
        tag_ids: list[str],
        category: Optional[str],
        cursor_value: str | int | datetime | None,
        cursor_id: str | None,
        limit: int,
        sort_by: str,
    ) -> list[Image]:
        stmt = select(Image).where(Image.deleted_at.is_(None)).options(*IMAGE_LOAD_OPTIONS)
        if keyword:
            keyword_terms = expand_search_terms(keyword)[:30]
            patterns = [f"%{term}%" for term in keyword_terms if term.strip()]
            manual_tag = aliased(Tag)
            business_tag = aliased(Tag)
            keyword_conditions = []
            for pattern in patterns:
                keyword_conditions.extend(
                    [
                        Image.title.ilike(pattern),
                        literal(keyword).ilike(literal("%") + Image.title + literal("%")),
                        Image.image_summary.ilike(pattern),
                        manual_tag.name.ilike(pattern),
                        ContentTag.tag_name.ilike(pattern),
                        ImageLevel2Category.category_name.ilike(pattern),
                        ImageBusinessLabel.label_code.ilike(pattern),
                        ImageBusinessLabel.reason.ilike(pattern),
                        business_tag.name.ilike(pattern),
                    ]
                )
            stmt = (
                stmt.outerjoin(ContentTag, ContentTag.image_id == Image.id)
                .outerjoin(ImageLevel2Category, ImageLevel2Category.image_id == Image.id)
                .outerjoin(ImageTag, ImageTag.image_id == Image.id)
                .outerjoin(manual_tag, ImageTag.tag_id == manual_tag.id)
                .outerjoin(
                    ImageBusinessLabel,
                    and_(
                        ImageBusinessLabel.image_id == Image.id,
                        ImageBusinessLabel.review_status != "rejected",
                    ),
                )
                .outerjoin(business_tag, ImageBusinessLabel.tag_id == business_tag.id)
                .where(or_(*keyword_conditions))
            )
        if tag_ids:
            matching_images = (
                select(ImageTag.image_id)
                .where(ImageTag.tag_id.in_(tag_ids))
                .group_by(ImageTag.image_id)
                .having(func.count(func.distinct(ImageTag.tag_id)) == len(set(tag_ids)))
            )
            stmt = stmt.where(Image.id.in_(matching_images))
        if category:
            stmt = stmt.join(ImageCategory).where(ImageCategory.name == category)

        if cursor_value is not None and cursor_id:
            if sort_by == "downloadCount":
                value = int(cast("str | int", cursor_value))
                stmt = stmt.where(
                    or_(
                        Image.download_count < value,
                        and_(Image.download_count == value, Image.id < cursor_id),
                    )
                )
            else:
                value = cast(datetime, cursor_value)
                stmt = stmt.where(
                    or_(
                        Image.created_at < value,
                        and_(Image.created_at == value, Image.id < cursor_id),
                    )
                )

        if sort_by == "downloadCount":
            order = (desc(Image.download_count), desc(Image.id))
        else:
            order = (desc(Image.created_at), desc(Image.id))
        return list(self.db.scalars(stmt.distinct().order_by(*order).limit(limit + 1)).all())

    def search(self, keyword: str, limit: int) -> list[Image]:
        pattern = f"%{keyword}%"
        business_tag = aliased(Tag)
        stmt = (
            select(Image)
            .outerjoin(ImageTag)
            .outerjoin(Tag)
            .outerjoin(ContentTag)
            .outerjoin(ImageLevel2Category)
            .outerjoin(
                ImageBusinessLabel,
                and_(
                    ImageBusinessLabel.image_id == Image.id,
                    ImageBusinessLabel.review_status != "rejected",
                ),
            )
            .outerjoin(business_tag, ImageBusinessLabel.tag_id == business_tag.id)
            .where(
                Image.deleted_at.is_(None),
                or_(
                    Image.title.ilike(pattern),
                    literal(keyword).ilike(literal("%") + Image.title + literal("%")),
                    Image.image_summary.ilike(pattern),
                    Tag.name.ilike(pattern),
                    ContentTag.tag_name.ilike(pattern),
                    ImageLevel2Category.category_name.ilike(pattern),
                    ImageBusinessLabel.label_code.ilike(pattern),
                    business_tag.name.ilike(pattern),
                )
            )
            .options(*IMAGE_LOAD_OPTIONS)
            .distinct()
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_many_by_ids(self, image_ids: list[str]) -> list[Image]:
        if not image_ids:
            return []
        stmt = (
            select(Image)
            .where(Image.id.in_(image_ids), Image.deleted_at.is_(None))
            .options(*IMAGE_LOAD_OPTIONS)
        )
        images_by_id = {image.id: image for image in self.db.scalars(stmt).all()}
        return [images_by_id[image_id] for image_id in image_ids if image_id in images_by_id]

    def get_business_label(self, image_id: str, label_id: str) -> Optional[ImageBusinessLabel]:
        return self.db.scalar(
            select(ImageBusinessLabel)
            .where(
                ImageBusinessLabel.id == label_id,
                ImageBusinessLabel.image_id == image_id,
            )
            .options(selectinload(ImageBusinessLabel.tag).selectinload(Tag.parent))
        )

    def get_analysis_run(self, image_id: str, run_id: str) -> Optional[AnalysisRun]:
        return self.db.scalar(
            select(AnalysisRun).where(
                AnalysisRun.id == run_id,
                AnalysisRun.image_id == image_id,
            )
        )

    def list_for_search_index(self, *, offset: int, limit: int) -> list[Image]:
        stmt = (
            select(Image)
            .where(Image.deleted_at.is_(None))
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(Image.created_at.asc(), Image.id.asc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_deleted(self, limit: int = 100) -> list[Image]:
        stmt = (
            select(Image)
            .where(Image.deleted_at.is_not(None))
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(desc(Image.deleted_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def add(self, image: Image) -> Image:
        self.db.add(image)
        self.db.flush()
        return image

    def save(self, image: Image) -> Image:
        self.db.add(image)
        self.db.flush()
        return image

    def soft_delete_many(self, image_ids: list[str], deleted_at: datetime) -> int:
        if not image_ids:
            return 0
        rows = list(
            self.db.scalars(
                select(Image).where(
                    Image.id.in_(image_ids),
                    Image.deleted_at.is_(None),
                )
            ).all()
        )
        for image in rows:
            image.deleted_at = deleted_at
            self.db.add(image)
        self.db.flush()
        return len(rows)

    def replace_tags(self, image: Image, tags: list[Tag]) -> Image:
        image.tag_links.clear()
        image.tag_links.extend(ImageTag(tag=tag) for tag in tags)
        self.db.flush()
        return image

    def remove_tag_links(self, image: Image, tag_ids: list[str]) -> Image:
        if not tag_ids:
            return image
        blocked = set(tag_ids)
        image.tag_links[:] = [
            link for link in image.tag_links if link.tag_id not in blocked
        ]
        self.db.flush()
        return image

    def replace_ai_profile(
        self,
        image: Image,
        *,
        summary: str,
        content_tags: list[ContentTag],
        level2_categories: list[ImageLevel2Category],
        analysis_run: AnalysisRun | None = None,
        business_labels: list[ImageBusinessLabel] | None = None,
    ) -> Image:
        image.image_summary = summary
        image.content_tags.clear()
        image.content_tags.extend(content_tags)
        image.level2_categories.clear()
        image.level2_categories.extend(level2_categories)
        image.business_labels[:] = [
            label
            for label in image.business_labels
            if label.origin != "ai" or label.review_status in {"accepted", "rejected"}
        ]
        if analysis_run is not None and all(
            existing.id != analysis_run.id for existing in image.analysis_runs
        ):
            image.analysis_runs.append(analysis_run)
        if business_labels:
            image.business_labels.extend(business_labels)
        self.db.flush()
        return image

    def delete(self, image: Image) -> None:
        self.db.delete(image)
        self.db.flush()
