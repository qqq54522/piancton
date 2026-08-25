from __future__ import annotations

from app.models.asset import AssetGroup
from app.models.image import Image
from app.schemas.asset import (
    AssetConceptLinkRead,
    AssetGroupRead,
    AssetImageRead,
    AssetSearchPhraseRead,
    AssetSourceLinkRead,
)


def asset_image_to_read(image: Image) -> AssetImageRead:
    return AssetImageRead(
        id=image.id,
        asset_code=image.asset_group.asset_code if image.asset_group else None,
        version_code=image.version_code,
        share_path=f"/share/{image.version_code}" if image.version_code else None,
        title=image.title,
        file_name=image.file_name,
        thumbnail_url=f"/api/images/{image.id}/thumbnail",
        content_url=f"/api/images/{image.id}/content",
        download_url=f"/api/images/{image.id}/download",
        media_type=image.media_type,
        asset_role=image.asset_role,
        width=image.width,
        height=image.height,
        aspect_ratio=image.aspect_ratio,
        channel=image.channel,
        version_no=image.version_no,
        is_current=image.is_current,
    )


def asset_group_to_read(
    group: AssetGroup,
    *,
    include_source_links: bool = False,
) -> AssetGroupRead:
    manually_confirmed_ids = {
        item.concept_id
        for item in group.concept_links
        if item.origin == "manual" and item.review_status == "accepted"
    }
    visible_concept_links = [
        item
        for item in group.concept_links
        if not (
            item.origin == "ai"
            and item.review_status == "pending"
            and item.concept_id in manually_confirmed_ids
        )
    ]
    return AssetGroupRead(
        id=group.id,
        asset_code=group.asset_code,
        share_path=f"/share/{group.asset_code}" if group.asset_code else None,
        title=group.title,
        primary_image_id=group.primary_image_id,
        approval_status=group.approval_status,
        publish_status=group.publish_status,
        style_label=group.style_label,
        is_scene_image=group.is_scene_image,
        primary_proof_point_code=group.primary_proof_point_code,
        primary_evidence_point_code=group.primary_evidence_point_code,
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
            for item in visible_concept_links
        ],
        search_phrases=[
            AssetSearchPhraseRead.model_validate(item) for item in group.search_phrases
        ],
        source_links=[
            AssetSourceLinkRead.model_validate(item)
            for item in sorted(group.source_links, key=lambda item: item.created_at)
        ] if include_source_links else [],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )
