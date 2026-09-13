from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field, field_validator

from app.schemas.base import ApiModel


class AnnouncementCreate(ApiModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("title", "content", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class AnnouncementRead(ApiModel):
    id: str
    title: str
    content: str
    publisher_name: str
    published_at: datetime


class AnnouncementListResponse(ApiModel):
    items: list[AnnouncementRead]


class AnnouncementFeedResponse(AnnouncementListResponse):
    unread_count: int


class AnnouncementUnreadCount(ApiModel):
    unread_count: int


class AnnouncementMarkRead(ApiModel):
    model_config = ConfigDict(extra="forbid")

    through_published_at: datetime
