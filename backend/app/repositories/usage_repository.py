from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.usage import UserUsageEvent
from app.models.user import User


class UsageEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: UserUsageEvent) -> UserUsageEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_between(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        limit: int = 5000,
    ) -> list[UserUsageEvent]:
        return list(
            self.db.scalars(
                select(UserUsageEvent)
                .where(UserUsageEvent.created_at >= start_at)
                .where(UserUsageEvent.created_at < end_at)
                .order_by(UserUsageEvent.created_at.desc(), UserUsageEvent.id.desc())
                .limit(limit)
            ).all()
        )


class UsageUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.created_at)).all())
