from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.image import Image, ImageTag
from app.models.tag import Tag


class TagRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_with_counts(self):
        tags = list(
            self.db.scalars(
                select(Tag).options(selectinload(Tag.parent)).order_by(Tag.name)
            ).all()
        )
        children_by_parent: dict[Optional[str], list[str]] = {}
        for tag in tags:
            children_by_parent.setdefault(tag.parent_id, []).append(tag.id)

        image_rows = self.db.execute(
            select(ImageTag.tag_id, ImageTag.image_id)
            .join(Image, Image.id == ImageTag.image_id)
            .where(Image.deleted_at.is_(None))
        ).all()
        direct_images: dict[str, set[str]] = {}
        for tag_id, image_id in image_rows:
            direct_images.setdefault(tag_id, set()).add(image_id)

        def collect_images(tag_id: str) -> set[str]:
            image_ids = set(direct_images.get(tag_id, set()))
            for child_id in children_by_parent.get(tag_id, []):
                image_ids.update(collect_images(child_id))
            return image_ids

        return [
            (tag, tag.parent.name if tag.parent else None, len(collect_images(tag.id)))
            for tag in tags
        ]

    def get(self, tag_id: str) -> Optional[Tag]:
        return self.db.scalar(
            select(Tag)
            .where(Tag.id == tag_id)
            .options(selectinload(Tag.parent), selectinload(Tag.children))
        )

    def get_by_code(self, code: str) -> Optional[Tag]:
        return self.db.scalar(
            select(Tag)
            .where(Tag.code == code)
            .options(selectinload(Tag.parent), selectinload(Tag.children))
        )

    def get_many(self, tag_ids: list[str]) -> list[Tag]:
        if not tag_ids:
            return []
        tags_by_id = {
            tag.id: tag for tag in self.db.scalars(select(Tag).where(Tag.id.in_(tag_ids))).all()
        }
        return [tags_by_id[tag_id] for tag_id in tag_ids if tag_id in tags_by_id]

    def non_leaf_ids(self, tag_ids: list[str]) -> list[str]:
        if not tag_ids:
            return []
        parent_ids = self.db.scalars(
                select(Tag.parent_id)
                .where(Tag.parent_id.in_(tag_ids))
                .distinct()
            ).all()
        return [parent_id for parent_id in parent_ids if parent_id is not None]

    def non_assignable_ids(self, tag_ids: list[str]) -> list[str]:
        if not tag_ids:
            return []
        return list(
            self.db.scalars(
                select(Tag.id).where(
                    Tag.id.in_(tag_ids),
                    (Tag.assignable.is_(False)) | (Tag.status != "active"),
                )
            ).all()
        )

    def descendant_ids(self, tag_id: str) -> list[str]:
        rows = list(self.db.execute(select(Tag.id, Tag.parent_id)).all())
        children_by_parent: dict[Optional[str], list[str]] = {}
        for row_id, parent_id in rows:
            children_by_parent.setdefault(parent_id, []).append(row_id)

        ordered: list[str] = []
        stack = [tag_id]
        while stack:
            current = stack.pop()
            ordered.append(current)
            stack.extend(children_by_parent.get(current, []))
        return ordered

    def image_ids_for_tags(self, tag_ids: list[str]) -> list[str]:
        if not tag_ids:
            return []
        return list(
            self.db.scalars(
                select(ImageTag.image_id)
                .join(Image, Image.id == ImageTag.image_id)
                .where(ImageTag.tag_id.in_(tag_ids), Image.deleted_at.is_(None))
                .distinct()
            ).all()
        )

    def add(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.flush()
        return tag

    def save(self, tag: Tag) -> Tag:
        self.db.add(tag)
        self.db.flush()
        return tag

    def delete(self, tag: Tag) -> None:
        self.db.delete(tag)
        self.db.flush()
