from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.models.image import Image
from app.repositories.search_feedback_repository import SearchFeedbackRepository
from app.repositories.usage_repository import UsageEventRepository, UsageUserRepository
from app.schemas.recommendation import RecommendationEvaluationRead

RecommendationStrategyMode = Literal[
    "learning",
    "balanced",
    "personalized",
    "explore",
]

HOME_RECOMMENDATION_SOURCE = "home_for_you"
POSITIVE_ACTIONS = {
    "open_detail",
    "download",
    "copy_identity",
    "add_to_project",
    "send_to_agent",
}
CONVERSION_ACTIONS = {
    "download",
    "copy_identity",
    "add_to_project",
    "send_to_agent",
}


@dataclass(frozen=True)
class RecommendationEvaluation:
    window_days: int
    exposure_count: int
    positive_action_count: int
    conversion_count: int
    click_through_rate: float
    conversion_rate: float
    feedback_count: int
    satisfaction_rate: float
    strategy_mode: RecommendationStrategyMode
    personalized_share: float
    exploration_interval: int
    summary: str
    evaluated_at: datetime

    def to_read(self) -> RecommendationEvaluationRead:
        return RecommendationEvaluationRead(**self.__dict__)


class RecommendationStrategyService:
    """Evaluate recommendation signals and choose a bounded ranking blend.

    The strategy never edits image facts or business relationships. It only
    changes how often a local cross-channel exploration item is mixed into the
    upstream personalized order.
    """

    def __init__(self, db):
        self.events = UsageEventRepository(db)
        self.feedback = SearchFeedbackRepository(db)
        self.users = UsageUserRepository(db)

    def evaluate(
        self,
        *,
        user_id: str | None = None,
        window_days: int = 30,
        limit: int = 10000,
    ) -> RecommendationEvaluation:
        days = max(7, min(window_days, 90))
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)
        business_user_ids = {user.id for user in self.users.list() if user.role == "business"}
        events = self.events.list_between(
            start_at=since,
            end_at=now + timedelta(seconds=1),
            limit=limit,
        )
        recommendation_actions: list[str] = []
        for event in events:
            if event.event_type != "search_interaction":
                continue
            if event.user_id not in business_user_ids:
                continue
            if user_id and event.user_id != user_id:
                continue
            details = _json_dict(event.details_json)
            if details.get("source") != HOME_RECOMMENDATION_SOURCE:
                continue
            recommendation_actions.append(str(details.get("action") or ""))

        feedback = [
            item
            for item in self.feedback.list_since(since, limit=limit)
            if item.actor_user_id in business_user_ids
            and (not user_id or item.actor_user_id == user_id)
        ]
        exposure_count = recommendation_actions.count("exposure")
        positive_action_count = sum(
            1 for action in recommendation_actions if action in POSITIVE_ACTIONS
        )
        conversion_count = sum(
            1 for action in recommendation_actions if action in CONVERSION_ACTIONS
        )
        feedback_count = len(feedback)
        positive_feedback_count = sum(1 for item in feedback if item.feedback_type == "relevant")
        click_through_rate = _rate(positive_action_count, exposure_count)
        conversion_rate = _rate(conversion_count, exposure_count)
        satisfaction_rate = _rate(positive_feedback_count, feedback_count)
        mode, personalized_share, exploration_interval, summary = _select_strategy(
            exposure_count=exposure_count,
            click_through_rate=click_through_rate,
            feedback_count=feedback_count,
            satisfaction_rate=satisfaction_rate,
        )
        return RecommendationEvaluation(
            window_days=days,
            exposure_count=exposure_count,
            positive_action_count=positive_action_count,
            conversion_count=conversion_count,
            click_through_rate=click_through_rate,
            conversion_rate=conversion_rate,
            feedback_count=feedback_count,
            satisfaction_rate=satisfaction_rate,
            strategy_mode=mode,
            personalized_share=personalized_share,
            exploration_interval=exploration_interval,
            summary=summary,
            evaluated_at=now,
        )

    def blend(
        self,
        personalized: list[Image],
        fallback: list[Image],
        *,
        evaluation: RecommendationEvaluation,
        limit: int,
    ) -> list[Image]:
        target = max(1, min(limit, 100))
        upstream = _dedupe(personalized)
        exploration = [
            item for item in _dedupe(fallback) if item.id not in {row.id for row in upstream}
        ]
        if not upstream:
            return exploration[:target]

        ranked: list[Image] = []
        interval = max(2, evaluation.exploration_interval)
        while len(ranked) < target and (upstream or exploration):
            position = len(ranked) + 1
            use_exploration = bool(exploration and position % interval == 0)
            if use_exploration or not upstream:
                ranked.append(_take_diverse(exploration, ranked))
            elif upstream:
                ranked.append(upstream.pop(0))
        return ranked


def _select_strategy(
    *,
    exposure_count: int,
    click_through_rate: float,
    feedback_count: int,
    satisfaction_rate: float,
) -> tuple[RecommendationStrategyMode, float, int, str]:
    enough_feedback = feedback_count >= 5
    enough_exposure = exposure_count >= 20
    if not enough_feedback and not enough_exposure:
        return (
            "learning",
            0.67,
            3,
            "样本仍在积累，保留更多跨渠道探索，避免过早固化用户偏好。",
        )
    if (enough_feedback and satisfaction_rate < 0.6) or (
        enough_exposure and click_through_rate < 0.08
    ):
        return (
            "explore",
            0.5,
            2,
            "近期反馈或推荐后操作偏弱，自动提高新素材与跨渠道探索比例。",
        )
    if (
        enough_feedback
        and enough_exposure
        and satisfaction_rate >= 0.8
        and click_through_rate >= 0.15
    ):
        return (
            "personalized",
            0.88,
            8,
            "近期反馈与推荐后操作稳定，自动提高个性化顺序的占比。",
        )
    return (
        "balanced",
        0.75,
        4,
        "个性化与跨渠道探索保持平衡，继续根据新行为和反馈滚动评估。",
    )


def _take_diverse(candidates: list[Image], ranked: list[Image]) -> Image:
    recent_channels = {
        _primary_channel(item.channel) for item in ranked[-3:] if _primary_channel(item.channel)
    }
    for index, candidate in enumerate(candidates):
        channel = _primary_channel(candidate.channel)
        if channel and channel not in recent_channels:
            return candidates.pop(index)
    return candidates.pop(0)


def _primary_channel(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("，", "、").replace(",", "、").replace("/", "、")
    return normalized.split("、", 1)[0].strip()


def _dedupe(images: list[Image]) -> list[Image]:
    seen: set[str] = set()
    result: list[Image] = []
    for image in images:
        if image.id in seen:
            continue
        seen.add(image.id)
        result.append(image)
    return result


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(min(numerator / denominator, 1.0), 4)


def _json_dict(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
