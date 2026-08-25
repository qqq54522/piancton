from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models.asset import AssetGroup, AssetIdentityCode
from app.models.image import Image
from app.repositories.image_repository import IMAGE_LOAD_OPTIONS

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_CHAR_CLASS = re.escape(CODE_ALPHABET)
ASSET_CODE_PATTERN = re.compile(rf"^PC-[{CODE_CHAR_CLASS}]{{6}}$")
VERSION_CODE_PATTERN = re.compile(rf"^PC-[{CODE_CHAR_CLASS}]{{6}}-V[0-9]{{1,3}}$")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetIdentityService:
    """Allocates and resolves public asset identifiers without model calls."""

    def __init__(self, db: Session):
        self.db = db

    def allocate_asset_code(self) -> str:
        for _ in range(20):
            code = "PC-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if not self.db.scalar(
                select(AssetIdentityCode.code).where(AssetIdentityCode.code == code)
            ):
                return code
        raise RuntimeError("unable to allocate asset identity code")

    def allocate_version_code(self, asset_code: str, version_no: int) -> str:
        code = f"{asset_code}-V{version_no:02d}"
        if self.db.scalar(
            select(AssetIdentityCode.code).where(AssetIdentityCode.code == code)
        ):
            raise RuntimeError(f"version identity code already exists: {code}")
        return code

    def register_group(self, group: AssetGroup) -> None:
        self.db.add(
            AssetIdentityCode(
                code=group.asset_code,
                code_type="asset",
                asset_group_id=group.id,
            )
        )

    def register_image(self, image: Image) -> None:
        self.db.add(
            AssetIdentityCode(
                code=image.version_code,
                code_type="version",
                asset_group_id=image.asset_group_id,
                image_id=image.id,
            )
        )

    def find_image(self, value: str) -> Image | None:
        code = extract_identity_code(value)
        if not code:
            return None
        identity = self.db.scalar(
            select(AssetIdentityCode).where(AssetIdentityCode.code == code)
        )
        if not identity or identity.retired_at is not None:
            return None
        if identity.code_type == "version" and identity.image_id:
            return self.db.scalar(
                select(Image)
                .where(Image.id == identity.image_id, Image.deleted_at.is_(None))
                .options(*IMAGE_LOAD_OPTIONS)
            )
        if identity.code_type == "asset" and identity.asset_group_id:
            group = self.db.scalar(
                select(AssetGroup)
                .where(AssetGroup.id == identity.asset_group_id)
                .options(selectinload(AssetGroup.images))
            )
            if not group:
                return None
            active_images = [
                image
                for image in group.images
                if image.deleted_at is None and image.is_current
            ]
            primary = next(
                (image for image in active_images if image.id == group.primary_image_id),
                None,
            )
            image_id = (
                primary.id
                if primary
                else next(
                    (
                        image.id
                        for image in sorted(
                            active_images,
                            key=lambda item: item.version_no,
                            reverse=True,
                        )
                    ),
                    None,
                )
            )
            if image_id:
                return self.db.scalar(
                    select(Image)
                    .where(Image.id == image_id, Image.deleted_at.is_(None))
                    .options(*IMAGE_LOAD_OPTIONS)
                )
        return None

    def retire_image(self, image_id: str) -> None:
        rows = list(
            self.db.scalars(
                select(AssetIdentityCode).where(
                    AssetIdentityCode.image_id == image_id,
                    AssetIdentityCode.retired_at.is_(None),
                )
            ).all()
        )
        for row in rows:
            row.retired_at = utcnow()

    def retire_group(self, asset_group_id: str) -> None:
        rows = list(
            self.db.scalars(
                select(AssetIdentityCode).where(
                    AssetIdentityCode.asset_group_id == asset_group_id,
                    AssetIdentityCode.retired_at.is_(None),
                )
            ).all()
        )
        for row in rows:
            row.retired_at = utcnow()

    def require_image(self, value: str) -> Image:
        image = self.find_image(value)
        if not image:
            raise NotFoundError("asset_identity_not_found", "素材身份码对应的图片不存在")
        return image


def extract_identity_code(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    candidates = [raw]
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        candidates.extend(
            [
                parsed.path.rsplit("/", 1)[-1],
                *parse_qs(parsed.query).get("code", []),
                *parse_qs(parsed.query).get("assetCode", []),
                *parse_qs(parsed.query).get("versionCode", []),
            ]
        )
    for candidate in candidates:
        code = candidate.strip().upper().rstrip("/")
        if ASSET_CODE_PATTERN.fullmatch(code) or VERSION_CODE_PATTERN.fullmatch(code):
            return code
    return None


def looks_like_identity_query(value: str) -> bool:
    raw = value.strip().upper()
    if raw.startswith("PC-"):
        return True
    parsed = urlparse(value.strip())
    if parsed.scheme and parsed.netloc:
        return any(
            key in parsed.query
            for key in ("code=", "assetCode=", "versionCode=")
        ) or "/image/" in parsed.path or "/share/" in parsed.path
    return False
