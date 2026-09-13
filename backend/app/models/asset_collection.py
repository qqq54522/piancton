from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserAssetLike(Base):
    __tablename__ = "user_asset_likes"
    __table_args__ = (
        Index("ix_user_asset_likes_user_created", "user_id", "created_at", "asset_group_id"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    asset_group_id: Mapped[str] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_image_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    asset_group = relationship("AssetGroup", lazy="selectin")


class AssetCollectionBoard(Base):
    __tablename__ = "asset_collection_boards"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_asset_board_user_name"),
        Index("ix_asset_boards_user_updated", "user_id", "updated_at", "id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )

    items: Mapped[list["AssetCollectionBoardItem"]] = relationship(
        back_populates="board", cascade="all, delete-orphan", lazy="selectin"
    )


class AssetCollectionBoardItem(Base):
    __tablename__ = "asset_collection_board_items"
    __table_args__ = (
        Index("ix_asset_board_items_board_created", "board_id", "created_at", "asset_group_id"),
        Index("ix_asset_board_items_asset_group", "asset_group_id"),
    )

    board_id: Mapped[str] = mapped_column(
        ForeignKey("asset_collection_boards.id", ondelete="CASCADE"), primary_key=True
    )
    asset_group_id: Mapped[str] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_image_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    board: Mapped[AssetCollectionBoard] = relationship(back_populates="items")
    asset_group = relationship("AssetGroup", lazy="selectin")
