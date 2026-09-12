from __future__ import annotations

import logging
from typing import Literal

from app.repositories.image_repository import ImageRepository
from app.schemas.recommendation import ForYouImageListResponse
from app.services.recommendation_strategy_service import RecommendationStrategyService
from app.services.serializers import image_to_read
from app.services.volc_ai_search_client import (
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

logger = logging.getLogger(__name__)


class HomeRecommendationService:
    """Build the business homepage feed across every published channel."""

    def __init__(
        self,
        db,
        *,
        ai_search_client: VolcAiSearchClient | None,
        enabled: bool,
    ):
        self.images = ImageRepository(db)
        self.strategy = RecommendationStrategyService(db)
        self.ai_search_client = ai_search_client
        self.enabled = enabled

    def for_user(self, *, user_id: str, limit: int = 48) -> ForYouImageListResponse:
        target = max(1, min(limit, 100))
        evaluation = self.strategy.evaluate(user_id=user_id)
        fallback = self.images.list_published_current(limit=max(target * 4, 100))
        personalized = []
        source: Literal["ai_search", "local_fallback"] = "local_fallback"
        client = self.ai_search_client
        if self.enabled and client is not None and client.recommend_configured:
            try:
                image_ids = client.recommend_items(
                    user_id=user_id,
                    page_size=max(target * 3, 48),
                )
                personalized = self.images.get_many_by_ids(image_ids)
                source = "ai_search" if personalized else "local_fallback"
            except VolcAiSearchClientError:
                logger.warning("AI Search homepage recommendation failed", exc_info=True)
        ranked = self.strategy.blend(
            personalized,
            fallback,
            evaluation=evaluation,
            limit=target,
        )
        return ForYouImageListResponse(
            items=[image_to_read(image) for image in ranked],
            source=source,
            evaluation=evaluation.to_read(),
        )
