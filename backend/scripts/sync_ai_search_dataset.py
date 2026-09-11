from __future__ import annotations

import argparse

from sqlalchemy import and_, desc, or_, select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.asset import AssetGroup
from app.models.image import Image
from app.repositories.image_repository import IMAGE_LOAD_OPTIONS
from app.services.volc_ai_search_client import VolcAiSearchClient
from app.services.volc_ai_search_sync import VolcAiSearchIndexSync


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill published Piancton images into Volcengine AI Search."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count and build documents; do not write to AI Search.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of images to sync. 0 means all eligible images.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of image documents per AI Search write request.",
    )
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
    sync = VolcAiSearchIndexSync(
        VolcAiSearchClient(
            base_url=settings.ai_search_base_url,
            api_key=settings.ai_search_api_key,
            dataset_id=settings.ai_search_dataset_id,
            search_path=settings.ai_search_search_path,
            timeout_seconds=settings.ai_search_timeout_seconds,
        ),
        enabled=settings.ai_search_enabled and settings.ai_search_sync_enabled,
        public_base_url=public_base_url,
    )
    batch_size = max(1, args.batch_size)
    with SessionLocal() as db:
        stmt = (
            select(Image)
            .outerjoin(AssetGroup, AssetGroup.id == Image.asset_group_id)
            .where(
                Image.deleted_at.is_(None),
                or_(
                    Image.asset_group_id.is_(None),
                    and_(
                        AssetGroup.publish_status == "published",
                        Image.is_current.is_(True),
                    ),
                ),
            )
            .options(*IMAGE_LOAD_OPTIONS)
            .order_by(desc(Image.created_at), desc(Image.id))
        )
        if args.limit and args.limit > 0:
            stmt = stmt.limit(args.limit)
        images = list(db.scalars(stmt).all())

    documents = [sync.document_for_image(image) for image in images]
    if args.dry_run:
        print(
            "AI Search dry run: "
            f"eligible_images={len(images)}, documents={len(documents)}, "
            f"public_base_url={public_base_url or '<relative>'}"
        )
        return

    if not sync.enabled:
        raise SystemExit("AI Search sync is not enabled or not fully configured.")
    submitted = 0
    for start in range(0, len(documents), batch_size):
        sync.client.write_documents(documents[start : start + batch_size])
        submitted += len(documents[start : start + batch_size])
        print(f"Submitted {submitted}/{len(documents)} documents")
    print(f"AI Search backfill complete: submitted={submitted}")


if __name__ == "__main__":
    main()
