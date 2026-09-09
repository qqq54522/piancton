from __future__ import annotations

import re
import secrets
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.image import Image
from app.repositories.image_repository import IMAGE_LOAD_OPTIONS

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_CHAR_CLASS = re.escape(CODE_ALPHABET)
IDENTITY_CODE_PATTERN = re.compile(rf"^PC-[{CODE_CHAR_CLASS}]{{6}}$")


class ImageIdentityService:
    """Allocates and resolves the single public identity attached to an image."""

    def __init__(self, db: Session):
        self.db = db

    def allocate_code(self) -> str:
        for _ in range(20):
            code = "PC-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if not self.db.scalar(
                select(Image.id).where(Image.identity_code == code)
            ):
                return code
        raise RuntimeError("unable to allocate image identity code")

    def find_image(self, value: str) -> Image | None:
        code = extract_identity_code(value)
        if not code:
            return None
        return self.db.scalar(
            select(Image)
            .where(
                Image.identity_code == code,
                Image.deleted_at.is_(None),
            )
            .options(*IMAGE_LOAD_OPTIONS)
        )

    def require_image(self, value: str) -> Image:
        image = self.find_image(value)
        if not image:
            raise NotFoundError("image_identity_not_found", "身份码对应的图片不存在")
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
            ]
        )
    for candidate in candidates:
        code = candidate.strip().upper().rstrip("/")
        if IDENTITY_CODE_PATTERN.fullmatch(code):
            return code
    return None


def looks_like_identity_query(value: str) -> bool:
    raw = value.strip().upper()
    if raw.startswith("PC-"):
        return True
    parsed = urlparse(value.strip())
    if parsed.scheme and parsed.netloc:
        return "code=" in parsed.query or "/image/" in parsed.path
    return False


# Compatibility alias for internal dependency names while the public model is image-only.
AssetIdentityService = ImageIdentityService
