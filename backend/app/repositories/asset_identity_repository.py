from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.models.image import Image


class ImageIdentityRepository:
    """Read-only queries for identities on currently available images."""

    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        *,
        keyword: str | None,
        offset: int,
        limit: int,
    ) -> tuple[list[dict], int]:
        conditions: list[ColumnElement[bool]] = [
            Image.deleted_at.is_(None),
            Image.identity_code.is_not(None),
        ]
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Image.identity_code.ilike(pattern),
                    Image.title.ilike(pattern),
                    Image.file_name.ilike(pattern),
                )
            )

        stmt = (
            select(
                Image.identity_code.label("code"),
                Image.id.label("image_id"),
                Image.title.label("image_title"),
                Image.file_name.label("file_name"),
                Image.channel.label("channel"),
                Image.width.label("width"),
                Image.height.label("height"),
                Image.created_at.label("created_at"),
            )
            .where(*conditions)
            .order_by(Image.created_at.desc(), Image.identity_code.desc())
            .offset(offset)
            .limit(limit)
        )
        count_stmt = select(func.count(Image.id)).where(*conditions)
        rows = [dict(row) for row in self.db.execute(stmt).mappings().all()]
        total = int(self.db.scalar(count_stmt) or 0)
        return rows, total


# Keep the old import name internal-only while callers migrate to image terminology.
AssetIdentityRepository = ImageIdentityRepository
