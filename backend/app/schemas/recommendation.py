from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.image import ImageRead

RecommendationStrategyMode = Literal[
    "learning",
    "balanced",
    "personalized",
    "explore",
]


class RecommendationEvaluationRead(ApiModel):
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


class ForYouImageListResponse(ApiModel):
    items: list[ImageRead] = Field(default_factory=list)
    source: Literal["ai_search", "local_fallback"]
    evaluation: RecommendationEvaluationRead
