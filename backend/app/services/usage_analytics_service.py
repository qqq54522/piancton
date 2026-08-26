from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.models.usage import UserUsageEvent
from app.models.user import User
from app.repositories.usage_repository import UsageEventRepository, UsageUserRepository
from app.schemas.usage import (
    DailyUsageMetric,
    UsageAnalyticsSummary,
    UsageEventRead,
    UsageTotals,
    UserUsageMetric,
)
from app.services.unit_of_work import UnitOfWork


@dataclass
class UsageRange:
    start_at: datetime
    end_at: datetime
    date_from: date
    date_to: date


class UsageAnalyticsService:
    def __init__(self, db):
        self.events = UsageEventRepository(db)
        self.users = UsageUserRepository(db)
        self.uow = UnitOfWork(db)

    def record_login(
        self,
        user: User,
        *,
        client_ip: str | None,
        request_id: str | None,
    ) -> None:
        self.record_event(
            user_id=user.id,
            event_type="login",
            target_type="session",
            details={"clientIp": client_ip, "requestId": request_id},
        )

    def record_page_view(
        self,
        user: User,
        *,
        path: str,
        title: str | None = None,
    ) -> None:
        self.record_event(
            user_id=user.id,
            event_type="page_view",
            target_type="page",
            path=_bounded_path(path),
            details={"title": title} if title else {},
        )

    def record_download(
        self,
        *,
        user_id: str,
        image_id: str,
        request_id: str | None = None,
    ) -> None:
        self.record_event(
            user_id=user_id,
            event_type="download",
            target_type="image",
            target_id=image_id,
            details={"requestId": request_id} if request_id else {},
        )

    def record_event(
        self,
        *,
        user_id: str | None,
        event_type: str,
        target_type: str | None = None,
        target_id: str | None = None,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.add(
            UserUsageEvent(
                user_id=user_id,
                event_type=event_type,
                target_type=target_type,
                target_id=target_id,
                path=path,
                details_json=json.dumps(details or {}, ensure_ascii=False),
            )
        )
        self.uow.commit()

    def summary(self, *, days: int = 7, limit: int = 5000) -> UsageAnalyticsSummary:
        usage_range = _usage_range(days)
        users = self.users.list()
        users_by_id = {item.id: item for item in users}
        events = self.events.list_between(
            start_at=usage_range.start_at,
            end_at=usage_range.end_at,
            limit=limit,
        )
        daily_events: dict[date, list[UserUsageEvent]] = defaultdict(list)
        user_events: dict[str, list[UserUsageEvent]] = defaultdict(list)
        for event in events:
            event_day = _as_utc(event.created_at).date()
            daily_events[event_day].append(event)
            if event.user_id:
                user_events[event.user_id].append(event)

        return UsageAnalyticsSummary(
            date_from=usage_range.date_from,
            date_to=usage_range.date_to,
            totals=_totals(events),
            daily=[
                _daily_metric(day, daily_events.get(day, []))
                for day in _date_series(usage_range.date_from, usage_range.date_to)
            ],
            users=[
                _user_metric(user, user_events.get(user.id, []))
                for user in users
            ],
            recent_events=[
                _event_read(event, users_by_id.get(event.user_id or ""))
                for event in events[:100]
            ],
        )


def _usage_range(days: int) -> UsageRange:
    bounded_days = max(1, min(days, 90))
    today = datetime.now(timezone.utc).date()
    date_from = today - timedelta(days=bounded_days - 1)
    start_at = datetime.combine(date_from, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(today + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return UsageRange(start_at=start_at, end_at=end_at, date_from=date_from, date_to=today)


def _date_series(date_from: date, date_to: date) -> list[date]:
    current = date_from
    values: list[date] = []
    while current <= date_to:
        values.append(current)
        current += timedelta(days=1)
    return values


def _totals(events: list[UserUsageEvent]) -> UsageTotals:
    return UsageTotals(
        login_count=_count(events, "login"),
        page_view_count=_count(events, "page_view"),
        download_count=_count(events, "download"),
        active_user_count=len({event.user_id for event in events if event.user_id}),
    )


def _daily_metric(day: date, events: list[UserUsageEvent]) -> DailyUsageMetric:
    return DailyUsageMetric(
        date=day,
        login_count=_count(events, "login"),
        page_view_count=_count(events, "page_view"),
        download_count=_count(events, "download"),
        active_user_count=len({event.user_id for event in events if event.user_id}),
    )


def _user_metric(user: User, events: list[UserUsageEvent]) -> UserUsageMetric:
    last_activity_at = max(
        (_as_utc(event.created_at) for event in events),
        default=None,
    )
    return UserUsageMetric(
        user_id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        login_count=_count(events, "login"),
        page_view_count=_count(events, "page_view"),
        download_count=_count(events, "download"),
        activity_count=len(events),
        last_activity_at=last_activity_at,
    )


def _event_read(event: UserUsageEvent, user: User | None) -> UsageEventRead:
    return UsageEventRead(
        id=event.id,
        user_id=event.user_id,
        username=user.username if user else None,
        event_type=event.event_type,
        target_type=event.target_type,
        target_id=event.target_id,
        path=event.path,
        details=_loads_dict(event.details_json),
        created_at=event.created_at,
    )


def _count(events: list[UserUsageEvent], event_type: str) -> int:
    return sum(1 for event in events if event.event_type == event_type)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _loads_dict(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _bounded_path(value: str) -> str:
    cleaned = value.strip() or "/"
    if not cleaned.startswith("/"):
        cleaned = f"/{cleaned}"
    return cleaned[:300]
