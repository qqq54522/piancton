from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.errors import AppError, NotFoundError
from app.models.image import Image, ImageCategory, ImageTag
from app.repositories.image_repository import ImageRepository
from app.schemas.image import ImageDetailRead, ImageListResponse, ImageRead
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_tagging_service import ImageTaggingService
from app.services.related_image_service import RelatedImageService
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
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.thumbnail_max_size = thumbnail_max_size
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.embedding_index = embedding_index or EmbeddingIndexSync.disabled()
        self.tagging = ImageTaggingService(
            db,
            search_index=self.search_index,
            embedding_index=self.embedding_index,
        )
        self.related_images = RelatedImageService(self.images)

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
        return image_to_detail(image, self.related_images.related_images(image, 8))

    def upload(
        self,
        stream: BinaryIO,
        original_name: str,
        title: str,
        tag_ids: list[str],
        primary_tag_id: str | None,
        categories: list[str],
        uploader: str,
        expected_search_words: list[str] | None = None,
    ) -> ImageRead:
        tags = self.tagging.validate_tags(tag_ids)
        manual_business_labels = self.tagging.manual_business_labels(tags, primary_tag_id)
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
            content_tags=self.tagging.expected_search_word_tags(expected_search_words or []),
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

    def content(self, image_id: str) -> tuple[Path, Image]:
        image = self._get(image_id)
        return self.storage.path_for(image.storage_key), image

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

    def _sync_index(self, image_id: str) -> None:
        image = self.images.get(image_id)
        if image:
            self.search_index.upsert_image(image)

    def _get(self, image_id: str) -> Image:
        image = self.images.get(image_id)
        if not image:
            raise NotFoundError("image_not_found", "图片不存在")
        return image
