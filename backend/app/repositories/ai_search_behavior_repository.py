from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage import AiSearchBehaviorEvent
from app.models.user import User


class AiSearchBehaviorRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: AiSearchBehaviorEvent) -> AiSearchBehaviorEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_pending(self, *, limit: int) -> list[AiSearchBehaviorEvent]:
        return list(
            self.db.scalars(
                select(AiSearchBehaviorEvent)
                .join(User, User.id == AiSearchBehaviorEvent.user_id)
                .where(AiSearchBehaviorEvent.status != "synced")
                .where(User.role == "business")
                .order_by(AiSearchBehaviorEvent.created_at, AiSearchBehaviorEvent.id)
                .limit(max(1, limit))
            ).all()
        )

    def mark_synced(
        self,
        events: list[AiSearchBehaviorEvent],
        *,
        synced_at: datetime,
    ) -> None:
        for event in events:
            event.status = "synced"
            event.attempt_count += 1
            event.last_error = None
            event.synced_at = synced_at

    def mark_failed(self, events: list[AiSearchBehaviorEvent], *, error: str) -> None:
        for event in events:
            event.status = "failed"
            event.attempt_count += 1
            event.last_error = error[:500]
