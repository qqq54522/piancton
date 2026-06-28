from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import AppError, NotFoundError
from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.repositories.tag_repository import TagRepository
from app.schemas.image import ImageRead
from app.services.search_index_sync import SearchIndexSync
from app.services.serializers import image_to_read
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork


class ImageLifecycleService:
    def __init__(
        self,
        db,
        storage: StorageProvider,
        search_index: SearchIndexSync | None = None,
    ):
        self.images = ImageRepository(db)
        self.tags = TagRepository(db)
        self.storage = storage
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()

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
        self._ensure_assignable_tags(remaining_tag_ids)
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

    def _ensure_assignable_tags(self, tag_ids: list[str]) -> None:
        unique_ids = list(dict.fromkeys(tag_ids))
        if not unique_ids:
            raise AppError("image_tag_required", "图片必须至少选择一个可打标标签")
        non_assignable_ids = self.tags.non_assignable_ids(unique_ids)
        if non_assignable_ids:
            raise AppError(
                "tag_not_assignable",
                "图片只能选择已启用且允许打标的标签",
                details=non_assignable_ids,
            )

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
