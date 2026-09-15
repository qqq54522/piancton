import uuid

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ManagedChannel(Base):
    __tablename__ = "managed_channels"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    first_level_label: Mapped[str] = mapped_column(String(30), default="分类")
    second_level_label: Mapped[str] = mapped_column(String(30), default="子分类")
    third_level_label: Mapped[str] = mapped_column(String(30), default="细分")


class ChannelFolder(Base):
    __tablename__ = "channel_folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    channel_name: Mapped[str] = mapped_column(
        ForeignKey("managed_channels.name", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("channel_folders.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(80))

    __table_args__ = (Index("ix_channel_folders_channel_parent", "channel_name", "parent_id"),)


class ImageChannelPlacement(Base):
    __tablename__ = "image_channel_placements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    channel_name: Mapped[str] = mapped_column(
        ForeignKey("managed_channels.name", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[str] = mapped_column(
        ForeignKey("channel_folders.id", ondelete="RESTRICT"), index=True
    )

    __table_args__ = (
        UniqueConstraint("image_id", "channel_name", name="uq_image_channel_placement"),
    )
