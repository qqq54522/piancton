from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

from PIL import Image as PillowImage
from PIL import UnidentifiedImageError

from app.core.errors import AppError, NotFoundError

ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp"),
    "GIF": ("image/gif", ".gif"),
}

# The masonry/grid preview is width-constrained. Bounding every thumbnail to a
# square made portrait assets progressively narrower (for example, a 1:3 image
# became only 213 px wide with a 640 px setting) and the browser then enlarged
# it. Keep the configured width for readable long-image previews while still
# bounding pathological panoramas by height.
THUMBNAIL_MAX_HEIGHT_MULTIPLIER = 12


@dataclass(frozen=True)
class StagedUpload:
    temp_path: Path
    storage_key: str
    thumbnail_temp_path: Path
    thumbnail_storage_key: str
    media_type: str
    size_bytes: int
    width: int
    height: int


class StorageProvider(Protocol):
    def stage(
        self,
        stream: BinaryIO,
        max_bytes: int,
        max_pixels: int,
        max_long_image_pixels: int,
        long_image_min_aspect_ratio: float,
        thumbnail_max_size: int,
    ) -> StagedUpload: ...
    def finalize(self, upload: StagedUpload) -> None: ...
    def discard(self, upload: StagedUpload) -> None: ...
    def path_for(self, storage_key: str) -> Path: ...
    def thumbnail_path_for(self, storage_key: str) -> Path: ...
    def regenerate_thumbnail(
        self,
        storage_key: str,
        thumbnail_storage_key: str,
        thumbnail_max_size: int,
    ) -> Path: ...
    def quarantine(self, storage_key: str) -> Path | None: ...
    def restore(self, storage_key: str, quarantined: Path) -> None: ...
    def purge(self, quarantined: Path | None) -> None: ...
    def delete_key(self, storage_key: str, *, thumbnail: bool = False) -> None: ...
    def release(self, path: Path) -> None: ...


class LocalStorageProvider:
    def release(self, path: Path) -> None:
        """Local persistent files do not need response cleanup."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.staging = self.root / ".staging"
        self.trash = self.root / ".trash"
        self.thumbnails = self.root / ".thumbnails"
        self.staging.mkdir(parents=True, exist_ok=True)
        self.trash.mkdir(parents=True, exist_ok=True)
        self.thumbnails.mkdir(parents=True, exist_ok=True)

    def stage(
        self,
        stream: BinaryIO,
        max_bytes: int,
        max_pixels: int,
        max_long_image_pixels: int,
        long_image_min_aspect_ratio: float,
        thumbnail_max_size: int,
    ) -> StagedUpload:
        temp_path = self.staging / f"{uuid.uuid4()}.upload"
        thumbnail_temp_path = self.staging / f"{uuid.uuid4()}.thumbnail"
        size = 0
        try:
            with temp_path.open("wb") as output:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > max_bytes:
                        raise AppError(
                            "upload_too_large",
                            f"图片不能超过 {max_bytes // (1024 * 1024)}MB",
                            status_code=413,
                        )
                    output.write(chunk)
            try:
                with PillowImage.open(temp_path) as image:
                    image_format = image.format or ""
                    width, height = image.size
                    _validate_image_pixels(
                        width,
                        height,
                        max_pixels,
                        max_long_image_pixels,
                        long_image_min_aspect_ratio,
                    )
                    image.verify()
            except (UnidentifiedImageError, OSError) as exc:
                raise AppError(
                    "invalid_image",
                    "文件不是受支持的有效图片",
                    status_code=415,
                ) from exc
            if image_format not in ALLOWED_FORMATS:
                raise AppError(
                    "unsupported_image_type",
                    "仅支持 JPEG、PNG、WebP 和 GIF",
                    status_code=415,
                )
            media_type, extension = ALLOWED_FORMATS[image_format]
            _create_preview_thumbnail(temp_path, thumbnail_temp_path, thumbnail_max_size)
            return StagedUpload(
                temp_path=temp_path,
                storage_key=f"{uuid.uuid4()}{extension}",
                thumbnail_temp_path=thumbnail_temp_path,
                thumbnail_storage_key=f"{uuid.uuid4()}.jpg",
                media_type=media_type,
                size_bytes=size,
                width=width,
                height=height,
            )
        except Exception:
            temp_path.unlink(missing_ok=True)
            thumbnail_temp_path.unlink(missing_ok=True)
            raise

    def finalize(self, upload: StagedUpload) -> None:
        os.replace(upload.temp_path, self._safe_path(upload.storage_key))
        os.replace(
            upload.thumbnail_temp_path,
            self._safe_thumbnail_path(upload.thumbnail_storage_key),
        )

    def discard(self, upload: StagedUpload) -> None:
        upload.temp_path.unlink(missing_ok=True)
        upload.thumbnail_temp_path.unlink(missing_ok=True)
        self._safe_path(upload.storage_key).unlink(missing_ok=True)
        self._safe_thumbnail_path(upload.thumbnail_storage_key).unlink(missing_ok=True)

    def path_for(self, storage_key: str) -> Path:
        self._require_local_key(storage_key)
        path = self._safe_path(storage_key)
        if not path.is_file():
            raise NotFoundError("image_content_missing", "图片文件不存在")
        return path

    def _safe_path(self, storage_key: str) -> Path:
        if not storage_key or Path(storage_key).name != storage_key:
            raise AppError("invalid_storage_key", "非法存储标识")
        path = (self.root / storage_key).resolve()
        if path.parent != self.root:
            raise AppError("invalid_storage_key", "非法存储标识")
        return path

    def thumbnail_path_for(self, storage_key: str) -> Path:
        self._require_local_key(storage_key)
        path = self._safe_thumbnail_path(storage_key)
        if not path.is_file():
            raise NotFoundError("thumbnail_missing", "缩略图不存在")
        return path

    def regenerate_thumbnail(
        self,
        storage_key: str,
        thumbnail_storage_key: str,
        thumbnail_max_size: int,
    ) -> Path:
        source = self.path_for(storage_key)
        temp_path = self.staging / f"{uuid.uuid4()}.thumbnail-refresh"
        try:
            _create_preview_thumbnail(source, temp_path, thumbnail_max_size)
            target = self._safe_thumbnail_path(thumbnail_storage_key)
            os.replace(temp_path, target)
            return target
        finally:
            temp_path.unlink(missing_ok=True)
            self.release(source)

    def _safe_thumbnail_path(self, storage_key: str) -> Path:
        if not storage_key or Path(storage_key).name != storage_key:
            raise AppError("invalid_storage_key", "非法存储标识")
        path = (self.thumbnails / storage_key).resolve()
        if path.parent != self.thumbnails:
            raise AppError("invalid_storage_key", "非法存储标识")
        return path

    def quarantine(self, storage_key: str) -> Path | None:
        try:
            source = self.path_for(storage_key)
        except NotFoundError:
            return None
        target = self.trash / f"{uuid.uuid4()}-{storage_key}"
        os.replace(source, target)
        return target

    def restore(self, storage_key: str, quarantined: Path) -> None:
        if quarantined.is_file():
            os.replace(quarantined, self.root / storage_key)

    def purge(self, quarantined: Path | None) -> None:
        if quarantined and quarantined.is_file():
            quarantined.unlink()

    def delete_key(self, storage_key: str, *, thumbnail: bool = False) -> None:
        self._require_local_key(storage_key)
        path = self._safe_thumbnail_path(storage_key) if thumbnail else self._safe_path(storage_key)
        path.unlink(missing_ok=True)

    @staticmethod
    def _require_local_key(storage_key: str) -> None:
        if storage_key.startswith("tos-"):
            raise AppError(
                "object_storage_not_enabled",
                "该图片存储在 TOS，请启用对象存储配置",
                status_code=503,
            )


def _create_preview_thumbnail(source: Path, target: Path, thumbnail_max_size: int) -> None:
    with PillowImage.open(source) as image:
        image.seek(0)
        image.thumbnail(
            (
                thumbnail_max_size,
                thumbnail_max_size * THUMBNAIL_MAX_HEIGHT_MULTIPLIER,
            ),
            PillowImage.Resampling.LANCZOS,
            reducing_gap=3.0,
        )
        if image.mode not in {"RGB", "L"}:
            background = PillowImage.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image.convert("RGB"))
            image = background
        image.convert("RGB").save(
            target,
            format="JPEG",
            quality=90,
            subsampling=0,
            optimize=True,
        )


def _validate_image_pixels(
    width: int,
    height: int,
    max_pixels: int,
    max_long_image_pixels: int,
    long_image_min_aspect_ratio: float,
) -> None:
    pixels = width * height
    if pixels <= max_pixels:
        return

    longer = max(width, height)
    shorter = max(min(width, height), 1)
    aspect_ratio = longer / shorter
    if aspect_ratio >= long_image_min_aspect_ratio and pixels <= max_long_image_pixels:
        return

    if aspect_ratio >= long_image_min_aspect_ratio:
        limit = max_long_image_pixels
        limit_label = "长图"
    else:
        limit = max_pixels
        limit_label = "普通图片"
    raise AppError(
        "image_too_many_pixels",
        f"图片像素总数为 {pixels}，超过{limit_label}上限 {limit}",
        status_code=413,
    )
