from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from app.core.errors import AppError, NotFoundError
from app.models.asset import AssetGroup
from app.models.image import Image
from app.repositories.asset_repository import AssetRepository
from app.repositories.image_repository import ImageRepository
from app.schemas.asset import AssetGroupRead
from app.services.asset_serializers import asset_group_to_read
from app.services.search_index_sync import SearchIndexSync
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork

ASSET_ROLES = {"derivative", "alternative", "revision"}


class AssetService:
    """Owns asset-group composition and delayed image variants."""

    def __init__(
        self,
        db,
        storage: StorageProvider,
        max_upload_bytes: int,
        max_image_pixels: int,
        thumbnail_max_size: int,
        search_index: SearchIndexSync | None = None,
    ):
        self.assets = AssetRepository(db)
        self.images = ImageRepository(db)
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.max_image_pixels = max_image_pixels
        self.thumbnail_max_size = thumbnail_max_size
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.uow = UnitOfWork(db)

    def list(self) -> list[AssetGroupRead]:
        return [asset_group_to_read(item) for item in self.assets.list()]

    def get(self, group_id: str) -> AssetGroupRead:
        return asset_group_to_read(self._get(group_id))

    def add_variant(
        self,
        group_id: str,
        stream: BinaryIO,
        original_name: str,
        title: str,
        role: str,
        channel: str | None,
        uploader: str,
    ) -> AssetGroupRead:
        group = self._get(group_id)
        if role not in ASSET_ROLES:
            raise AppError("invalid_asset_role", "追加素材只能是延展图、备选图或修订版")
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        version_no = max((image.version_no for image in group.images), default=0) + 1
        image = Image(
            title=title.strip() or Path(original_name).stem,
            file_name=original_name,
            storage_key=staged.storage_key,
            thumbnail_storage_key=staged.thumbnail_storage_key,
            media_type=staged.media_type,
            size_bytes=staged.size_bytes,
            uploader=uploader,
            asset_group=group,
            asset_role=role,
            width=staged.width,
            height=staged.height,
            aspect_ratio=staged.width / staged.height,
            channel=(channel or "").strip() or None,
            version_no=version_no,
            is_current=True,
        )
        try:
            self.images.add(image)
            self.storage.finalize(staged)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            self.storage.discard(staged)
            raise
        self.search_index.upsert_image(image)
        # Group-level relations and accepted phrases are inherited by reference.
        return asset_group_to_read(self._get(group_id))

    def replace_primary(
        self,
        group_id: str,
        stream: BinaryIO,
        original_name: str,
        title: str,
        channel: str | None,
        uploader: str,
    ) -> AssetGroupRead:
        group = self._get(group_id)
        staged = self.storage.stage(
            stream,
            self.max_upload_bytes,
            self.max_image_pixels,
            self.thumbnail_max_size,
        )
        version_no = max((image.version_no for image in group.images), default=0) + 1
        previous_primary = next(
            (image for image in group.images if image.id == group.primary_image_id),
            None,
        )
        if previous_primary:
            previous_primary.asset_role = "revision"
            previous_primary.is_current = False
        image = Image(
            title=title.strip() or Path(original_name).stem,
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
            version_no=version_no,
            is_current=True,
        )
        try:
            self.images.add(image)
            group.primary_image_id = image.id
            group.title = image.title
            self.assets.save(group)
            self.storage.finalize(staged)
            self.uow.commit()
        except Exception:
            self.uow.rollback()
            self.storage.discard(staged)
            raise
        if previous_primary:
            self.search_index.delete_image(previous_primary.id)
        self.search_index.upsert_image(image)
        return asset_group_to_read(self._get(group_id))

    def _get(self, group_id: str) -> AssetGroup:
        group = self.assets.get(group_id)
        if not group:
            raise NotFoundError("asset_group_not_found", "素材组不存在")
        return group
