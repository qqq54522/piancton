import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BusinessConcept(Base):
    __tablename__ = "business_concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    concept_type: Mapped[str] = mapped_column(String(50), default="business_term", index=True)
    definition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    replaced_by_concept_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True
    )

    replacement: Mapped[Optional["BusinessConcept"]] = relationship(
        remote_side="BusinessConcept.id", foreign_keys=[replaced_by_concept_id]
    )
    system_links: Mapped[list["ConceptSystemLink"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )
    search_phrases: Mapped[list["ConceptSearchPhrase"]] = relationship(
        back_populates="concept", cascade="all, delete-orphan"
    )


class ConceptSystemLink(Base):
    __tablename__ = "concept_system_links"

    concept_id: Mapped[str] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="CASCADE"), primary_key=True
    )
    system_tag_id: Mapped[str] = mapped_column(
        ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), default="core", index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    concept: Mapped[BusinessConcept] = relationship(back_populates="system_links")
    system_tag = relationship("Tag")


class ConceptRelation(Base):
    __tablename__ = "concept_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_concept_id", "target_concept_id", "relation_type",
            name="uq_concept_relation",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_concept_id: Mapped[str] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="CASCADE"), index=True
    )
    target_concept_id: Mapped[str] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="CASCADE"), index=True
    )
    relation_type: Mapped[str] = mapped_column(String(40), index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    source_concept: Mapped[BusinessConcept] = relationship(foreign_keys=[source_concept_id])
    target_concept: Mapped[BusinessConcept] = relationship(foreign_keys=[target_concept_id])


class ConceptSearchPhrase(Base):
    __tablename__ = "concept_search_phrases"
    __table_args__ = (
        UniqueConstraint("concept_id", "phrase", "origin", name="uq_concept_phrase_origin"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_id: Mapped[str] = mapped_column(
        ForeignKey("business_concepts.id", ondelete="CASCADE"), index=True
    )
    phrase: Mapped[str] = mapped_column(String(300), index=True)
    phrase_type: Mapped[str] = mapped_column(String(30), default="official", index=True)
    origin: Mapped[str] = mapped_column(String(30), default="manual", index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="accepted", index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source_ref: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    concept: Mapped[BusinessConcept] = relationship(back_populates="search_phrases")
