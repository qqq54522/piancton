from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import NotFoundError
from app.models.image import Image
from app.repositories.image_repository import ImageRepository
from app.schemas.image import ImageRead
from app.services.asset_identity_service import AssetIdentityService
from app.services.search_index_sync import SearchIndexSync
from app.services.serializers import image_to_read
from app.services.storage_service import StorageProvider
from app.services.unit_of_work import UnitOfWork
from app.services.vikingdb_vector_index import VikingDBVectorIndexSync


class ImageLifecycleService:
    def __init__(
        self,
        db,
        storage: StorageProvider,
        search_index: SearchIndexSync | None = None,
        vector_index: VikingDBVectorIndexSync | None = None,
    ):
        self.images = ImageRepository(db)
        self.storage = storage
        self.uow = UnitOfWork(db)
        self.search_index = search_index or SearchIndexSync.from_settings()
        self.vector_index = vector_index or VikingDBVectorIndexSync.disabled()
        self.identities = AssetIdentityService(db)

    def delete(self, image_id: str) -> None:
        image = self._get(image_id)
        image.deleted_at = datetime.now(timezone.utc)
        self.images.save(image)
        self.uow.commit()
        self.search_index.delete_image(image_id)
        self.vector_index.best_effort_upsert_image(image)

    def list_deleted(self) -> list[ImageRead]:
        return [image_to_read(image) for image in self.images.list_deleted()]

    def restore(self, image_id: str) -> ImageRead:
        image = self._get_deleted(image_id)
        image.deleted_at = None
        self.images.save(image)
        self.uow.commit()
        self._sync_index(image.id)
        return image_to_read(image)

    def purge(self, image_id: str) -> None:
        image = self._get_deleted(image_id)
        self.identities.retire_image(image.id)
        self.images.delete(image)
        self.uow.commit()
        self.search_index.delete_image(image_id)
        self.vector_index.best_effort_upsert_image(image)
        self.storage.delete_key(image.storage_key)
        if image.thumbnail_storage_key:
            self.storage.delete_key(image.thumbnail_storage_key, thumbnail=True)

    def _sync_index(self, image_id: str) -> None:
        image = self.images.get(image_id)
        if image:
            self.search_index.upsert_image(image)
            self.vector_index.best_effort_upsert_image(image)

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
