from __future__ import annotations

import json
import threading
import time
from collections import deque

from app.models.api_provider import ModelApiCredential


class CredentialCapacityTracker:
    """Process-local capacity and short-window runtime health ledger."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._in_flight: dict[str, int] = {}
        self._recent: dict[str, deque[tuple[float, str, int]]] = {}

    def try_acquire(self, credential_id: str, max_concurrency: int) -> bool:
        limit = max(1, max_concurrency)
        with self._lock:
            current = self._in_flight.get(credential_id, 0)
            if current >= limit:
                return False
            self._in_flight[credential_id] = current + 1
            return True

    def release(self, credential_id: str) -> None:
        with self._lock:
            current = self._in_flight.get(credential_id, 0)
            if current <= 1:
                self._in_flight.pop(credential_id, None)
            else:
                self._in_flight[credential_id] = current - 1

    def record(self, credential_id: str, *, status: str, duration_ms: int) -> None:
        now = time.monotonic()
        with self._lock:
            calls = self._recent.setdefault(credential_id, deque(maxlen=200))
            calls.append((now, status, max(0, duration_ms)))
            self._trim_locked(calls, now)

    def snapshot(
        self,
        credential_ids: list[str],
        *,
        max_age_seconds: float = 300.0,
    ) -> dict[str, dict[str, float]]:
        now = time.monotonic()
        with self._lock:
            snapshots: dict[str, dict[str, float]] = {}
            for credential_id in credential_ids:
                calls = self._recent.setdefault(credential_id, deque(maxlen=200))
                self._trim_locked(calls, now, max_age_seconds=max_age_seconds)
                total = len(calls)
                failed = sum(1 for _, status, _ in calls if status != "ok")
                latency_total = sum(duration_ms for _, _, duration_ms in calls)
                snapshots[credential_id] = {
                    "in_flight": float(self._in_flight.get(credential_id, 0)),
                    "runtime_total": float(total),
                    "runtime_failed": float(failed),
                    "runtime_failure_rate": failed / total if total else 0.0,
                    "runtime_avg_latency": latency_total / total if total else 0.0,
                }
            return snapshots

    def reset_for_tests(self) -> None:
        with self._lock:
            self._in_flight.clear()
            self._recent.clear()

    def _trim_locked(
        self,
        calls: deque[tuple[float, str, int]],
        now: float,
        *,
        max_age_seconds: float = 300.0,
    ) -> None:
        cutoff = now - max_age_seconds
        while calls and calls[0][0] < cutoff:
            calls.popleft()


_CAPACITY_TRACKER = CredentialCapacityTracker()


def normalize_max_concurrency(value: int | None) -> int:
    return min(max(1, int(value or 1)), 20)


def credential_can_run_task(
    credential: ModelApiCredential,
    task: str,
    *,
    require_auto_assign: bool = True,
) -> bool:
    if credential.status != "active":
        return False
    if require_auto_assign and not credential.auto_assign_enabled:
        return False
    scopes = _loads_list(credential.task_scope_json)
    return not scopes or task in scopes


def credential_schedule_key(
    credential: ModelApiCredential,
    metrics: dict[str, dict[str, float]],
    runtime: dict[str, dict[str, float]],
) -> tuple[int, int, float, float, float, int, float, int, str]:
    health_rank = {
        "ok": 0,
        None: 1,
        "failed": 2,
        "timed_out": 2,
    }.get(credential.last_status, 1)
    metric = metrics.get(credential.id, {})
    runtime_metric = runtime.get(credential.id, {})
    total = int(metric.get("total", 0))
    ok = metric.get("ok", 0.0)
    failed = int(metric.get("failed", 0))
    runtime_failure_rate = runtime_metric.get("runtime_failure_rate", 0.0)
    avg_latency = metric.get(
        "avg_latency",
        float(
            credential.last_latency_ms
            if credential.last_latency_ms is not None
            else 999_999
        ),
    )
    success_rate = ok / total if total else (
        1.0 if credential.last_status == "ok" else 0.5
    )
    max_concurrency = normalize_max_concurrency(credential.max_concurrency)
    in_flight = runtime_metric.get("in_flight", 0.0)
    load_ratio = in_flight / max_concurrency
    saturated_rank = 1 if in_flight >= max_concurrency else 0
    return (
        saturated_rank,
        health_rank,
        -success_rate,
        runtime_failure_rate,
        load_ratio,
        failed,
        avg_latency,
        credential.priority,
        credential.created_at.isoformat(),
    )


def _loads_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
