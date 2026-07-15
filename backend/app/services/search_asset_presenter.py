from __future__ import annotations

from dataclasses import dataclass

from app.models.image import Image
from app.schemas.asset import AssetImageRead
from app.services.asset_serializers import asset_image_to_read


@dataclass(frozen=True)
class SearchAssetPresentation:
    group_id: str | None
    title: str
    variants: tuple[AssetImageRead, ...]
    expressed_concepts: tuple[str, ...]
    supported_concepts: tuple[str, ...]


class SearchAssetPresenter:
    """Builds business-facing asset metadata from already-loaded relationships."""

    def present(self, image: Image) -> SearchAssetPresentation:
        group = image.asset_group
        if group is None:
            return SearchAssetPresentation(
                group_id=image.asset_group_id,
                title=image.title,
                variants=(asset_image_to_read(image),),
                expressed_concepts=(),
                supported_concepts=(),
            )
        accepted_links = [
            item
            for item in group.concept_links
            if item.review_status == "accepted" and item.relation_role != "excludes"
        ]
        variants = tuple(
            asset_image_to_read(item)
            for item in sorted(
                (item for item in group.images if item.deleted_at is None and item.is_current),
                key=lambda item: (
                    item.id != group.primary_image_id,
                    item.version_no,
                    item.id,
                ),
            )
        )
        return SearchAssetPresentation(
            group_id=group.id,
            title=group.title,
            variants=variants or (asset_image_to_read(image),),
            expressed_concepts=_concept_names(accepted_links, "expresses"),
            supported_concepts=_concept_names(accepted_links, "supports"),
        )


def _concept_names(links, role: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.concept.name for item in links if item.relation_role == role))
