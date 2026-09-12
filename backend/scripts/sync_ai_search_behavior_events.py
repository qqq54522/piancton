from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.ai_search_behavior_repository import AiSearchBehaviorRepository
from app.services.ai_search_behavior_sync import (
    AiSearchBehaviorSyncService,
    resolve_ai_search_behavior_api_key,
)
from app.services.volc_ai_search_client import VolcAiSearchClient


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drain Piancton user behavior events into Volcengine AI Search."
    )
    parser.add_argument("--dry-run", action="store_true", help="Only count pending events.")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--max-batches", type=int, default=100)
    args = parser.parse_args()

    settings = get_settings()
    batch_size = max(1, min(args.batch_size, 500))
    with SessionLocal() as db:
        if args.dry_run:
            pending = AiSearchBehaviorRepository(db).list_pending(limit=batch_size)
            print(f"AI Search behavior dry run: pending_in_first_batch={len(pending)}")
            return
        if not (
            settings.ai_search_enabled
            and settings.ai_search_behavior_enabled
            and resolve_ai_search_behavior_api_key(settings)
            and settings.ai_search_behavior_dataset_id
        ):
            raise SystemExit("AI Search behavior sync is not enabled or fully configured.")
        service = AiSearchBehaviorSyncService(
            db,
            VolcAiSearchClient(
                base_url=settings.ai_search_base_url,
                api_key=resolve_ai_search_behavior_api_key(settings),
                dataset_id=settings.ai_search_dataset_id,
                behavior_dataset_id=settings.ai_search_behavior_dataset_id,
                timeout_seconds=settings.ai_search_timeout_seconds,
            ),
            batch_size=batch_size,
        )
        total = 0
        for _ in range(max(1, args.max_batches)):
            synced = service.sync_once()
            if not synced:
                break
            total += synced
            print(f"Synced {total} behavior events")
        print(f"AI Search behavior sync complete: submitted={total}")


if __name__ == "__main__":
    main()
