from __future__ import annotations

from app.models.asset import AssetGroup
from app.models.image import Image
from app.schemas.asset import (
    AssetConceptLinkRead,
    AssetGroupRead,
    AssetImageRead,
    AssetSearchPhraseRead,
)


def asset_image_to_read(image: Image) -> AssetImageRead:
    return AssetImageRead(
        id=image.id,
        title=image.title,
        file_name=image.file_name,
        thumbnail_url=f"/api/images/{image.id}/thumbnail",
        content_url=f"/api/images/{image.id}/content",
        download_url=f"/api/images/{image.id}/download",
        asset_role=image.asset_role,
        width=image.width,
        height=image.height,
        aspect_ratio=image.aspect_ratio,
        channel=image.channel,
        version_no=image.version_no,
        is_current=image.is_current,
    )


def asset_group_to_read(group: AssetGroup) -> AssetGroupRead:
    return AssetGroupRead(
        id=group.id,
        title=group.title,
        primary_image_id=group.primary_image_id,
        approval_status=group.approval_status,
        publish_status=group.publish_status,
        created_by=group.created_by,
        images=[
            asset_image_to_read(image)
            for image in sorted(
                (item for item in group.images if item.deleted_at is None),
                key=lambda item: (item.version_no, item.created_at),
            )
        ],
        concept_links=[
            AssetConceptLinkRead(
                id=item.id,
                concept_id=item.concept_id,
                concept_code=item.concept.code,
                concept_name=item.concept.name,
                relation_role=item.relation_role,
                origin=item.origin,
                review_status=item.review_status,
                confidence=item.confidence,
                evidence_reason=item.evidence_reason,
                source_ref=item.source_ref,
            )
            for item in group.concept_links
        ],
        search_phrases=[
            AssetSearchPhraseRead.model_validate(item) for item in group.search_phrases
        ],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )
