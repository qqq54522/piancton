from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urljoin

from PIL import Image as PillowImage
from PIL import UnidentifiedImageError

from app.core.errors import AppError, NotFoundError
from app.schemas.asset_agent import AssetAgentTemporaryImageRead
from app.services.storage_service import ALLOWED_FORMATS, validate_image_pixels

TEMPORARY_IMAGE_TTL = timedelta(minutes=15)
TEMPORARY_IMAGE_MAX_BYTES = 10 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{24,80}$")


@dataclass(frozen=True)
class AssetAgentTemporaryImageFile:
    path: Path
    media_type: str
    title: str


class AssetAgentTemporaryImageService:
    """Short-lived image bridge for AI Search multimodal chat.

    Files live outside the material database and are addressed by an unguessable,
    expiring capability token so the external AI Search service can fetch them.
    """

    def __init__(
        self,
        root: Path,
        *,
        public_base_url: str,
        max_upload_bytes: int,
        max_image_pixels: int,
        max_long_image_pixels: int,
        long_image_min_aspect_ratio: float,
    ):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.public_base_url = public_base_url.rstrip("/")
        self.max_upload_bytes = min(max_upload_bytes, TEMPORARY_IMAGE_MAX_BYTES)
        self.max_image_pixels = max_image_pixels
        self.max_long_image_pixels = max_long_image_pixels
        self.long_image_min_aspect_ratio = long_image_min_aspect_ratio

    def create(
        self,
        stream: BinaryIO,
        *,
        owner_id: str,
        filename: str,
    ) -> AssetAgentTemporaryImageRead:
        self.cleanup_expired()
        token = secrets.token_urlsafe(24)
        staged_path = self.root / f".{token}.upload"
        target_path: Path | None = None
        metadata_path = self._metadata_path(token)
        size = 0
        try:
            with staged_path.open("wb") as output:
                while chunk := stream.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_upload_bytes:
                        raise AppError(
                            "upload_too_large",
                            f"临时问图不能超过 {self.max_upload_bytes // (1024 * 1024)}MB",
                            status_code=413,
                        )
                    output.write(chunk)
            if size == 0:
                raise AppError("empty_upload", "请选择一张图片", status_code=422)

            try:
                with PillowImage.open(staged_path) as image:
                    image_format = image.format or ""
                    width, height = image.size
                    validate_image_pixels(
                        width,
                        height,
                        self.max_image_pixels,
                        self.max_long_image_pixels,
                        self.long_image_min_aspect_ratio,
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
            target_path = self._image_path(token, extension)
            os.replace(staged_path, target_path)
            expires_at = _now() + TEMPORARY_IMAGE_TTL
            title = _safe_title(filename)
            metadata_path.write_text(
                json.dumps(
                    {
                        "ownerId": owner_id,
                        "title": title,
                        "mediaType": media_type,
                        "extension": extension,
                        "expiresAt": expires_at.isoformat(),
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                encoding="utf-8",
            )
            return AssetAgentTemporaryImageRead(
                token=token,
                title=title,
                preview_url=self.public_url(token),
                expires_at=expires_at,
            )
        except Exception:
            staged_path.unlink(missing_ok=True)
            if target_path is not None:
                target_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)
            raise

    def public_file(self, token: str) -> AssetAgentTemporaryImageFile:
        metadata = self._load_metadata(token)
        path = self._image_path(token, str(metadata["extension"]))
        if not path.is_file():
            self._delete_files(token, metadata)
            raise NotFoundError("temporary_image_not_found", "临时图片不存在或已过期")
        return AssetAgentTemporaryImageFile(
            path=path,
            media_type=str(metadata["mediaType"]),
            title=str(metadata["title"]),
        )

    def public_url_for_owner(self, token: str, *, owner_id: str) -> str:
        metadata = self._load_metadata(token)
        if metadata.get("ownerId") != owner_id:
            raise NotFoundError("temporary_image_not_found", "临时图片不存在或已过期")
        return self.public_url(token)

    def public_url(self, token: str) -> str:
        self._validate_token(token)
        if not self.public_base_url:
            raise AppError(
                "temporary_image_public_url_missing",
                "临时问图地址尚未配置，请联系管理员",
                status_code=503,
            )
        return urljoin(
            f"{self.public_base_url}/",
            f"api/asset-agent/temporary-images/{token}",
        )

    def delete(self, token: str, *, owner_id: str | None = None) -> None:
        try:
            metadata = self._load_metadata(token, allow_expired=True)
        except NotFoundError:
            return
        if owner_id is not None and metadata.get("ownerId") != owner_id:
            raise NotFoundError("temporary_image_not_found", "临时图片不存在或已过期")
        self._delete_files(token, metadata)

    def cleanup_expired(self) -> None:
        for metadata_path in self.root.glob("*.json"):
            token = metadata_path.stem
            if not TOKEN_PATTERN.fullmatch(token):
                continue
            try:
                metadata = self._read_metadata(metadata_path)
                expires_at = datetime.fromisoformat(str(metadata["expiresAt"]))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
                self._delete_all_token_files(token)
                continue
            if _aware(expires_at) <= _now():
                self._delete_files(token, metadata)

    def _load_metadata(
        self,
        token: str,
        *,
        allow_expired: bool = False,
    ) -> dict[str, Any]:
        self._validate_token(token)
        metadata_path = self._metadata_path(token)
        try:
            metadata = self._read_metadata(metadata_path)
            expires_at = _aware(datetime.fromisoformat(str(metadata["expiresAt"])))
            extension = str(metadata["extension"])
            if extension not in {item[1] for item in ALLOWED_FORMATS.values()}:
                raise ValueError("invalid extension")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError) as exc:
            self._delete_all_token_files(token)
            raise NotFoundError(
                "temporary_image_not_found",
                "临时图片不存在或已过期",
            ) from exc
        if not allow_expired and expires_at <= _now():
            self._delete_files(token, metadata)
            raise NotFoundError("temporary_image_not_found", "临时图片不存在或已过期")
        return metadata

    @staticmethod
    def _read_metadata(path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise OSError("metadata missing")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("metadata must be an object")
        return raw

    def _delete_files(self, token: str, metadata: dict[str, Any]) -> None:
        extension = str(metadata.get("extension", ""))
        if extension in {item[1] for item in ALLOWED_FORMATS.values()}:
            self._image_path(token, extension).unlink(missing_ok=True)
        self._metadata_path(token).unlink(missing_ok=True)

    def _delete_all_token_files(self, token: str) -> None:
        self._validate_token(token)
        for _media_type, extension in ALLOWED_FORMATS.values():
            self._image_path(token, extension).unlink(missing_ok=True)
        self._metadata_path(token).unlink(missing_ok=True)

    def _metadata_path(self, token: str) -> Path:
        self._validate_token(token)
        return self.root / f"{token}.json"

    def _image_path(self, token: str, extension: str) -> Path:
        self._validate_token(token)
        path = (self.root / f"{token}{extension}").resolve()
        if path.parent != self.root:
            raise AppError("invalid_temporary_image_token", "非法临时图片标识")
        return path

    @staticmethod
    def _validate_token(token: str) -> None:
        if not TOKEN_PATTERN.fullmatch(token):
            raise NotFoundError("temporary_image_not_found", "临时图片不存在或已过期")


def _safe_title(filename: str) -> str:
    name = Path(filename or "临时图片").name
    title = name.rsplit(".", 1)[0].strip()
    return (title or "临时图片")[:255]


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)
