from __future__ import annotations

from app.repositories.asset_identity_repository import AssetIdentityRepository
from app.schemas.asset_identity import (
    AssetIdentityCodeListResponse,
    AssetIdentityCodeRead,
    AssetIdentityCodeSummary,
)


class AssetIdentityAdminService:
    """Provides the administrator's read-only identity-code ledger."""

    def __init__(self, db):
        self.repository = AssetIdentityRepository(db)

    def list(
        self,
        *,
        keyword: str | None,
        code_type: str,
        status: str,
        page: int,
        page_size: int,
    ) -> AssetIdentityCodeListResponse:
        rows, total = self.repository.list(
            keyword=keyword,
            code_type=code_type,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        summary = self.repository.summary()
        return AssetIdentityCodeListResponse(
            items=[self._to_read(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
            summary=AssetIdentityCodeSummary(**summary),
        )

    @staticmethod
    def _to_read(row: dict) -> AssetIdentityCodeRead:
        detail_id = row["image_id"] or row["code"]
        detail_path = f"/image/{detail_id}" if row["status"] == "active" else None
        return AssetIdentityCodeRead(
            code=row["code"],
            code_type=row["code_type"],
            asset_group_id=row["asset_group_id"],
            primary_image_id=row["primary_image_id"],
            image_id=row["image_id"],
            asset_title=row["asset_title"],
            image_title=row["image_title"],
            file_name=row["file_name"],
            asset_role=row["asset_role"],
            version_no=row["version_no"],
            is_current=row["is_current"],
            deleted_at=row["deleted_at"],
            created_at=row["created_at"],
            retired_at=row["retired_at"],
            status=row["status"],
            detail_path=detail_path,
        )
