from __future__ import annotations

from app.core.errors import AppError
from app.domain.image_titles import (
    allocate_unique_image_title,
    clean_image_title,
    title_namespace,
)
from app.repositories.image_repository import ImageRepository


class ImageTitleService:
    """Resolve globally unique display titles without coupling them to selling points."""

    def __init__(self, db):
        self.images = ImageRepository(db)

    def resolve(
        self,
        requested: str,
        *,
        exclude_image_id: str | None = None,
        reserve: bool = True,
    ) -> str:
        title = clean_image_title(requested)
        if not title:
            raise AppError(
                "invalid_image_title",
                "素材名称不能为空",
                status_code=422,
            )
        if reserve:
            self.images.lock_title_namespace(title_namespace(title))
        existing = self.images.list_all_titles(
            exclude_image_id=exclude_image_id,
        )
        resolved = allocate_unique_image_title(title, existing)
        return resolved
