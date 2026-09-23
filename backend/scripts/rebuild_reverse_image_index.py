from __future__ import annotations

import argparse

from sqlalchemy import and_, desc, or_, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.asset import AssetGroup
from app.models.image import Image
from app.repositories.image_repository import IMAGE_LOAD_OPTIONS
from app.services.storage_factory import build_storage
from app.services.volc_ai_search_client import VolcAiSearchClient
from app.services.volc_ai_search_sync import VolcAiSearchIndexSync


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill published gallery images into the Viking image-search dataset."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    settings = get_settings()
    public_base_url = (
        settings.ai_search_public_base_url
        or settings.public_base_url
        or next(
            (
                origin
                for origin in settings.cors_origin_list
                if origin.startswith(("http://", "https://"))
            ),
            "",
        )
    )
    image_client = VolcAiSearchClient(
        base_url=settings.ai_search_base_url,
        api_key=settings.ai_search_api_key,
        dataset_id=settings.ai_search_image_dataset_id,
        search_path=settings.ai_search_image_search_path,
        timeout_seconds=settings.ai_search_timeout_seconds,
    )
    sync = VolcAiSearchIndexSync(
        VolcAiSearchClient(
            base_url=settings.ai_search_base_url,
            api_key=settings.ai_search_api_key,
            dataset_id=settings.ai_search_dataset_id,
            search_path=settings.ai_search_search_path,
            timeout_seconds=settings.ai_search_timeout_seconds,
        ),
        enabled=False,
        public_base_url=public_base_url,
        image_client=image_client,
        image_enabled=True,
        image_storage=build_storage(settings),
    )

    with SessionLocal() as db:
        stmt = (
            select(Image)
            .outerjoin(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .where(
                Image.deleted_at.is_(None),
                Image.is_current.is_(True),
                or_(
                    Image.asset_group_id.is_(None),
                    and_(AssetGroup.publish_status == "published"),
                ),
            )
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(desc(Image.created_at), desc(Image.id))
        )
        if args.limit > 0:
            stmt = stmt.limit(args.limit)
        images = list(db.scalars(stmt).all())

    if args.dry_run:
        print(
            "Reverse image index dry run: "
            f"eligible_images={len(images)}, "
            f"dataset_id={settings.ai_search_image_dataset_id or '<missing>'}"
        )
        return

    if not image_client.configured:
        raise SystemExit(
            "Viking image dataset is not configured. Set AI_SEARCH_IMAGE_DATASET_ID "
            "and AI_SEARCH_IMAGE_SEARCH_PATH first."
        )

    batch_size = max(1, args.batch_size)
    documents = [sync.reverse_document_for_image(image) for image in images]
    submitted = 0
    for start in range(0, len(documents), batch_size):
        image_client.write_documents(documents[start : start + batch_size])
        submitted += len(documents[start : start + batch_size])
        print(f"Submitted {submitted}/{len(documents)} reverse-image documents")
    print(f"Reverse image index rebuild complete: submitted={submitted}")


if __name__ == "__main__":
    main()
