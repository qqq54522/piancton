from __future__ import annotations

from datetime import datetime, timezone

from app.models.announcement import Announcement
from app.models.user import User
from app.repositories.announcement_repository import AnnouncementRepository
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementFeedResponse,
    AnnouncementListResponse,
    AnnouncementRead,
    AnnouncementUnreadCount,
)
from app.services.unit_of_work import UnitOfWork


class AnnouncementService:
    def __init__(self, db):
        self.announcements = AnnouncementRepository(db)
        self.uow = UnitOfWork(db)

    def feed(self, user: User) -> AnnouncementFeedResponse:
        return AnnouncementFeedResponse(
            items=[self._read(item) for item in self.announcements.list_recent()],
            unread_count=self.announcements.unread_count(user),
        )

    def unread_count(self, user: User) -> AnnouncementUnreadCount:
        return AnnouncementUnreadCount(unread_count=self.announcements.unread_count(user))

    def mark_read(self, user: User, through_published_at: datetime) -> AnnouncementUnreadCount:
        latest = self.announcements.latest_published_at()
        if latest is None:
            return AnnouncementUnreadCount(unread_count=0)
        safe_through = min(_as_utc(through_published_at), _as_utc(latest))
        current = _as_utc(user.announcements_read_at or user.created_at)
        if safe_through > current:
            user.announcements_read_at = safe_through
            self.announcements.save_user(user)
            self.uow.commit()
        return self.unread_count(user)

    def list_for_managers(self) -> AnnouncementListResponse:
        return AnnouncementListResponse(
            items=[self._read(item) for item in self.announcements.list_recent()]
        )

    def publish(self, actor: User, payload: AnnouncementCreate) -> AnnouncementRead:
        announcement = self.announcements.add(
            Announcement(
                title=payload.title,
                content=payload.content,
                published_by_user_id=actor.id,
            )
        )
        announcement.publisher = actor
        self.uow.commit()
        return self._read(announcement)

    @staticmethod
    def _read(announcement: Announcement) -> AnnouncementRead:
        return AnnouncementRead(
            id=announcement.id,
            title=announcement.title,
            content=announcement.content,
            publisher_name=(announcement.publisher.username if announcement.publisher else "系统"),
            published_at=announcement.published_at,
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
