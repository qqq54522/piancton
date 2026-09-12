from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Any

from app.core.config import Settings
from app.repositories.ai_search_behavior_repository import AiSearchBehaviorRepository
from app.services.unit_of_work import UnitOfWork
from app.services.volc_ai_search_client import VolcAiSearchClient, VolcAiSearchClientError

logger = logging.getLogger(__name__)


def resolve_ai_search_behavior_api_key(settings: Settings) -> str:
    """Prefer the dataset-scoped realtime key without breaking old deployments."""
    return settings.ai_search_behavior_api_key.strip() or settings.ai_search_api_key.strip()


class AiSearchBehaviorSyncService:
    def __init__(
        self,
        db: Any,
        client: VolcAiSearchClient,
        *,
        batch_size: int = 100,
    ) -> None:
        self.events = AiSearchBehaviorRepository(db)
        self.client = client
        self.batch_size = max(1, min(batch_size, 500))
        self.uow = UnitOfWork(db)

    def sync_once(self) -> int:
        pending = self.events.list_pending(limit=self.batch_size)
        if not pending:
            return 0
        documents = [
            {
                "event_id": event.id,
                "user_id": event.user_id,
                "item_id": event.item_id,
                "event_type": event.event_type,
                "event_timestamp": event.event_timestamp,
                "event_scene": event.event_scene,
                **_safe_details(event.details_json),
            }
            for event in pending
        ]
        try:
            self.client.write_behavior_events(documents)
        except VolcAiSearchClientError as exc:
            self.events.mark_failed(pending, error=str(exc))
            self.uow.commit()
            raise
        self.events.mark_synced(pending, synced_at=datetime.now(timezone.utc))
        self.uow.commit()
        return len(pending)


class AiSearchBehaviorWorker:
    """Single-backend outbox drain loop for Viking AI Search user events."""

    def __init__(
        self,
        session_factory: Callable[[], Any],
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self._stop = Event()
        self._lock = Lock()
        self._thread: Thread | None = None

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.ai_search_enabled
            and self.settings.ai_search_behavior_enabled
            and resolve_ai_search_behavior_api_key(self.settings)
            and self.settings.ai_search_behavior_dataset_id
        )

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = Thread(
            target=self._run_forever,
            name="ai-search-behavior-sync",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def run_once(self) -> int:
        if not self.enabled or not self._lock.acquire(blocking=False):
            return 0
        try:
            with self.session_factory() as db:
                return AiSearchBehaviorSyncService(
                    db,
                    VolcAiSearchClient(
                        base_url=self.settings.ai_search_base_url,
                        api_key=resolve_ai_search_behavior_api_key(self.settings),
                        dataset_id=self.settings.ai_search_dataset_id,
                        behavior_dataset_id=self.settings.ai_search_behavior_dataset_id,
                        timeout_seconds=self.settings.ai_search_timeout_seconds,
                    ),
                    batch_size=self.settings.ai_search_behavior_sync_batch_size,
                ).sync_once()
        except Exception:
            logger.exception("AI Search behavior sync cycle failed")
            return 0
        finally:
            self._lock.release()

    def _run_forever(self) -> None:
        startup_delay = max(
            0,
            int(self.settings.ai_search_behavior_sync_startup_delay_seconds),
        )
        if self._stop.wait(startup_delay):
            return
        while not self._stop.is_set():
            self.run_once()
            if self._stop.wait(
                max(5, int(self.settings.ai_search_behavior_sync_interval_seconds))
            ):
                return


def _safe_details(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    allowed = {"source_action", "search_log_id", "conversation_id", "position"}
    return {key: value for key, value in payload.items() if key in allowed and value is not None}
