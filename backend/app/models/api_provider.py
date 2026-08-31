from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModelApiCredential(Base):
    __tablename__ = "model_api_credentials"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    label: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    provider_type: Mapped[str] = mapped_column(
        String(40),
        default="openai_compatible",
        index=True,
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    api_key_secret: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    api_key_preview: Mapped[str] = mapped_column(String(32), nullable=False)
    task_scope_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)
    timeout_seconds: Mapped[float] = mapped_column(Float, default=20.0)
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    temperature_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=1)
    auto_assign_enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    capability_profile_json: Mapped[str] = mapped_column(Text, default="{}")
    last_status: Mapped[Optional[str]] = mapped_column(String(24), nullable=True, index=True)
    last_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class ModelRoutingSlot(Base):
    __tablename__ = "model_routing_slots"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    task: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    primary_credential_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("model_api_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    backup_credential_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    excluded_credential_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    timeout_seconds: Mapped[float] = mapped_column(Float, default=20.0)
    hedging_delay_ms: Mapped[int] = mapped_column(Integer, default=2500)
    max_parallel: Mapped[int] = mapped_column(Integer, default=1)
    auto_select_enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )


class ModelApiHealthCheck(Base):
    __tablename__ = "model_api_health_checks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    credential_id: Mapped[str] = mapped_column(
        ForeignKey("model_api_credentials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task: Mapped[str] = mapped_column(String(80), default="search_system_routing", index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, index=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    error_summary: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        index=True,
    )


class ModelCallTrace(Base):
    __tablename__ = "model_call_traces"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    search_log_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("search_logs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    task: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    layer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    credential_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("model_api_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    credential_label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    provider: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, index=True)
    fallback_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    error_summary: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    response_valid: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    output_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        index=True,
    )


class ApiCenterSetting(Base):
    __tablename__ = "api_center_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
