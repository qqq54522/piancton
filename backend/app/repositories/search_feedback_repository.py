from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.search_feedback import SearchFeedbackEvent


class SearchFeedbackRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, event: SearchFeedbackEvent) -> SearchFeedbackEvent:
        self.db.add(event)
        self.db.flush()
        return event

    def list_since(self, since: datetime, *, limit: int = 1000) -> list[SearchFeedbackEvent]:
        return list(
            self.db.scalars(
                select(SearchFeedbackEvent)
                .where(SearchFeedbackEvent.created_at >= since)
                .order_by(desc(SearchFeedbackEvent.created_at))
                .limit(limit)
            ).all()
        )
