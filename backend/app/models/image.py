import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tag import Tag


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    tag_links: Mapped[list["ImageTag"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    categories: Mapped[list["ImageCategory"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    content_tags: Mapped[list["ContentTag"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    level2_categories: Mapped[list["ImageLevel2Category"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    business_labels: Mapped[list["ImageBusinessLabel"]] = relationship(
        back_populates="image", cascade="all, delete-orphan"
    )
    embedding: Mapped[Optional["ImageEmbedding"]] = relationship(
        back_populates="image", cascade="all, delete-orphan", uselist=False
    )


class ImageTag(Base):
    __tablename__ = "image_tags"

    image_id: Mapped[str] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True
    )
    image: Mapped[Image] = relationship(back_populates="tag_links")
    tag: Mapped["Tag"] = relationship(back_populates="image_links")


class ImageCategory(Base):
    __tablename__ = "image_categories"
    __table_args__ = (UniqueConstraint("image_id", "name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50), index=True)
    image: Mapped[Image] = relationship(back_populates="categories")


class ContentTag(Base):
    __tablename__ = "content_tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    tag_name: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    dimension: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    image: Mapped[Image] = relationship(back_populates="content_tags")


class ImageLevel2Category(Base):
    __tablename__ = "image_level2_categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    category_name: Mapped[str] = mapped_column(String(100), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image: Mapped[Image] = relationship(back_populates="level2_categories")


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
    business_labels: Mapped[list["ImageBusinessLabel"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class ImageBusinessLabel(Base):
    __tablename__ = "image_business_labels"
    __table_args__ = (
        UniqueConstraint(
            "image_id",
            "tag_id",
            "origin",
            "analysis_run_id",
            name="uq_image_business_label_source",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    image_id: Mapped[str] = mapped_column(ForeignKey("images.id", ondelete="CASCADE"), index=True)
    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), index=True)
    label_code: Mapped[str] = mapped_column(String(100), index=True)
    origin: Mapped[str] = mapped_column(String(20), index=True)
    role: Mapped[str] = mapped_column(String(20), default="secondary", index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_level: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_run_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )

    image: Mapped[Image] = relationship(back_populates="business_labels")
    tag: Mapped["Tag"] = relationship()
    analysis_run: Mapped[Optional[AnalysisRun]] = relationship(back_populates="business_labels")


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
