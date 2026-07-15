import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    color: Mapped[str] = mapped_column(String(20), default="#6B7280")
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("tags.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_secondary: Mapped[bool] = mapped_column(Boolean, default=False)
    node_type: Mapped[str] = mapped_column(String(30), default="custom", index=True)
    assignable: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    taxonomy_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        Index(
            "uq_tags_root_name",
            "name",
            unique=True,
            sqlite_where=parent_id.is_(None),
            postgresql_where=parent_id.is_(None),
        ),
        Index(
            "uq_tags_parent_name",
            "parent_id",
            "name",
            unique=True,
            sqlite_where=parent_id.is_not(None),
            postgresql_where=parent_id.is_not(None),
        ),
    )

    parent: Mapped[Optional["Tag"]] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Tag"]] = relationship(back_populates="parent")
