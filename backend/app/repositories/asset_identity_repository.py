from __future__ import annotations

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.asset import AssetGroup, AssetIdentityCode
from app.models.image import Image


class AssetIdentityRepository:
    """Read-only queries for the permanent asset identity registry."""

    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        *,
        keyword: str | None,
        code_type: str,
        status: str,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        stmt = self._base_statement()
        count_stmt = self._count_statement()

        conditions = self._conditions(keyword=keyword, code_type=code_type, status=status)
        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        stmt = stmt.order_by(
            AssetIdentityCode.created_at.desc(),
            AssetIdentityCode.code.desc(),
        ).offset(offset).limit(limit)
        rows = [dict(row) for row in self.db.execute(stmt).mappings().all()]
        total = int(self.db.scalar(count_stmt) or 0)
        return rows, total

    def summary(self) -> dict[str, int]:
        status_expression = self._status_expression()
        rows = self.db.execute(
            select(
                AssetIdentityCode.code_type.label("code_type"),
                status_expression.label("status"),
                func.count(AssetIdentityCode.code).label("count"),
            )
            .outerjoin(
                AssetGroup,
                AssetGroup.id == AssetIdentityCode.asset_group_id,
            )
            .outerjoin(Image, Image.id == AssetIdentityCode.image_id)
            .group_by(AssetIdentityCode.code_type, status_expression)
        ).all()

        values = {
            "asset_total": 0,
            "version_total": 0,
            "active_total": 0,
            "deleted_total": 0,
            "retired_total": 0,
        }
        for code_type, status, count in rows:
            if code_type == "asset":
                values["asset_total"] += count
            elif code_type == "version":
                values["version_total"] += count
            values[f"{status}_total"] += count
        return values

    def _base_statement(self):
        return select(
            AssetIdentityCode.code.label("code"),
            AssetIdentityCode.code_type.label("code_type"),
            AssetIdentityCode.asset_group_id.label("asset_group_id"),
            AssetIdentityCode.image_id.label("image_id"),
            AssetIdentityCode.created_at.label("created_at"),
            AssetIdentityCode.retired_at.label("retired_at"),
            AssetGroup.title.label("asset_title"),
            AssetGroup.primary_image_id.label("primary_image_id"),
            Image.title.label("image_title"),
            Image.file_name.label("file_name"),
            Image.asset_role.label("asset_role"),
            Image.version_no.label("version_no"),
            Image.is_current.label("is_current"),
            Image.deleted_at.label("deleted_at"),
            self._status_expression().label("status"),
        ).outerjoin(
            AssetGroup,
            AssetGroup.id == AssetIdentityCode.asset_group_id,
        ).outerjoin(
            Image,
            Image.id == AssetIdentityCode.image_id,
        )

    def _count_statement(self):
        return (
            select(func.count(AssetIdentityCode.code))
            .select_from(AssetIdentityCode)
            .outerjoin(
                AssetGroup,
                AssetGroup.id == AssetIdentityCode.asset_group_id,
            )
            .outerjoin(
                Image,
                Image.id == AssetIdentityCode.image_id,
            )
        )

    def _conditions(self, *, keyword: str | None, code_type: str, status: str):
        conditions = []
        if code_type != "all":
            conditions.append(AssetIdentityCode.code_type == code_type)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    AssetIdentityCode.code.ilike(pattern),
                    AssetGroup.title.ilike(pattern),
                    Image.title.ilike(pattern),
                    Image.file_name.ilike(pattern),
                )
            )
        if status != "all":
            conditions.append(self._status_expression() == status)
        return conditions

    def _status_expression(self):
        return case(
            (AssetIdentityCode.retired_at.is_not(None), literal("retired")),
            (
                and_(
                    AssetIdentityCode.code_type == "version",
                    Image.deleted_at.is_not(None),
                ),
                literal("deleted"),
            ),
            (AssetGroup.id.is_(None), literal("retired")),
            else_=literal("active"),
        )
