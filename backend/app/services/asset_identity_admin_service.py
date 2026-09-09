from __future__ import annotations

from app.repositories.asset_identity_repository import ImageIdentityRepository
from app.schemas.asset_identity import (
    ImageIdentityCodeListResponse,
    ImageIdentityCodeRead,
    ImageIdentityCodeSummary,
)


class ImageIdentityAdminService:
    """Lists the single identity of each currently available image."""

    def __init__(self, db):
        self.repository = ImageIdentityRepository(db)

    def list(
        self,
        *,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> ImageIdentityCodeListResponse:
        rows, total = self.repository.list(
            keyword=keyword,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return ImageIdentityCodeListResponse(
            items=[self._to_read(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            summary=ImageIdentityCodeSummary(image_total=total),
        )

    @staticmethod
    def _to_read(row: dict) -> ImageIdentityCodeRead:
        return ImageIdentityCodeRead(
            **row,
            detail_path=f"/image/{row['image_id']}",
        )


# Compatibility alias for the dependency function name.
AssetIdentityAdminService = ImageIdentityAdminService
