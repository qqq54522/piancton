from __future__ import annotations

import json
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, cast

from app.ai.contracts import (
    ModelProvider,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.fallback import _format_attempts
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models.api_provider import (
    ModelApiCredential,
    ModelApiHealthCheck,
    ModelCallTrace,
    ModelRoutingSlot,
)
from app.repositories.api_center_repository import ApiCenterRepository
from app.schemas.api_center import (
    ApiCallTraceRead,
    ApiCenterOverview,
    ApiCenterSummary,
    ApiCredentialCreate,
    ApiCredentialRead,
    ApiCredentialUpdate,
    ApiHealthCheckCreate,
    ApiHealthCheckRead,
    ApiHealthCheckRunRequest,
    ApiHealthCheckRunResult,
    ModelTaskName,
    RoutingSlotRead,
    RoutingSlotUpdate,
)
from app.services.unit_of_work import UnitOfWork

DEFAULT_ROUTING_SLOTS: tuple[tuple[str, str, float, int], ...] = (
    ("search_system_routing", "第一层：体系路由", 15.0, 2500),
    ("search_intent_understanding", "第二层：卖点识别", 25.0, 3500),
    ("search_proof_point_understanding", "第三层：证明点识别", 20.0, 3500),
    ("search_candidate_review", "第四层：候选图片复核", 20.0, 3500),
    ("search_result_recommendation_reason", "搜索结果：动态推荐理由", 20.0, 3000),
    ("image_content_analysis", "上传主图：图片语义分析", 60.0, 5000),
    ("asset_search_phrase_generation", "上传前：素材话术生成", 30.0, 3500),
    ("copy_selling_point_matching", "兼容接口：文案卖点匹配", 20.0, 3000),
    ("asset_agent_chat", "素材库 Agent：业务解释", 30.0, 3500),
)
VALID_MODEL_TASKS = {item[0] for item in DEFAULT_ROUTING_SLOTS}

SEARCH_TASKS = (
    "search_system_routing",
    "search_intent_understanding",
    "search_proof_point_understanding",
    "search_candidate_review",
)

TASK_LAYER_LABELS = {
    task: label for task, label, _, _ in DEFAULT_ROUTING_SLOTS
}

ENV_CREDENTIAL_SPECS: tuple[dict[str, Any], ...] = (
    {
        "label": "环境导入 · 搜索主 Key",
        "api_key": "model_api_key",
        "base_url": "model_base_url",
        "model_name": "model_name",
        "temperature": "model_temperature",
        "priority": 10,
        "tasks": SEARCH_TASKS,
    },
    {
        "label": "环境导入 · 搜索备用 Key",
        "api_key": "search_fallback_api_key",
        "base_url": "search_fallback_base_url",
        "model_name": "search_fallback_model_name",
        "temperature": "search_fallback_temperature",
        "priority": 20,
        "tasks": SEARCH_TASKS,
    },
    {
        "label": "环境导入 · 主图分析 Key",
        "api_key": "image_analysis_api_key",
        "base_url": "image_analysis_base_url",
        "model_name": "image_analysis_model_name",
        "temperature": "image_analysis_temperature",
        "priority": 30,
        "tasks": ("image_content_analysis",),
    },
    {
        "label": "环境导入 · 话术生成 Key",
        "api_key": "asset_phrase_api_key",
        "base_url": "asset_phrase_base_url",
        "model_name": "asset_phrase_model_name",
        "temperature": "asset_phrase_temperature",
        "priority": 40,
        "tasks": (
            "asset_search_phrase_generation",
            "asset_agent_chat",
            "search_result_recommendation_reason",
        ),
    },
)


class CredentialCapacityTracker:
    """Process-local capacity ledger for API Center runtime scheduling.

    The database stores stable capacity configuration. This tracker keeps only
    short-lived runtime facts: in-flight calls and the last few minutes of
    success/latency signals. It is intentionally provider-neutral and never
    sees API keys or prompts.
    """

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


class ApiCenterService:
    def __init__(
        self,
        db,
        *,
        trace_session_factory: Callable[[], Any] | None = None,
    ):
        self.db = db
        self.repo = ApiCenterRepository(db)
        self.uow = UnitOfWork(db)
        self.trace_session_factory = trace_session_factory

    def summary(self) -> ApiCenterSummary:
        self.ensure_default_slots()
        self.sync_environment_credentials()
        credentials = self.repo.list_credentials()
        slots = self.repo.list_slots()
        recent_checks = self.repo.list_recent_health_checks(limit=50)
        recent_traces = self.repo.list_recent_call_traces(limit=100)
        recent_day_traces = self.repo.list_call_traces_since(hours=24, limit=2000)
        schedule_metrics = _build_schedule_metrics(
            recent_day_traces,
            self.repo.list_recent_health_checks(limit=5000),
        )
        durations = sorted(item.duration_ms for item in recent_day_traces)
        return ApiCenterSummary(
            overview=ApiCenterOverview(
                credential_count=len(credentials),
                active_credential_count=sum(1 for item in credentials if item.status == "active"),
                healthy_credential_count=sum(1 for item in credentials if item.last_status == "ok"),
                degraded_credential_count=sum(
                    1
                    for item in credentials
                    if item.status in {"cooling", "invalid"}
                    or item.last_status in {"failed", "timed_out"}
                ),
                configured_slot_count=sum(
                    1
                    for item in slots
                    if item.auto_select_enabled
                    or item.primary_credential_id
                    or _loads_list(item.backup_credential_ids_json)
                ),
                recent_call_count=len(recent_day_traces),
                recent_failure_count=sum(
                    1 for item in recent_day_traces if item.status in {"failed", "timed_out"}
                ),
                p95_latency_ms=_percentile(durations, 0.95),
            ),
            credentials=[
                self._credential_read(item, schedule_metrics.get(item.id))
                for item in credentials
            ],
            routing_slots=[self._slot_read(item, credentials) for item in slots],
            recent_health_checks=[
                self._health_check_read(item, credentials) for item in recent_checks
            ],
            recent_call_traces=[self._call_trace_read(item) for item in recent_traces],
        )

    def ensure_default_slots(self) -> None:
        changed = False
        for task, label, timeout_seconds, hedging_delay_ms in DEFAULT_ROUTING_SLOTS:
            slot = self.repo.get_slot_by_task(task)
            if slot:
                has_manual_routing = bool(
                    slot.primary_credential_id
                    or _loads_list(slot.backup_credential_ids_json)
                )
                if not slot.auto_select_enabled and not has_manual_routing:
                    slot.auto_select_enabled = True
                    slot.max_parallel = max(slot.max_parallel, 4 if task in SEARCH_TASKS else 2)
                    changed = True
                continue
            self.repo.add_slot(
                ModelRoutingSlot(
                    task=task,
                    label=label,
                    timeout_seconds=timeout_seconds,
                    hedging_delay_ms=hedging_delay_ms,
                    max_parallel=4 if task in SEARCH_TASKS else 2,
                    auto_select_enabled=True,
                    backup_credential_ids_json="[]",
                )
            )
            changed = True
        if changed:
            self.uow.commit()

    def sync_environment_credentials(self) -> None:
        settings = get_settings()
        changed = False
        for spec in ENV_CREDENTIAL_SPECS:
            api_key = str(getattr(settings, spec["api_key"], "") or "").strip()
            if not api_key:
                continue
            base_url = str(
                getattr(settings, spec["base_url"], "") or settings.model_base_url or ""
            ).strip()
            model_name = str(
                getattr(settings, spec["model_name"], "") or settings.model_name or ""
            ).strip()
            if not base_url or not model_name:
                continue
            label = str(spec["label"])
            credential = self.repo.get_credential_by_label(label)
            if not credential:
                credential = self.repo.add_credential(
                    ModelApiCredential(
                        label=label,
                        provider_type="openai_compatible",
                        base_url=_bounded(base_url, 500).rstrip("/"),
                        model_name=_bounded(model_name, 120),
                        api_key_secret=api_key,
                        api_key_preview=_api_key_preview(api_key),
                        task_scope_json=json.dumps(spec["tasks"], ensure_ascii=False),
                        status="active",
                        priority=int(spec["priority"]),
                        timeout_seconds=20.0,
                        temperature=float(getattr(settings, spec["temperature"], 0.2) or 0.2),
                        max_concurrency=1,
                        auto_assign_enabled=True,
                    )
                )
                changed = True
                continue
            updates = {
                "base_url": _bounded(base_url, 500).rstrip("/"),
                "model_name": _bounded(model_name, 120),
                "api_key_secret": api_key,
                "api_key_preview": _api_key_preview(api_key),
                "task_scope_json": json.dumps(spec["tasks"], ensure_ascii=False),
                "priority": min(credential.priority, int(spec["priority"])),
                "auto_assign_enabled": True,
            }
            credential_changed = False
            for field, value in updates.items():
                if getattr(credential, field) != value:
                    setattr(credential, field, value)
                    credential_changed = True
            if credential_changed:
                credential.updated_at = datetime.now(timezone.utc)
                changed = True
        if changed:
            self.uow.commit()

    def build_scheduled_provider(
        self,
        *,
        fallback_provider: ModelProvider,
    ) -> ModelProvider:
        self.ensure_default_slots()
        self.sync_environment_credentials()
        return ApiCenterScheduledModelProvider(self, fallback_provider)

    def select_credentials_for_task(
        self,
        task: str,
    ) -> tuple[ModelRoutingSlot | None, list[ModelApiCredential]]:
        self.ensure_default_slots()
        slot = self.repo.get_slot_by_task(task)
        credentials = self.repo.list_credentials()
        by_id = {item.id: item for item in credentials}
        selected: list[ModelApiCredential] = []
        if slot and not slot.auto_select_enabled:
            configured_backup_ids = _loads_list(slot.backup_credential_ids_json)
            manual_ids = [
                item
                for item in [slot.primary_credential_id, *configured_backup_ids]
                if item
            ]
            for credential_id in manual_ids:
                credential = by_id.get(credential_id)
                if credential and _credential_can_run_task(credential, task):
                    selected.append(credential)
            return slot, selected

        candidates = [
            item
            for item in self.repo.list_auto_assign_credentials()
            if _credential_can_run_task(item, task)
        ]
        metrics = _build_schedule_metrics(
            self.repo.list_call_traces_since(hours=24, limit=5000),
            self.repo.list_recent_health_checks(limit=5000),
        )
        runtime = _CAPACITY_TRACKER.snapshot([item.id for item in candidates])
        selected = sorted(
            candidates,
            key=lambda credential: _credential_schedule_key(
                credential,
                metrics,
                runtime,
            ),
        )
        limit = max(1, min(slot.max_parallel if slot else 4, 4))
        return slot, selected[:limit]

    def record_runtime_attempt(
        self,
        credential_id: str,
        *,
        status: str,
        duration_ms: int,
        error_summary: str | None,
    ) -> None:
        if self.trace_session_factory is not None:
            with self.trace_session_factory() as runtime_db:
                ApiCenterService(runtime_db).record_runtime_attempt(
                    credential_id,
                    status=status,
                    duration_ms=duration_ms,
                    error_summary=error_summary,
                )
            return
        credential = self.repo.get_credential(credential_id)
        if not credential:
            return
        credential.last_status = status
        credential.last_latency_ms = duration_ms
        credential.last_error = error_summary
        credential.last_checked_at = datetime.now(timezone.utc)
        _CAPACITY_TRACKER.record(credential_id, status=status, duration_ms=duration_ms)
        if status == "ok" and credential.status in {"cooling", "invalid"}:
            credential.status = "active"
        elif status != "ok" and credential.status == "active":
            credential.status = "cooling"
        credential.updated_at = datetime.now(timezone.utc)
        self.db.flush()

    def create_credential(
        self,
        payload: ApiCredentialCreate,
        *,
        actor_user_id: str | None,
    ) -> ApiCredentialRead:
        api_key = payload.api_key.strip()
        if not api_key:
            raise AppError("api_key_required", "API key 不能为空")
        credential = self.repo.add_credential(
            ModelApiCredential(
                label=_bounded(payload.label, 120),
                provider_type=_bounded(payload.provider_type, 40),
                base_url=_bounded(payload.base_url, 500).rstrip("/"),
                model_name=_bounded(payload.model_name, 120),
                api_key_secret=api_key,
                api_key_preview=_api_key_preview(api_key),
                task_scope_json=json.dumps(payload.task_scope, ensure_ascii=False),
                status=payload.status,
                priority=payload.priority,
                timeout_seconds=max(0.5, payload.timeout_seconds),
                temperature=payload.temperature,
                max_concurrency=_normalize_max_concurrency(payload.max_concurrency),
                auto_assign_enabled=payload.auto_assign_enabled,
                created_by=actor_user_id,
            )
        )
        self.uow.commit()
        return self._credential_read(credential)

    def record_external_call(
        self,
        *,
        task: str,
        layer_name: str,
        provider: str,
        model: str,
        status: str,
        duration_ms: int,
        error_summary: str | None = None,
        credential_label: str | None = None,
        request_id: str | None = None,
    ) -> None:
        """Persist telemetry for non-chat external APIs.

        Search enhancement providers and index services do not use the model
        scheduler, but they still belong in the same operational ledger.
        """

        if self.trace_session_factory is not None:
            with self.trace_session_factory() as trace_db:
                ApiCenterService(trace_db).record_external_call(
                    task=task,
                    layer_name=layer_name,
                    provider=provider,
                    model=model,
                    status=status,
                    duration_ms=duration_ms,
                    error_summary=error_summary,
                    credential_label=credential_label,
                    request_id=request_id,
                )
            return

        self.repo.add_call_trace(
            ModelCallTrace(
                request_id=request_id,
                task=_bounded(task, 80),
                layer_name=_bounded(layer_name, 120),
                credential_label=_bounded(credential_label or "", 120) or None,
                provider=_bounded(provider, 120) or "unknown",
                model=_bounded(model, 120) or "unknown",
                status=_bounded(status, 24) or "unknown",
                duration_ms=max(0, int(duration_ms)),
                error_summary=_bounded(error_summary or "", 300) or None,
                response_valid=status == "ok",
                output_summary_json=json.dumps(
                    {"kind": "external_api"},
                    ensure_ascii=False,
                ),
            )
        )
        self.uow.commit()

    def update_credential(
        self,
        credential_id: str,
        payload: ApiCredentialUpdate,
    ) -> ApiCredentialRead:
        credential = self.repo.get_credential(credential_id)
        if not credential:
            raise NotFoundError("api_credential_not_found", "API key 不存在")
        if payload.label is not None:
            credential.label = _bounded(payload.label, 120)
        if payload.provider_type is not None:
            credential.provider_type = _bounded(payload.provider_type, 40)
        if payload.base_url is not None:
            credential.base_url = _bounded(payload.base_url, 500).rstrip("/")
        if payload.model_name is not None:
            credential.model_name = _bounded(payload.model_name, 120)
        if payload.api_key is not None and payload.api_key.strip():
            api_key = payload.api_key.strip()
            credential.api_key_secret = api_key
            credential.api_key_preview = _api_key_preview(api_key)
        if payload.task_scope is not None:
            credential.task_scope_json = json.dumps(payload.task_scope, ensure_ascii=False)
        if payload.status is not None:
            credential.status = payload.status
        if payload.priority is not None:
            credential.priority = payload.priority
        if payload.timeout_seconds is not None:
            credential.timeout_seconds = max(0.5, payload.timeout_seconds)
        if payload.temperature is not None:
            credential.temperature = payload.temperature
        if payload.max_concurrency is not None:
            credential.max_concurrency = _normalize_max_concurrency(payload.max_concurrency)
        if payload.auto_assign_enabled is not None:
            credential.auto_assign_enabled = payload.auto_assign_enabled
        credential.updated_at = datetime.now(timezone.utc)
        self.uow.commit()
        return self._credential_read(credential)

    def update_slot(
        self,
        task: str,
        payload: RoutingSlotUpdate,
        *,
        actor_user_id: str | None,
    ) -> RoutingSlotRead:
        self.ensure_default_slots()
        slot = self.repo.get_slot_by_task(task)
        if not slot:
            raise NotFoundError("routing_slot_not_found", "调用槽位不存在")
        credentials = {item.id: item for item in self.repo.list_credentials()}
        if payload.primary_credential_id is not None:
            if payload.primary_credential_id and payload.primary_credential_id not in credentials:
                raise AppError("credential_not_found", "主 API key 不存在")
            slot.primary_credential_id = payload.primary_credential_id or None
        if payload.backup_credential_ids is not None:
            backup_ids = []
            for credential_id in payload.backup_credential_ids:
                if credential_id not in credentials:
                    raise AppError("credential_not_found", "备用 API key 不存在")
                if credential_id not in backup_ids:
                    backup_ids.append(credential_id)
            slot.backup_credential_ids_json = json.dumps(backup_ids, ensure_ascii=False)
        if payload.label is not None:
            slot.label = _bounded(payload.label, 120)
        if payload.timeout_seconds is not None:
            slot.timeout_seconds = max(0.5, payload.timeout_seconds)
        if payload.hedging_delay_ms is not None:
            slot.hedging_delay_ms = max(0, payload.hedging_delay_ms)
        if payload.max_parallel is not None:
            slot.max_parallel = min(max(1, payload.max_parallel), 4)
        if payload.auto_select_enabled is not None:
            slot.auto_select_enabled = payload.auto_select_enabled
        if payload.notes is not None:
            slot.notes = _bounded(payload.notes, 500) or None
        slot.updated_by = actor_user_id
        slot.updated_at = datetime.now(timezone.utc)
        self.uow.commit()
        return self._slot_read(slot, list(credentials.values()))

    def test_credential(
        self,
        credential_id: str,
        payload: ApiHealthCheckCreate,
    ) -> ApiHealthCheckRead:
        credential = self.repo.get_credential(credential_id)
        if not credential:
            raise NotFoundError("api_credential_not_found", "API key 不存在")
        timeout_seconds = max(
            0.5,
            min(payload.timeout_seconds or credential.timeout_seconds, 30.0),
        )
        started = time.monotonic()
        status = "failed"
        error = None
        provider: OpenAICompatibleModelProvider | None = None
        try:
            provider = OpenAICompatibleModelProvider(
                base_url=credential.base_url,
                api_key=credential.api_key_secret,
                model_name=credential.model_name,
                timeout_seconds=int(max(1, timeout_seconds)),
                temperature=credential.temperature,
            )
            result = provider.generate_json(
                ModelRequest(
                    task=payload.task,
                    prompt='请只返回 {"ok": true} 这个 JSON 对象，用于健康检查。',
                    input_text="health check",
                    timeout_seconds=timeout_seconds,
                )
            )
            if not isinstance(result, dict):
                raise AppError("invalid_model_response", "模型没有返回 JSON 对象")
            status = "ok"
        except Exception as exc:
            status = _status_for_exception(exc)
            error = _safe_error(exc)
        duration_ms = _elapsed_ms(started)
        attempts = _health_check_attempts(
            provider,
            credential=credential,
            task=payload.task,
            status=status,
            duration_ms=duration_ms,
            error=error or "",
        )
        check = self.repo.add_health_check(
            ModelApiHealthCheck(
                credential_id=credential.id,
                task=payload.task,
                status=status,
                duration_ms=duration_ms,
                error_summary=error,
            )
        )
        self.record_call_traces_from_attempts(
            search_log_id=None,
            request_id=None,
            branches=[
                {
                    "source": "健康检查",
                    "status": status,
                    "attempts": attempts,
                }
            ],
            persist=True,
            output_kind="health_check",
        )
        credential.last_status = status
        credential.last_latency_ms = duration_ms
        credential.last_error = error
        credential.last_checked_at = check.checked_at
        _CAPACITY_TRACKER.record(credential.id, status=status, duration_ms=duration_ms)
        if status == "ok" and credential.status in {"invalid", "cooling"}:
            credential.status = "active"
        elif status != "ok" and credential.status == "active":
            credential.status = "invalid"
        self.uow.commit()
        return self._health_check_read(check, [credential])

    def run_health_checks(
        self,
        payload: ApiHealthCheckRunRequest,
    ) -> ApiHealthCheckRunResult:
        self.ensure_default_slots()
        self.sync_environment_credentials()
        credentials = [
            credential
            for credential in self.repo.list_credentials()
            if payload.include_disabled or credential.status != "disabled"
        ]
        checks = []
        for credential in credentials:
            task = payload.task or _representative_task(credential)
            checks.append(
                self.test_credential(
                    credential.id,
                    ApiHealthCheckCreate(
                        task=task,
                        timeout_seconds=payload.timeout_seconds,
                    ),
                )
            )
        return ApiHealthCheckRunResult(
            checked_count=len(checks),
            ok_count=sum(1 for item in checks if item.status == "ok"),
            failed_count=sum(1 for item in checks if item.status != "ok"),
            checks=checks,
        )

    def record_call_traces_from_attempts(
        self,
        *,
        search_log_id: str | None,
        request_id: str | None,
        branches: list[dict[str, Any]],
        persist: bool = False,
        output_kind: str = "runtime",
    ) -> int:
        if persist and self.trace_session_factory is not None:
            with self.trace_session_factory() as trace_db:
                return ApiCenterService(trace_db).record_call_traces_from_attempts(
                    search_log_id=search_log_id,
                    request_id=request_id,
                    branches=branches,
                    persist=True,
                    output_kind=output_kind,
                )
        credentials = self.repo.list_credentials()
        credential_lookup = _credential_lookup(credentials)
        added = 0
        for branch in branches:
            attempts = branch.get("attempts")
            if not isinstance(attempts, list):
                continue
            for attempt in attempts:
                if not isinstance(attempt, dict):
                    continue
                provider = str(attempt.get("provider") or "unknown")[:120]
                model = str(attempt.get("model") or "unknown")[:120]
                credential_id = attempt.get("credential_id")
                credential = (
                    self.repo.get_credential(str(credential_id))
                    if credential_id
                    else credential_lookup.get((provider, model))
                )
                self.repo.add_call_trace(
                    ModelCallTrace(
                        search_log_id=search_log_id,
                        request_id=request_id,
                        task=str(attempt.get("task") or branch.get("source") or "unknown")[:80],
                        layer_name=str(
                            attempt.get("layer") or branch.get("source") or "模型调用"
                        )[:120],
                        credential_id=credential.id if credential else None,
                        credential_label=credential.label if credential else None,
                        provider=provider,
                        model=model,
                        status=str(attempt.get("status") or "unknown")[:24],
                        duration_ms=int(
                            attempt.get("duration_ms")
                            or attempt.get("durationMs")
                            or 0
                        ),
                        fallback_index=_optional_int(
                            attempt.get("fallback_index")
                            if "fallback_index" in attempt
                            else attempt.get("fallbackIndex")
                        ),
                        error_summary=(
                            _bounded(str(attempt.get("error") or ""), 300) or None
                        ),
                        response_valid=attempt.get("status") == "ok",
                        output_summary_json=json.dumps(
                            {
                                "branch": branch.get("source"),
                                "branchStatus": branch.get("status"),
                                "kind": output_kind,
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
                added += 1
        if persist and added:
            self.uow.commit()
        return added

    def _credential_read(
        self,
        item: ModelApiCredential,
        metric: dict[str, float] | None = None,
    ) -> ApiCredentialRead:
        runtime = _CAPACITY_TRACKER.snapshot([item.id]).get(item.id, {})
        metric = metric or {}
        max_concurrency = _normalize_max_concurrency(item.max_concurrency)
        current_concurrency = int(runtime.get("in_flight", 0))
        available_concurrency = max(0, max_concurrency - current_concurrency)
        total = int(metric.get("total", 0))
        failed = int(metric.get("failed", 0))
        avg_latency = int(
            metric.get(
                "avg_latency",
                item.last_latency_ms if item.last_latency_ms is not None else 0,
            )
            or 0
        )
        return ApiCredentialRead(
            id=item.id,
            label=item.label,
            provider_type=item.provider_type,
            base_url=item.base_url,
            model_name=item.model_name,
            api_key_preview=item.api_key_preview,
            task_scope=_loads_list(item.task_scope_json),
            status=item.status,
            priority=item.priority,
            timeout_seconds=item.timeout_seconds,
            temperature=item.temperature,
            max_concurrency=max_concurrency,
            auto_assign_enabled=item.auto_assign_enabled,
            current_concurrency=current_concurrency,
            available_concurrency=available_concurrency,
            capacity_status=_capacity_status(
                status=item.status,
                last_status=item.last_status,
                current_concurrency=current_concurrency,
                max_concurrency=max_concurrency,
                failure_rate=failed / total if total else 0.0,
            ),
            recent_call_count=total,
            recent_failure_rate=failed / total if total else 0.0,
            recent_average_latency_ms=avg_latency,
            last_status=item.last_status,
            last_latency_ms=item.last_latency_ms,
            last_error=item.last_error,
            last_checked_at=item.last_checked_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    def _slot_read(
        self,
        item: ModelRoutingSlot,
        credentials: list[ModelApiCredential],
    ) -> RoutingSlotRead:
        labels = {credential.id: credential.label for credential in credentials}
        backup_ids = _loads_list(item.backup_credential_ids_json)
        return RoutingSlotRead(
            id=item.id,
            task=item.task,
            label=item.label,
            primary_credential_id=item.primary_credential_id,
            primary_credential_label=(
                labels.get(item.primary_credential_id) if item.primary_credential_id else None
            ),
            backup_credential_ids=backup_ids,
            backup_credential_labels=[labels.get(item, item) for item in backup_ids],
            timeout_seconds=item.timeout_seconds,
            hedging_delay_ms=item.hedging_delay_ms,
            max_parallel=item.max_parallel,
            auto_select_enabled=item.auto_select_enabled,
            notes=item.notes,
            updated_at=item.updated_at,
        )

    def _health_check_read(
        self,
        item: ModelApiHealthCheck,
        credentials: list[ModelApiCredential],
    ) -> ApiHealthCheckRead:
        labels = {credential.id: credential.label for credential in credentials}
        return ApiHealthCheckRead(
            id=item.id,
            credential_id=item.credential_id,
            credential_label=labels.get(item.credential_id),
            task=item.task,
            status=item.status,
            duration_ms=item.duration_ms,
            error_summary=item.error_summary,
            checked_at=item.checked_at,
        )

    def _call_trace_read(self, item: ModelCallTrace) -> ApiCallTraceRead:
        return ApiCallTraceRead(
            id=item.id,
            search_log_id=item.search_log_id,
            request_id=item.request_id,
            task=item.task,
            layer_name=item.layer_name,
            credential_id=item.credential_id,
            credential_label=item.credential_label,
            provider=item.provider,
            model=item.model,
            status=item.status,
            duration_ms=item.duration_ms,
            fallback_index=item.fallback_index,
            error_summary=item.error_summary,
            response_valid=item.response_valid,
            output_summary=_loads_dict(item.output_summary_json),
            created_at=item.created_at,
        )


class ApiCenterScheduledModelProvider:
    """Task-aware provider that lets API Center choose healthy credentials at runtime."""

    name = "api_center_scheduler"

    def __init__(
        self,
        api_center: ApiCenterService,
        fallback_provider: ModelProvider,
    ) -> None:
        self.api_center = api_center
        self.fallback_provider = fallback_provider
        self.last_attempts: list[dict[str, Any]] = []

    @property
    def configured(self) -> bool:
        credentials = self.api_center.repo.list_auto_assign_credentials()
        return bool(credentials) or self.fallback_provider.configured

    @property
    def attempt_count(self) -> int:
        # The scheduler owns internal fallbacks; outer search budgets should not be
        # multiplied by the number of keys, otherwise slow providers stretch the
        # whole search chain.
        return 1

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        return self._run(request)

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any],
    ) -> Any:
        return self._run(request, validator=validator)

    def _run(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any] | None = None,
    ) -> Any:
        attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
        slot, credentials = self.api_center.select_credentials_for_task(request.task)
        if not credentials:
            return self._run_fallback(request, validator=validator)

        total_timeout = _task_timeout(request, slot)
        deadline = time.monotonic() + total_timeout
        fallback_index = 0
        while time.monotonic() < deadline:
            _, credentials = self.api_center.select_credentials_for_task(request.task)
            if not credentials:
                break
            acquired_any = False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            for credential in credentials:
                if not _CAPACITY_TRACKER.try_acquire(
                    credential.id,
                    _normalize_max_concurrency(credential.max_concurrency),
                ):
                    continue
                acquired_any = True
                provider = OpenAICompatibleModelProvider(
                    base_url=credential.base_url,
                    api_key=credential.api_key_secret,
                    model_name=credential.model_name,
                    timeout_seconds=int(max(1, min(credential.timeout_seconds, remaining))),
                    temperature=credential.temperature,
                )
                started = time.monotonic()
                try:
                    attempt_request = replace(
                        request,
                        timeout_seconds=max(
                            0.5,
                            min(
                                request.timeout_seconds or total_timeout,
                                credential.timeout_seconds,
                                remaining,
                            ),
                        ),
                    )
                    payload = provider.generate_json(attempt_request)
                    result = validator(payload) if validator else payload
                    duration_ms = _elapsed_ms(started)
                    current_attempts = _scheduled_attempts(
                        provider.last_attempts,
                        credential=credential,
                        fallback_index=fallback_index,
                        status="ok",
                        duration_ms=duration_ms,
                        task=request.task,
                    )
                    attempts.extend(current_attempts)
                    self.last_attempts = attempts
                    self._record_traces(request, current_attempts, status="ok")
                    self.api_center.record_runtime_attempt(
                        credential.id,
                        status="ok",
                        duration_ms=duration_ms,
                        error_summary=None,
                    )
                    return result
                except Exception as exc:
                    duration_ms = _elapsed_ms(started)
                    error = _safe_error(exc)
                    status = _status_for_exception(exc)
                    current_attempts = _scheduled_attempts(
                        provider.last_attempts,
                        credential=credential,
                        fallback_index=fallback_index,
                        status=status,
                        duration_ms=duration_ms,
                        task=request.task,
                        error=error,
                    )
                    attempts.extend(current_attempts)
                    self.last_attempts = attempts
                    self._record_traces(request, current_attempts, status=status)
                    self.api_center.record_runtime_attempt(
                        credential.id,
                        status=status,
                        duration_ms=duration_ms,
                        error_summary=error,
                    )
                    last_error = exc
                    fallback_index += 1
                    continue
                finally:
                    _CAPACITY_TRACKER.release(credential.id)
            if not acquired_any:
                time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
                continue
            if attempts:
                break

        if attempts:
            raise ModelProviderError(
                f"API 中心调度的 {len(attempts)} 次模型调用均失败："
                f"{_format_attempts(attempts)}"
            ) from last_error
        timeout_attempt = _scheduler_terminal_attempt(
            request,
            status="timed_out",
            error="API 中心可用 API 当前都已达到并发上限，超过任务时间预算",
            duration_ms=round(total_timeout * 1000),
        )
        self.last_attempts = [timeout_attempt]
        self._record_traces(request, self.last_attempts, status="timed_out")
        raise ModelProviderError("API 中心可用 API 当前都已达到并发上限，请稍后重试")

    def _run_fallback(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any] | None = None,
    ) -> Any:
        if not self.fallback_provider.configured:
            self.last_attempts = [
                _scheduler_terminal_attempt(
                    request,
                    status="skipped",
                    error="API 中心和环境变量 Provider 均未配置",
                    duration_ms=0,
                )
            ]
            self._record_traces(request, self.last_attempts, status="skipped")
            raise ModelProviderNotConfigured("API 中心和环境变量 Provider 均未配置")
        status = "failed"
        error = ""
        try:
            if validator:
                validated_runner = getattr(
                    self.fallback_provider,
                    "generate_validated_json",
                    None,
                )
                if callable(validated_runner):
                    result = validated_runner(request, validator)
                else:
                    result = validator(self.fallback_provider.generate_json(request))
            else:
                result = self.fallback_provider.generate_json(request)
            status = "ok"
            error = ""
        except Exception as exc:
            status = _status_for_exception(exc)
            error = _safe_error(exc)
            raise
        finally:
            self.last_attempts = [
                {
                    **attempt,
                    "task": request.task,
                    "layer": TASK_LAYER_LABELS.get(request.task, "模型调用"),
                    "credential_id": None,
                    "credential_label": "环境变量兜底",
                    "status": status,
                    "error": error or str(attempt.get("error") or ""),
                }
                for attempt in getattr(self.fallback_provider, "last_attempts", [])
                if isinstance(attempt, dict)
            ]
            if not self.last_attempts:
                self.last_attempts = [
                    _scheduler_terminal_attempt(
                        request,
                        status=status,
                        error=error,
                        duration_ms=0,
                    )
                ]
            self._record_traces(request, self.last_attempts, status=status)
        return result

    def _record_traces(
        self,
        request: ModelRequest,
        attempts: list[dict[str, Any]],
        *,
        status: str,
    ) -> None:
        self.api_center.record_call_traces_from_attempts(
            search_log_id=None,
            request_id=None,
            branches=[
                {
                    "source": TASK_LAYER_LABELS.get(request.task, "模型调用"),
                    "status": status,
                    "attempts": attempts,
                }
            ],
            persist=True,
        )


def _api_key_preview(api_key: str) -> str:
    cleaned = api_key.strip()
    if len(cleaned) <= 8:
        return "*" * len(cleaned)
    return f"{cleaned[:3]}****{cleaned[-4:]}"


def _bounded(value: str, limit: int) -> str:
    return value.strip()[:limit]


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:300]


def _status_for_exception(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError,)):
        return "timed_out"
    message = str(exc).lower()
    if "timeout" in message or "timed out" in message or "超时" in message:
        return "timed_out"
    return "failed"


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _loads_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _loads_dict(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _task_timeout(request: ModelRequest, slot: ModelRoutingSlot | None) -> float:
    if request.timeout_seconds is not None:
        return max(0.5, request.timeout_seconds)
    if slot:
        return max(0.5, slot.timeout_seconds)
    return 20.0


def _normalize_max_concurrency(value: int | None) -> int:
    return min(max(1, int(value or 1)), 20)


def _capacity_status(
    *,
    status: str,
    last_status: str | None,
    current_concurrency: int,
    max_concurrency: int,
    failure_rate: float,
) -> str:
    if status in {"disabled", "invalid"} or last_status in {"failed", "timed_out"}:
        return "degraded"
    if current_concurrency >= max(1, max_concurrency):
        return "saturated"
    if current_concurrency > 0:
        return "busy"
    if failure_rate >= 0.5:
        return "degraded"
    return "idle"


def _credential_can_run_task(credential: ModelApiCredential, task: str) -> bool:
    if credential.status != "active" or not credential.auto_assign_enabled:
        return False
    scopes = _loads_list(credential.task_scope_json)
    return not scopes or task in scopes


def _credential_schedule_key(
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
        float(credential.last_latency_ms if credential.last_latency_ms is not None else 999_999),
    )
    success_rate = ok / total if total else (1.0 if credential.last_status == "ok" else 0.5)
    max_concurrency = _normalize_max_concurrency(credential.max_concurrency)
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


def _build_schedule_metrics(
    traces: list[ModelCallTrace],
    checks: list[ModelApiHealthCheck],
) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for trace in traces:
        if not trace.credential_id:
            continue
        _add_metric(
            metrics,
            trace.credential_id,
            ok=trace.status == "ok",
            duration_ms=trace.duration_ms,
        )
    for check in checks:
        _add_metric(
            metrics,
            check.credential_id,
            ok=check.status == "ok",
            duration_ms=check.duration_ms,
        )
    for metric in metrics.values():
        total = max(1.0, metric["total"])
        metric["avg_latency"] = metric["latency_total"] / total
    return metrics


def _add_metric(
    metrics: dict[str, dict[str, float]],
    credential_id: str,
    *,
    ok: bool,
    duration_ms: int,
) -> None:
    metric = metrics.setdefault(
        credential_id,
        {"total": 0.0, "ok": 0.0, "failed": 0.0, "latency_total": 0.0},
    )
    metric["total"] += 1
    metric["ok"] += 1 if ok else 0
    metric["failed"] += 0 if ok else 1
    metric["latency_total"] += max(0, duration_ms)


def _representative_task(credential: ModelApiCredential) -> ModelTaskName:
    scopes = _loads_list(credential.task_scope_json)
    for task in scopes:
        if task in VALID_MODEL_TASKS:
            return cast(ModelTaskName, task)
    return "search_system_routing"


def _scheduled_attempts(
    provider_attempts: list[dict[str, Any]],
    *,
    credential: ModelApiCredential,
    fallback_index: int,
    status: str,
    duration_ms: int,
    task: str,
    error: str = "",
) -> list[dict[str, Any]]:
    raw_attempts = provider_attempts or [
        {
            "provider": _provider_host_label(credential.base_url),
            "model": credential.model_name,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
        }
    ]
    attempts = []
    for attempt in raw_attempts:
        if not isinstance(attempt, dict):
            continue
        attempts.append(
            {
                **attempt,
                "task": task,
                "layer": TASK_LAYER_LABELS.get(task, "模型调用"),
                "credential_id": credential.id,
                "credential_label": credential.label,
                "fallback_index": fallback_index,
                "status": status,
                "duration_ms": int(attempt.get("duration_ms") or duration_ms),
                "error": error or str(attempt.get("error") or ""),
            }
        )
    return attempts


def _health_check_attempts(
    provider: OpenAICompatibleModelProvider | None,
    *,
    credential: ModelApiCredential,
    task: str,
    status: str,
    duration_ms: int,
    error: str,
) -> list[dict[str, Any]]:
    raw_attempts = provider.last_attempts if provider else []
    if not raw_attempts:
        raw_attempts = [
            {
                "provider": _provider_host_label(credential.base_url),
                "model": credential.model_name,
                "duration_ms": duration_ms,
            }
        ]
    return [
        {
            **attempt,
            "task": task,
            "layer": "健康检查",
            "credential_id": credential.id,
            "credential_label": credential.label,
            "status": status,
            "duration_ms": int(attempt.get("duration_ms") or duration_ms),
            "error": error or str(attempt.get("error") or ""),
        }
        for attempt in raw_attempts
        if isinstance(attempt, dict)
    ]


def _scheduler_terminal_attempt(
    request: ModelRequest,
    *,
    status: str,
    error: str,
    duration_ms: int,
) -> dict[str, Any]:
    return {
        "task": request.task,
        "layer": TASK_LAYER_LABELS.get(request.task, "模型调用"),
        "provider": "api_center_scheduler",
        "model": "未分配",
        "status": status,
        "duration_ms": max(0, duration_ms),
        "error": error,
        "credential_id": None,
        "credential_label": None,
    }


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    index = min(len(values) - 1, max(0, round((len(values) - 1) * percentile)))
    return int(values[index])


def _credential_lookup(
    credentials: list[ModelApiCredential],
) -> dict[tuple[str, str], ModelApiCredential]:
    lookup = {}
    for credential in credentials:
        host = _provider_host_label(credential.base_url)
        for provider_label in {host, credential.provider_type, credential.label}:
            lookup[(provider_label, credential.model_name)] = credential
    return lookup


def _provider_host_label(base_url: str) -> str:
    return base_url.rstrip("/").split("//")[-1].split("/")[0].split(":")[0]


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None
