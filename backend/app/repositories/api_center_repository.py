from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.api_provider import (
    ModelApiCredential,
    ModelApiHealthCheck,
    ModelCallTrace,
    ModelRoutingSlot,
)


class ApiCenterRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_credential(self, credential: ModelApiCredential) -> ModelApiCredential:
        self.db.add(credential)
        self.db.flush()
        return credential

    def get_credential(self, credential_id: str) -> ModelApiCredential | None:
        return self.db.get(ModelApiCredential, credential_id)

    def get_credential_by_label(self, label: str) -> ModelApiCredential | None:
        return self.db.scalar(
            select(ModelApiCredential).where(ModelApiCredential.label == label)
        )

    def list_credentials(self) -> list[ModelApiCredential]:
        return list(
            self.db.scalars(
                select(ModelApiCredential)
                .order_by(
                    ModelApiCredential.priority.asc(),
                    ModelApiCredential.created_at.desc(),
                )
            ).all()
        )

    def list_auto_assign_credentials(self) -> list[ModelApiCredential]:
        return list(
            self.db.scalars(
                select(ModelApiCredential)
                .where(ModelApiCredential.auto_assign_enabled.is_(True))
                .where(ModelApiCredential.status == "active")
                .order_by(
                    ModelApiCredential.priority.asc(),
                    ModelApiCredential.last_latency_ms.asc().nulls_last(),
                    ModelApiCredential.created_at.asc(),
                )
            ).all()
        )

    def add_slot(self, slot: ModelRoutingSlot) -> ModelRoutingSlot:
        self.db.add(slot)
        self.db.flush()
        return slot

    def get_slot_by_task(self, task: str) -> ModelRoutingSlot | None:
        return self.db.scalar(select(ModelRoutingSlot).where(ModelRoutingSlot.task == task))

    def list_slots(self) -> list[ModelRoutingSlot]:
        return list(
            self.db.scalars(
                select(ModelRoutingSlot).order_by(ModelRoutingSlot.created_at.asc())
            ).all()
        )

    def add_health_check(self, check: ModelApiHealthCheck) -> ModelApiHealthCheck:
        self.db.add(check)
        self.db.flush()
        return check

    def list_recent_health_checks(self, *, limit: int = 50) -> list[ModelApiHealthCheck]:
        return list(
            self.db.scalars(
                select(ModelApiHealthCheck)
                .order_by(desc(ModelApiHealthCheck.checked_at))
                .limit(limit)
            ).all()
        )

    def add_call_trace(self, trace: ModelCallTrace) -> ModelCallTrace:
        self.db.add(trace)
        self.db.flush()
        return trace

    def list_recent_call_traces(self, *, limit: int = 100) -> list[ModelCallTrace]:
        return list(
            self.db.scalars(
                select(ModelCallTrace)
                .order_by(desc(ModelCallTrace.created_at))
                .limit(limit)
            ).all()
        )

    def list_call_traces_since(self, *, hours: int = 24, limit: int = 2000) -> list[ModelCallTrace]:
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        return list(
            self.db.scalars(
                select(ModelCallTrace)
                .where(ModelCallTrace.created_at >= since)
                .order_by(desc(ModelCallTrace.created_at))
                .limit(limit)
            ).all()
        )
