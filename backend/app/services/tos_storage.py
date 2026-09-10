"""TOS files use a namespaced key; legacy keys remain in local storage."""

from __future__ import annotations

import logging
import tempfile
from dataclasses import replace
from pathlib import Path

from app.core.errors import AppError, NotFoundError
from app.services.storage_service import (
    LocalStorageProvider,
    StagedUpload,
    _create_preview_thumbnail,
)

logger = logging.getLogger(__name__)
REMOTE_PREFIX = "tos-"


class TosStorageProvider(LocalStorageProvider):
    def __init__(self, root: Path, client, bucket: str, prefix: str):
        super().__init__(root)
        self.client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if not self.prefix or any(p in {"", ".", ".."} for p in self.prefix.split("/")):
            raise AppError("storage_config_invalid", "对象存储路径前缀无效", status_code=503)
        self.downloads = self.root / ".tos-downloads"
        self.downloads.mkdir(exist_ok=True)

    def object_key(self, key: str, *, thumbnail: bool = False) -> str:
        # Validate even remote keys using the same strict local filename boundary.
        self._safe_path(key)
        if not key.startswith(REMOTE_PREFIX) or key == REMOTE_PREFIX:
            raise AppError("invalid_storage_key", "非法对象存储标识")
        folder = "thumbnails" if thumbnail else "originals"
        return f"{self.prefix}/{folder}/{key}"

    def stage(
        self,
        stream,
        max_bytes,
        max_pixels,
        max_long_image_pixels,
        long_image_min_aspect_ratio,
        thumbnail_max_size,
    ) -> StagedUpload:
        upload = super().stage(
            stream,
            max_bytes,
            max_pixels,
            max_long_image_pixels,
            long_image_min_aspect_ratio,
            thumbnail_max_size,
        )
        return replace(
            upload,
            storage_key=REMOTE_PREFIX + upload.storage_key,
            thumbnail_storage_key=REMOTE_PREFIX + upload.thumbnail_storage_key,
        )

    def upload_file(
        self, key: str, path: Path, media_type: str, *, thumbnail: bool = False
    ) -> None:
        from tos.enum import ACLType

        object_key = self.object_key(key, thumbnail=thumbnail)
        try:
            self.client.put_object_from_file(
                self.bucket,
                object_key,
                str(path),
                content_type=media_type,
                acl=ACLType.ACL_Private,
            )
        except Exception:
            raise AppError(
                "object_storage_unavailable", "图片存储服务暂不可用，请稍后重试", status_code=503
            ) from None

    def finalize(self, upload: StagedUpload) -> None:
        self.upload_file(upload.storage_key, upload.temp_path, upload.media_type)
        self.upload_file(
            upload.thumbnail_storage_key, upload.thumbnail_temp_path, "image/jpeg", thumbnail=True
        )
        upload.temp_path.unlink(missing_ok=True)
        upload.thumbnail_temp_path.unlink(missing_ok=True)

    def discard(self, upload: StagedUpload) -> None:
        # Rollback cleanup must attempt both objects, including uncertain PUT outcomes.
        for key, thumbnail in ((upload.storage_key, False), (upload.thumbnail_storage_key, True)):
            try:
                self.delete_key(key, thumbnail=thumbnail)
            except AppError:
                logger.error("tos_upload_cleanup_failed key=%s thumbnail=%s", key, thumbnail)
        upload.temp_path.unlink(missing_ok=True)
        upload.thumbnail_temp_path.unlink(missing_ok=True)

    def _fetch(self, key: str, *, thumbnail: bool = False) -> Path:
        object_key = self.object_key(key, thumbnail=thumbnail)
        with tempfile.NamedTemporaryFile(dir=self.downloads, delete=False) as output:
            path = Path(output.name)
        try:
            self.client.get_object_to_file(self.bucket, object_key, str(path))
            return path
        except Exception as exc:
            path.unlink(missing_ok=True)
            if getattr(exc, "status_code", None) == 404:
                raise NotFoundError("image_content_missing", "图片文件不存在") from None
            raise AppError(
                "object_storage_unavailable", "图片存储服务暂不可用，请稍后重试", status_code=503
            ) from None

    def path_for(self, storage_key: str) -> Path:
        if storage_key.startswith(REMOTE_PREFIX):
            return self._fetch(storage_key)
        return super().path_for(storage_key)

    def thumbnail_path_for(self, storage_key: str) -> Path:
        if storage_key.startswith(REMOTE_PREFIX):
            return self._fetch(storage_key, thumbnail=True)
        return super().thumbnail_path_for(storage_key)

    def regenerate_thumbnail(
        self,
        storage_key: str,
        thumbnail_storage_key: str,
        thumbnail_max_size: int,
    ) -> Path:
        if not storage_key.startswith(REMOTE_PREFIX):
            return super().regenerate_thumbnail(
                storage_key,
                thumbnail_storage_key,
                thumbnail_max_size,
            )

        source = self.path_for(storage_key)
        with tempfile.NamedTemporaryFile(dir=self.downloads, delete=False) as output:
            refreshed = Path(output.name)
        try:
            _create_preview_thumbnail(source, refreshed, thumbnail_max_size)
            self.upload_file(
                thumbnail_storage_key,
                refreshed,
                "image/jpeg",
                thumbnail=True,
            )
            return refreshed
        except Exception:
            refreshed.unlink(missing_ok=True)
            raise
        finally:
            self.release(source)

    def release(self, path: Path) -> None:
        if path.resolve().parent == self.downloads.resolve():
            path.unlink(missing_ok=True)

    def delete_key(self, storage_key: str, *, thumbnail: bool = False) -> None:
        if not storage_key.startswith(REMOTE_PREFIX):
            return super().delete_key(storage_key, thumbnail=thumbnail)
        object_key = self.object_key(storage_key, thumbnail=thumbnail)
        try:
            self.client.delete_object(self.bucket, object_key)
        except Exception as exc:
            if getattr(exc, "status_code", None) != 404:
                raise AppError(
                    "object_storage_unavailable", "图片删除未完成，请稍后重试", status_code=503
                ) from None
