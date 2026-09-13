from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.announcement import Announcement
from app.models.user import User


class AnnouncementRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, announcement: Announcement) -> Announcement:
        self.db.add(announcement)
        self.db.flush()
        return announcement

    def list_recent(self, limit: int = 100) -> list[Announcement]:
        return list(
            self.db.scalars(
                select(Announcement)
                .options(selectinload(Announcement.publisher))
                .order_by(Announcement.published_at.desc(), Announcement.id.desc())
                .limit(limit)
            ).all()
        )

    def latest_published_at(self) -> datetime | None:
        return self.db.scalar(select(func.max(Announcement.published_at)))

    def unread_count(self, user: User) -> int:
        threshold = user.announcements_read_at or user.created_at
        return int(
            self.db.scalar(
                select(func.count(Announcement.id)).where(Announcement.published_at > threshold)
            )
            or 0
        )

    def save_user(self, user: User) -> None:
        self.db.add(user)
        self.db.flush()
