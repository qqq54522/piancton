from __future__ import annotations

import logging
from typing import BinaryIO

from app.core.errors import AppError
from app.repositories.image_repository import ImageRepository
from app.schemas.reverse_image_search import (
    ReverseImageMatchRead,
    ReverseImageSearchResponse,
)
from app.services.asset_agent_temporary_image_service import (
    AssetAgentTemporaryImageService,
)
from app.services.serializers import image_to_read
from app.services.volc_ai_search_client import (
    VolcAiSearchClient,
    VolcAiSearchClientError,
)

logger = logging.getLogger(__name__)


class ReverseImageSearchService:
    """Search the published gallery by image pixels through Viking AI Search."""

    def __init__(
        self,
        db,
        *,
        client: VolcAiSearchClient,
        temporary_images: AssetAgentTemporaryImageService,
        enabled: bool,
        page_size: int,
    ):
        self.images = ImageRepository(db)
        self.client = client
        self.temporary_images = temporary_images
        self.enabled = enabled
        self.page_size = max(1, min(page_size, 50))

    def search(
        self,
        stream: BinaryIO,
        *,
        owner_id: str,
        filename: str,
        limit: int = 12,
    ) -> ReverseImageSearchResponse:
        if not self.enabled or not self.client.search_configured:
            raise AppError(
                "reverse_image_search_unavailable",
                "以图查图尚未配置 Viking 图片数据集或搜索接口",
                status_code=503,
            )

        temporary = self.temporary_images.create(
            stream,
            owner_id=owner_id,
            filename=filename,
        )
        try:
            image_url = self.temporary_images.public_url_for_owner(
                temporary.token,
                owner_id=owner_id,
            )
            result = self.client.search(
                "",
                image_url=image_url,
                page_size=max(1, min(limit, self.page_size)),
                user_id=owner_id,
            )
        except VolcAiSearchClientError as exc:
            logger.warning("reverse image search failed", exc_info=True)
            raise AppError(
                "reverse_image_search_failed",
                "图片检索暂时不可用，请稍后重试",
                status_code=502,
            ) from exc
        finally:
            self.temporary_images.delete(temporary.token, owner_id=owner_id)

        candidates = _extract_candidates(result.matches)
        images = self.images.get_many_by_ids([item[0] for item in candidates])
        by_id = {image.id: image for image in images}
        matches: list[ReverseImageMatchRead] = []
        for image_id, score in candidates:
            image = by_id.get(image_id)
            if image is None or not image.is_current:
                continue
            if image.asset_group is not None and image.asset_group.publish_status != "published":
                continue
            read = image_to_read(image)
            matches.append(
                ReverseImageMatchRead(
                    image_id=image.id,
                    title=image.title,
                    thumbnail_url=read.thumbnail_url,
                    detail_url=f"/image/{image.id}",
                    score=max(0.0, min(1.0, score)),
                    match_type=(
                        "same_or_transformed" if score >= 0.85 else "visually_similar"
                    ),
                )
            )
        message = (
            f"找到 {len(matches)} 张可能相同或相似的图片"
            if matches
            else "图库中暂未找到相同或相似图片"
        )
        return ReverseImageSearchResponse(
            matches=matches,
            message=message,
        )


def _extract_candidates(matches: list[dict]) -> list[tuple[str, float]]:
    result: list[tuple[str, float]] = []
    seen: set[str] = set()
    for item in matches:
        record = _record_payload(item)
        image_id = str(
            record.get("image_id") or record.get("_id") or record.get("id") or ""
        ).strip()
        if not image_id or image_id in seen:
            continue
        seen.add(image_id)
        raw_score = record.get("score", item.get("score", 0.0))
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        if score > 1:
            score = score / 100
        result.append((image_id, score))
    return result


def _record_payload(item: dict) -> dict:
    for key in ("fields", "field", "item", "doc", "document", "source", "_source"):
        value = item.get(key)
        if isinstance(value, dict):
            merged = dict(value)
            for fallback_key in ("_id", "id", "image_id", "score"):
                if fallback_key in item and fallback_key not in merged:
                    merged[fallback_key] = item[fallback_key]
            return merged
    return item
