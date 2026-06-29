from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.search_log import SearchLog


class SearchLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, log: SearchLog) -> SearchLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list_since(self, since: datetime, *, limit: int = 2000) -> list[SearchLog]:
        return list(
            self.db.scalars(
                select(SearchLog)
                .where(SearchLog.created_at >= since)
                .order_by(desc(SearchLog.created_at))
                .limit(limit)
            ).all()
        )

    def list_recent(self, *, limit: int = 50) -> list[SearchLog]:
        return list(
            self.db.scalars(
                select(SearchLog)
                .order_by(desc(SearchLog.created_at))
                .limit(limit)
            ).all()
        )
