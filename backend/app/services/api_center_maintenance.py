from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Event, Lock, Thread
from typing import Any

from app.core.config import Settings
from app.services.api_center_service import ApiCenterService

logger = logging.getLogger(__name__)


class ApiCenterMaintenanceWorker:
    """Single-backend maintenance loop for API Center health and log retention."""

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
        return self.settings.api_center_maintenance_enabled

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = Thread(
            target=self._run_forever,
            name="api-center-maintenance",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def run_once(self) -> None:
        if not self._lock.acquire(blocking=False):
            return
        try:
            with self.session_factory() as db:
                ApiCenterService(db).run_maintenance_cycle()
        except Exception:
            logger.exception("API Center maintenance cycle failed")
        finally:
            self._lock.release()

    def _run_forever(self) -> None:
        startup_delay = max(
            0,
            int(self.settings.api_center_maintenance_startup_delay_seconds),
        )
        if self._stop.wait(startup_delay):
            return
        while not self._stop.is_set():
            self.run_once()
            interval_seconds = max(
                60,
                int(self.settings.api_center_maintenance_interval_minutes) * 60,
            )
            if self._stop.wait(interval_seconds):
                return
