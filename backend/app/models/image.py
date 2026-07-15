import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.asset import AssetGroup


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Image(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    thumbnail_storage_key: Mapped[Optional[str]] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploader: Mapped[str] = mapped_column(String(100), default="local")
    download_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    image_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    semantic_profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asset_group_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), nullable=True, index=True
    )
    asset_role: Mapped[str] = mapped_column(String(20), default="primary", index=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    aspect_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    content_tags: Mapped[list["ContentTag"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["ImageEmbedding"]] = relationship(
        back_populates="image", cascade="all, delete-orphan", uselist=False
    )
    asset_group: Mapped[Optional["AssetGroup"]] = relationship(back_populates="images")


class ContentTag(Base):
    __tablename__ = "content_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    tag_name: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    dimension: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    image: Mapped[Image] = relationship(back_populates="content_tags")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    task: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="succeeded", index=True)
    taxonomy_version: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    model_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    image: Mapped[Image] = relationship(back_populates="analysis_runs")
class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"

    image_id: Mapped[str] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    model_name: Mapped[str] = mapped_column(String(200), index=True)
    dimension: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    document_text: Mapped[str] = mapped_column(Text)
    vector_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    image: Mapped[Image] = relationship(back_populates="embedding")
