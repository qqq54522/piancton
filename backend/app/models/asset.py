import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        index=True,
        default=lambda: f"PC-{uuid.uuid4().hex[:6].upper()}",
    )
    title: Mapped[str] = mapped_column(String(255), index=True)
    # Kept as an application-validated reference to avoid a circular FK with images.asset_group_id.
    primary_image_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(20), default="approved", index=True)
    publish_status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    style_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_scene_image: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    primary_proof_point_code: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, index=True
    )
    primary_evidence_point_code: Mapped[Optional[str]] = mapped_column(
        String(140), nullable=True, index=True
    )
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )

    images = relationship("Image", back_populates="asset_group", cascade="all, delete-orphan")
    concept_links: Mapped[list["AssetConceptLink"]] = relationship(
        back_populates="asset_group", cascade="all, delete-orphan"
    )
    search_phrases: Mapped[list["AssetSearchPhrase"]] = relationship(
        back_populates="asset_group", cascade="all, delete-orphan"
    )
    source_links: Mapped[list["AssetSourceLink"]] = relationship(
        back_populates="asset_group", cascade="all, delete-orphan"
    )


class AssetIdentityCode(Base):
    """Permanent registry for public asset/version identifiers.

    Rows remain after an image or asset group is purged so identifiers cannot
    silently be assigned to a different piece of content later.
    """

    __tablename__ = "asset_identity_codes"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    code_type: Mapped[str] = mapped_column(String(20), index=True)
    asset_group_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("images.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    retired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AssetConceptLink(Base):
    __tablename__ = "asset_concept_links"
    __table_args__ = (
        UniqueConstraint(
            "asset_group_id", "concept_id", "origin", "relation_role",
            name="uq_asset_concept_source_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_group_id: Mapped[str] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), index=True
    )
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="RESTRICT"), index=True
    )
    relation_role: Mapped[str] = mapped_column(String(30), index=True)
    origin: Mapped[str] = mapped_column(String(20), index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    asset_group: Mapped[AssetGroup] = relationship(back_populates="concept_links")
    concept = relationship("BusinessConcept")


class AssetSearchPhrase(Base):
    __tablename__ = "asset_search_phrases"
    __table_args__ = (
        UniqueConstraint("asset_group_id", "phrase", "origin", name="uq_asset_phrase_origin"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_group_id: Mapped[str] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), index=True
    )
    phrase: Mapped[str] = mapped_column(String(300), index=True)
    origin: Mapped[str] = mapped_column(String(20), index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    asset_group: Mapped[AssetGroup] = relationship(back_populates="search_phrases")


class AssetSourceLink(Base):
    __tablename__ = "asset_source_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_group_id: Mapped[str] = mapped_column(
        ForeignKey("asset_groups.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(2048))
    link_type: Mapped[str] = mapped_column(String(40), default="figma", index=True)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    asset_group: Mapped[AssetGroup] = relationship(back_populates="source_links")
