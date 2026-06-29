from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    keyword: Mapped[str] = mapped_column(String(200), index=True)
    requested_mode: Mapped[str] = mapped_column(String(20), index=True)
    served_mode: Mapped[str] = mapped_column(String(20), index=True)
    fallback: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    normalized_query: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    query_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    matched_category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    top_image_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    match_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )
