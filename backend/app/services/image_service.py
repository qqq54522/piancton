from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from app.core.errors import AppError, NotFoundError
from app.domain.image_titles import clean_image_title
from app.models.asset import AssetGroup
from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.schemas.image import (
    ImageDetailRead,
    ImageListResponse,
    ImageRead,
    ImageTitleResolution,
)
from app.services.asset_identity_service import AssetIdentityService
from app.services.asset_relation_service import AssetRelationService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_title_service import ImageTitleService
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
        self.asset_relations = AssetRelationService(db)
        self.identities = AssetIdentityService(db)
        self.related_images = RelatedImageService(self.images)
        self.image_titles = ImageTitleService(db)

    def list_images(
        self,
        keyword: Optional[str],
        cursor: Optional[str],
        limit: int,
        sort_by: str,
    ) -> ImageListResponse:
        cursor_value = cursor_id = None
        if cursor:
            cursor_value, cursor_id = decode_cursor(cursor, sort_by)
        rows = self.images.list(keyword, cursor_value, cursor_id, limit, sort_by)
        has_more = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_more and items:
            last = items[-1]
            value = (
                last.download_count if sort_by == "downloadCount" else last.created_at.isoformat()
            )
            next_cursor = encode_cursor(sort_by, value, last.id)
        return ImageListResponse(
            items=[image_to_read(item) for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def get_detail(self, image_id: str) -> ImageDetailRead:
        image = self._get_or_identity(image_id)
        return image_to_detail(image, self.related_images.related_images(image, 8))

    def upload(
        self,
        stream: BinaryIO,
        original_name: str,
        title: str,
        uploader: str,
        expected_search_words: list[str] | None = None,
        channel: str | None = None,
        style_label: str | None = None,
        is_scene_image: bool | None = None,
    ) -> ImageRead:
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        requested_title = title.strip() or Path(original_name).stem
        resolved_title = self.image_titles.resolve(requested_title)
        group = AssetGroup(
            asset_code=self.identities.allocate_asset_code(),
            title=resolved_title,
            approval_status="approved",
            publish_status="published",
            style_label=(style_label or "").strip() or None,
            is_scene_image=is_scene_image,
            created_by=uploader,
            search_phrases=self.asset_relations.manual_phrases(expected_search_words or []),
        )
        image = Image(
            version_code=self.identities.allocate_version_code(group.asset_code, 1),
            title=resolved_title,
            file_name=original_name,
            storage_key=staged.storage_key,
            thumbnail_storage_key=staged.thumbnail_storage_key,
            media_type=staged.media_type,
            size_bytes=staged.size_bytes,
            uploader=uploader,
            asset_group=group,
            asset_role="primary",
            width=staged.width,
            height=staged.height,
            aspect_ratio=staged.width / staged.height,
            channel=(channel or "").strip() or None,
            version_no=1,
            is_current=True,
        )
        try:
            self.images.add(image)
            group.primary_image_id = image.id
            self.identities.register_group(group)
            self.identities.register_image(image)
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
        requested_title = clean_image_title(title)
        resolved_title = (
            requested_title
            if requested_title.casefold() == image.title.casefold()
            else self.image_titles.resolve(
                requested_title,
                exclude_image_id=image.id,
            )
        )
        image.title = resolved_title
        if image.asset_group and image.asset_group.primary_image_id == image.id:
            image.asset_group.title = resolved_title
        self.embedding_index.upsert_image(self.images, image)
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(image)

    def resolve_title(self, title: str) -> ImageTitleResolution:
        requested = title.strip()
        resolved = self.image_titles.resolve(requested, reserve=False)
        return ImageTitleResolution(
            requested_title=requested,
            resolved_title=resolved,
            changed=requested != resolved,
        )

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

    def _get_or_identity(self, value: str) -> Image:
        image = self.images.get(value)
        if image:
            return image
        image = self.identities.require_image(value)
        return image
