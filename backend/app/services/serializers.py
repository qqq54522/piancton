from datetime import datetime, timezone
from typing import Literal, cast

from app.models.image import Image
from app.schemas.image import (
    AnalysisRunRead,
    ContentTagRead,
    ImageDetailRead,
    ImageRead,
    SemanticProfileRead,
)
from app.schemas.tag import TagRead
from app.services.image_semantic_profile_service import ImageSemanticProfileService

AnalysisRunStatus = Literal["queued", "running", "succeeded", "failed"]
VALID_ANALYSIS_RUN_STATUSES: set[AnalysisRunStatus] = {
    "queued",
    "running",
    "succeeded",
    "failed",
}


def tag_to_read(tag, image_count: int = 0) -> TagRead:
    return TagRead(
        id=tag.id,
        code=tag.code,
        name=tag.name,
        color=tag.color,
        parent_id=tag.parent_id,
        parent_name=tag.parent.name if tag.parent else None,
        is_secondary=tag.is_secondary,
        node_type=tag.node_type,
        assignable=tag.assignable,
        status=tag.status,
        taxonomy_version=tag.taxonomy_version,
        sort_order=tag.sort_order,
        image_count=image_count,
    )


def image_to_read(image: Image) -> ImageRead:
    return ImageRead(
        id=image.id,
        title=image.title,
        file_name=image.file_name,
        content_url=f"/api/images/{image.id}/content",
        thumbnail_url=f"/api/images/{image.id}/thumbnail",
        download_url=f"/api/images/{image.id}/download",
        media_type=image.media_type,
        size_bytes=image.size_bytes,
        uploader=image.uploader,
        download_count=image.download_count,
        created_at=image.created_at,
        deleted_at=image.deleted_at,
        asset_group_id=image.asset_group_id,
        asset_role=image.asset_role,
        width=image.width,
        height=image.height,
        aspect_ratio=image.aspect_ratio,
        channel=image.channel,
        version_no=image.version_no,
        is_current=image.is_current,
        variant_count=(
            len(
                [
                    item
                    for item in image.asset_group.images
                    if item.is_current and item.deleted_at is None
                ]
            )
            if image.asset_group
            else 1
        ),
    )


def analysis_run_sort_key(run) -> datetime:
    created_at = run.created_at
    if created_at is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at


def analysis_run_status(value: str) -> AnalysisRunStatus:
    if value in VALID_ANALYSIS_RUN_STATUSES:
        return cast(AnalysisRunStatus, value)
    return "failed"


def image_to_detail(image: Image, related: list[Image]) -> ImageDetailRead:
    semantic_profile = ImageSemanticProfileService().profile_from_image(image)
    return ImageDetailRead(
        **image_to_read(image).model_dump(),
        image_summary=image.image_summary,
        semantic_profile=(
            SemanticProfileRead(
                **semantic_profile.model_dump(),
            )
            if semantic_profile
            else None
        ),
        related_images=[image_to_read(item) for item in related],
        content_tags=[
            ContentTagRead(
                id=item.id,
                tag_name=item.tag_name,
                confidence=item.confidence,
                dimension=item.dimension,
            )
            for item in image.content_tags
        ],
        analysis_runs=[
            AnalysisRunRead(
                id=item.id,
                task=item.task,
                status=analysis_run_status(item.status),
                taxonomy_version=item.taxonomy_version,
                model_provider=item.model_provider,
                model_name=item.model_name,
                created_at=item.created_at,
            )
            for item in sorted(
                image.analysis_runs,
                key=analysis_run_sort_key,
                reverse=True,
            )[:5]
        ],
    )
