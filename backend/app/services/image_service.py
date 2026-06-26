from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.errors import AppError, NotFoundError
from app.models.image import (
    Image,
    ImageBusinessLabel,
    ImageCategory,
    ImageTag,
)
from app.repositories.image_repository import ImageRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.image import ImageDetailRead, ImageListResponse, ImageRead
from app.services.embedding_index import EmbeddingIndexSync
from app.services.search_index_sync import SearchIndexSync
from app.services.serializers import image_to_detail, image_to_read
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork


def encode_cursor(sort_by: str, value: str | int, image_id: str) -> str:
    payload = json.dumps({"sort": sort_by, "value": value, "id": image_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(cursor: str, sort_by: str) -> tuple[str | int | datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        payload = json.loads(raw)
        if payload["sort"] != sort_by or not payload["id"]:
            raise ValueError
        value = payload["value"]
        if sort_by == "createdAt":
            value = datetime.fromisoformat(value)
        else:
            value = int(value)
        return value, str(payload["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise AppError("invalid_cursor", "分页游标无效") from exc


class ImageService:
    def __init__(
        self,
        db,
        storage: StorageProvider,
        max_upload_bytes: int,
        max_image_pixels: int,
        thumbnail_max_size: int,
        search_index: SearchIndexSync | None = None,
        embedding_index: EmbeddingIndexSync | None = None,
    ):
        self.images = ImageRepository(db)
        self.tags = TagRepository(db)
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.thumbnail_max_size = thumbnail_max_size
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.embedding_index = embedding_index or EmbeddingIndexSync.disabled()

    def list_images(
        self,
        keyword: Optional[str],
        tag_ids: list[str],
        cursor: Optional[str],
        limit: int,
        sort_by: str,
        category: Optional[str],
    ) -> ImageListResponse:
        cursor_value = cursor_id = None
        if cursor:
            cursor_value, cursor_id = decode_cursor(cursor, sort_by)
        rows = self.images.list(
            keyword, tag_ids, category, cursor_value, cursor_id, limit, sort_by
        )
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            value = (
                last.download_count
                if sort_by == "downloadCount"
                else last.created_at.isoformat()
            )
            next_cursor = encode_cursor(sort_by, value, last.id)
        return ImageListResponse(
            items=[image_to_read(item) for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_detail(self, image_id: str) -> ImageDetailRead:
        image = self._get(image_id)
        tag_ids = [link.tag_id for link in image.tag_links]
        related = self.images.list(None, tag_ids, None, None, None, 9, "createdAt")
        return image_to_detail(image, [item for item in related if item.id != image.id][:8])

    def upload(
        self,
        stream: BinaryIO,
        original_name: str,
        title: str,
        tag_ids: list[str],
        primary_tag_id: str | None,
        categories: list[str],
        uploader: str,
    ) -> ImageRead:
        tags = self._validated_tags(tag_ids)
        manual_business_labels = self._manual_business_labels(tags, primary_tag_id)
        invalid_categories = set(categories) - {"scene", "function"}
        if invalid_categories:
            raise AppError("invalid_category", "图片分类无效", details=sorted(invalid_categories))
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        image = Image(
            title=title.strip() or Path(original_name).stem,
            file_name=original_name,
            storage_key=staged.storage_key,
            thumbnail_storage_key=staged.thumbnail_storage_key,
            media_type=staged.media_type,
            size_bytes=staged.size_bytes,
            uploader=uploader,
            tag_links=[ImageTag(tag=tag) for tag in tags],
            business_labels=manual_business_labels,
            categories=[ImageCategory(name=name) for name in sorted(set(categories))],
        )
        try:
            self.images.add(image)
            self.embedding_index.upsert_image(self.images, image)
            self.storage.finalize(staged)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            self.storage.discard(staged)
            raise
        self._sync_index(image.id)
        return image_to_read(self._get(image.id))

    def update_title(self, image_id: str, title: str) -> ImageRead:
        image = self._get(image_id)
        image.title = title
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(image)

    def update_tags(
        self,
        image_id: str,
        tag_ids: list[str],
        primary_tag_id: str | None = None,
    ) -> ImageRead:
        image = self._get(image_id)
        tags = self._validated_tags(tag_ids)
        self.images.replace_tags(image, tags)
        image.business_labels[:] = [
            label for label in image.business_labels if label.origin != "manual"
        ]
        image.business_labels.extend(self._manual_business_labels(tags, primary_tag_id))
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(self._get(image.id))

    def review_business_label(
        self,
        image_id: str,
        label_id: str,
        review_status: str,
    ) -> ImageDetailRead:
        image = self._get(image_id)
        label = self.images.get_business_label(image_id, label_id)
        if not label:
            raise NotFoundError("business_label_not_found", "业务标签建议不存在")
        if label.origin != "ai":
            raise AppError("manual_label_not_reviewable", "人工业务标签不需要审核")
        label.review_status = review_status
        if review_status == "accepted":
            self._promote_ai_label_to_manual(image, label)
        elif review_status == "rejected":
            self._remove_rejected_ai_label_outputs(image, label)
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return self.get_detail(image.id)

    def delete(self, image_id: str) -> None:
        image = self._get(image_id)
        image.deleted_at = datetime.now(timezone.utc)
        self.images.save(image)
        self.uow.commit()
        self.search_index.delete_image(image_id)

    def list_deleted(self) -> list[ImageRead]:
        return [image_to_read(image) for image in self.images.list_deleted()]

    def restore(self, image_id: str) -> ImageRead:
        image = self._get_deleted(image_id)
        non_leaf_ids = self.tags.non_assignable_ids([link.tag_id for link in image.tag_links])
        remaining_tag_ids = [
            link.tag_id for link in image.tag_links if link.tag_id not in set(non_leaf_ids)
        ]
        self._validated_tags(remaining_tag_ids)
        self.images.remove_tag_links(image, non_leaf_ids)
        image.deleted_at = None
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(image)

    def purge(self, image_id: str) -> None:
        image = self._get_deleted(image_id)
        self.images.delete(image)
        self.uow.commit()
        self.search_index.delete_image(image_id)
        self.storage.delete_key(image.storage_key)
        if image.thumbnail_storage_key:
            self.storage.delete_key(image.thumbnail_storage_key, thumbnail=True)

    def content(self, image_id: str) -> tuple[Path, Image]:
        image = self._get(image_id)
        return self.storage.path_for(image.storage_key), image

    def _promote_ai_label_to_manual(
        self,
        image: Image,
        label: ImageBusinessLabel,
    ) -> None:
        if not any(link.tag_id == label.tag_id for link in image.tag_links):
            image.tag_links.append(ImageTag(tag=label.tag))

        if any(
            item.origin == "manual" and item.tag_id == label.tag_id
            for item in image.business_labels
        ):
            return

        has_manual_primary = any(
            item.origin == "manual" and item.role == "primary"
            for item in image.business_labels
        )
        image.business_labels.append(
            ImageBusinessLabel(
                image=image,
                tag=label.tag,
                label_code=label.label_code,
                origin="manual",
                role="additional" if has_manual_primary else "primary",
                review_status="accepted",
                confidence=1.0,
                evidence_level=label.evidence_level,
                reason=(
                    "设计师接受 AI 建议"
                    + (f"：{label.reason}" if label.reason else "")
                ),
            )
        )

    def _business_label_display_name(self, label: ImageBusinessLabel) -> str:
        if label.tag.parent:
            return f"{label.tag.parent.name} > {label.tag.name}"
        return label.tag.name

    def _remove_rejected_ai_label_outputs(
        self,
        image: Image,
        label: ImageBusinessLabel,
    ) -> None:
        rejected_name = self._business_label_display_name(label)
        image.level2_categories[:] = [
            item for item in image.level2_categories if item.category_name != rejected_name
        ]
        image.business_labels[:] = [
            item
            for item in image.business_labels
            if not (
                item.origin == "manual"
                and item.tag_id == label.tag_id
                and (item.reason or "").startswith("设计师接受 AI 建议")
            )
        ]
        if not any(
            item.origin == "manual" and item.tag_id == label.tag_id
            for item in image.business_labels
        ):
            image.tag_links[:] = [
                link for link in image.tag_links if link.tag_id != label.tag_id
            ]

    def thumbnail(self, image_id: str) -> tuple[Path, Image]:
        image = self.images.get_any(image_id)
        if not image:
            raise NotFoundError("image_not_found", "图片不存在")
        if not image.thumbnail_storage_key:
            return self.storage.path_for(image.storage_key), image
        return self.storage.thumbnail_path_for(image.thumbnail_storage_key), image

    def download(self, image_id: str) -> tuple[Path, Image]:
        image = self._get(image_id)
        path = self.storage.path_for(image.storage_key)
        return path, image

    def increment_download(self, image_id: str) -> None:
        image = self._get(image_id)
        image.download_count += 1
        self.images.save(image)
        self.uow.commit()

    def _validated_tags(self, tag_ids: list[str]):
        unique_ids = list(dict.fromkeys(tag_ids))
        if not unique_ids:
            raise AppError("image_tag_required", "图片必须至少选择一个可打标标签")
        tags = self.tags.get_many(unique_ids)
        found = {tag.id for tag in tags}
        missing = [tag_id for tag_id in unique_ids if tag_id not in found]
        if missing:
            raise AppError("unknown_tags", "存在无效标签", details=missing)
        non_assignable_ids = self.tags.non_assignable_ids(unique_ids)
        if non_assignable_ids:
            raise AppError(
                "tag_not_assignable",
                "图片只能选择已启用且允许打标的标签",
                details=non_assignable_ids,
            )
        return tags

    def _manual_business_labels(
        self,
        tags,
        primary_tag_id: str | None,
    ) -> list[ImageBusinessLabel]:
        if not tags:
            return []
        tags_by_id = {tag.id: tag for tag in tags}
        selected_primary_id = primary_tag_id or tags[0].id
        if selected_primary_id not in tags_by_id:
            raise AppError(
                "primary_tag_required",
                "主业务标签必须来自已选择的标签",
                details={"primaryTagId": selected_primary_id},
            )
        labels: list[ImageBusinessLabel] = []
        for tag in tags:
            labels.append(
                ImageBusinessLabel(
                    tag=tag,
                    label_code=tag.code or tag.id,
                    origin="manual",
                    role="primary" if tag.id == selected_primary_id else "additional",
                    review_status="accepted",
                    confidence=1.0,
                )
            )
        return labels

    def _sync_index(self, image_id: str) -> None:
        image = self.images.get(image_id)
        if image:
            self.search_index.upsert_image(image)

    def _get(self, image_id: str) -> Image:
        image = self.images.get(image_id)
        if not image:
            raise NotFoundError("image_not_found", "图片不存在")
        return image

    def _get_deleted(self, image_id: str) -> Image:
        image = self.images.get_any(image_id)
        if not image or image.deleted_at is None:
            raise NotFoundError("deleted_image_not_found", "回收站中不存在该图片")
        return image
