from __future__ import annotations

import hashlib
import json
import math
import tempfile
import time
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Literal, NoReturn, cast
from urllib.parse import urlparse, urlunparse

from app.ai.contracts import (
    CancellationSignal,
    ModelCallResult,
    ModelProvider,
    ModelProviderCancelled,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.fallback import _format_attempts
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.core.config import get_settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.api_provider import (
    ModelApiCredential,
    ModelApiHealthCheck,
    ModelCallTrace,
    ModelRoutingSlot,
)
from app.repositories.api_center_repository import ApiCenterRepository
from app.schemas.api_center import (
    ApiCallTraceListResponse,
    ApiCallTraceRead,
    ApiCenterOverview,
    ApiCenterMaintenanceRead,
    ApiCenterMaintenanceRunResult,
    ApiCenterSummary,
    ApiCredentialCapabilityRead,
    ApiCredentialCreate,
    ApiCredentialRead,
    ApiCredentialUpdate,
    ApiHealthCheckCreate,
    ApiHealthCheckRead,
    ApiHealthCheckRunRequest,
    ApiHealthCheckRunResult,
    ApiProviderGroupRead,
    ApiTemperatureProbeRead,
    ApiTemperatureProbeRequest,
    ApiTemperatureTuneRequest,
    ApiTemperatureTuneResult,
    ModelTaskName,
    RoutingSlotRead,
    RoutingSlotUpdate,
)
from app.services.api_center_error_catalog import classify_api_error
from app.services.api_center_runtime_policy import (
    _CAPACITY_TRACKER,
    credential_is_available,
    credential_schedule_key,
    normalize_max_concurrency,
    provider_runtime_snapshot,
)
from app.services.unit_of_work import UnitOfWork

DEFAULT_ROUTING_SLOTS: tuple[tuple[str, str, float, int], ...] = (
    ("search_system_routing", "第一层：体系路由", 45.0, 2500),
    ("search_intent_understanding", "第二层：卖点识别", 60.0, 3500),
    ("search_proof_point_understanding", "第三层：证明点识别", 45.0, 3500),
    ("search_candidate_review", "第四层：候选图片复核", 45.0, 3500),
    ("search_result_recommendation_reason", "搜索结果：动态推荐理由", 45.0, 3000),
    ("image_content_analysis", "上传主图：图片语义分析", 120.0, 6000),
    ("asset_search_phrase_generation", "上传前：素材话术生成", 120.0, 6000),
    ("copy_selling_point_matching", "兼容接口：文案卖点匹配", 20.0, 3000),
    ("asset_agent_chat", "素材库 Agent：业务解释", 30.0, 3500),
)
SEARCH_TASKS = (
    "search_system_routing",
    "search_intent_understanding",
    "search_proof_point_understanding",
    "search_candidate_review",
)

TASK_LAYER_LABELS = {
    task: label for task, label, _, _ in DEFAULT_ROUTING_SLOTS
}
ENV_IMPORT_SETTING_KEY = "environment_credentials_imported"
MAINTENANCE_STATUS_SETTING_KEY = "api_center_maintenance_status"
TEMPERATURE_PROBE_TIMEOUT_SECONDS = 60.0
TEMPERATURE_PROBE_MAX_CANDIDATES = 6
DEFAULT_TEMPERATURE_PROBE_CANDIDATES = (0.2, 1.0, 0.0, 0.7)
HEALTH_PROBE_TIMEOUT_SECONDS = 60.0
HEALTH_PROBE_MAX_ATTEMPTS = 2
MIN_API_CALL_TIMEOUT_SECONDS = 20.0
MAX_API_CALL_TIMEOUT_SECONDS = 60.0
MIN_SCHEDULER_ATTEMPT_SECONDS = 8.0
MIN_FALLBACK_RELAY_SECONDS = 8.0
SCHEDULER_IDLE_WAIT_SECONDS = 0.1
SCHEDULER_METRICS_CACHE_TTL_SECONDS = 15.0
UPLOAD_TASK_MIN_SLOT_TIMEOUT_SECONDS = {
    "image_content_analysis": 120.0,
    "asset_search_phrase_generation": 120.0,
}
UPLOAD_TASK_MIN_PARALLEL = 3
TASK_MIN_ATTEMPT_TIMEOUT_SECONDS = {
    "image_content_analysis": 55.0,
    "asset_search_phrase_generation": 55.0,
}
TRANSIENT_HEALTH_ERROR_CODES = {
    "connection_failed",
    "connection_timeout",
    "provider_timeout",
    "rate_limited",
    "response_timeout",
    "upstream_unavailable",
}
SUPPORTED_PROVIDER_TYPES = {"openai_compatible"}
MODEL_CAPABILITY_LABELS = {
    "text_json": "文本结构化 JSON",
    "vision_json": "图片输入 JSON",
}
CapabilityStatus = Literal["ok", "failed", "unknown"]
TASK_CAPABILITY_REQUIREMENTS = {
    "image_content_analysis": "vision_json",
}
CAPABILITY_FAILURE_ERROR_CODES = {
    "task_capability_unsupported",
    "invalid_json_response",
    "invalid_response_shape",
    "empty_response",
    "request_rejected",
}
_TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

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
_ENVIRONMENT_IMPORT_LOCK = Lock()
HEALTH_CHECK_MAX_WORKERS = 4


@dataclass(frozen=True)
class _CredentialSaveProbeResult:
    status: str
    duration_ms: int
    temperature: float | None
    temperature_enabled: bool


@dataclass(frozen=True)
class _HealthProbeTarget:
    credential_id: str
    task: ModelTaskName
    provider_group: str


@dataclass(frozen=True)
class _ScheduledAttemptOutcome:
    credential: ModelApiCredential
    fallback_index: int
    status: str
    duration_ms: int
    provider_attempts: tuple[dict[str, Any], ...]
    result: Any | None = None
    error: Exception | None = None
    error_summary: str | None = None
    error_code: str | None = None


@dataclass(frozen=True)
class _RunningScheduledAttempt:
    credential: ModelApiCredential
    fallback_index: int
    started_at: float
    cancellation: CancellationSignal


@dataclass(frozen=True)
class _SchedulerSelectionSnapshot:
    credentials: list[ModelApiCredential]
    auto_credentials: list[ModelApiCredential]
    slots_by_task: dict[str, ModelRoutingSlot]
    metrics: dict[str, dict[str, float]]


@dataclass(frozen=True)
class _CachedScheduleMetrics:
    expires_at: float
    metrics: dict[str, dict[str, float]]


class _ScheduleMetricsCache:
    def __init__(self) -> None:
        self._lock = Lock()
        self._by_bind_id: dict[int, _CachedScheduleMetrics] = {}

    def get(self, repo: ApiCenterRepository) -> dict[str, dict[str, float]]:
        bind_id = id(repo.db.get_bind())
        now = time.monotonic()
        with self._lock:
            cached = self._by_bind_id.get(bind_id)
            if cached and cached.expires_at > now:
                return cached.metrics
        metrics = _build_schedule_metrics(
            repo.list_call_traces_since(hours=24, limit=5000),
            repo.list_recent_health_checks(limit=5000),
        )
        with self._lock:
            self._by_bind_id[bind_id] = _CachedScheduleMetrics(
                expires_at=now + SCHEDULER_METRICS_CACHE_TTL_SECONDS,
                metrics=metrics,
            )
        return metrics

    def reset_for_tests(self) -> None:
        with self._lock:
            self._by_bind_id.clear()


_SCHEDULE_METRICS_CACHE = _ScheduleMetricsCache()


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
        credentials = self.repo.list_credentials()
        slots = self.repo.list_slots()
        recent_traces = self.repo.list_recent_call_traces(limit=100)
        search_context = self.repo.search_context_by_ids(
            {
                item.search_log_id
                for item in recent_traces
                if item.search_log_id is not None
            }
        )
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
            maintenance=self.maintenance_status(),
            credentials=[
                self._credential_read(item, schedule_metrics.get(item.id))
                for item in credentials
            ],
            provider_groups=_build_provider_groups(credentials, recent_day_traces),
            routing_slots=[self._slot_read(item, credentials) for item in slots],
            recent_call_traces=[
                self._call_trace_read(
                    item,
                    search_context=search_context.get(item.search_log_id)
                    if item.search_log_id
                    else None,
                )
                for item in recent_traces
            ],
        )

    def maintenance_status(self) -> ApiCenterMaintenanceRead:
        settings = get_settings()
        raw = self.repo.get_setting(MAINTENANCE_STATUS_SETTING_KEY)
        payload = _loads_dict(raw.value if raw else "{}")
        last_started_at = _parse_datetime(payload.get("last_started_at"))
        last_finished_at = _parse_datetime(payload.get("last_finished_at"))
        interval_minutes = max(
            1,
            int(getattr(settings, "api_center_maintenance_interval_minutes", 360)),
        )
        next_run_at = (
            last_started_at + timedelta(minutes=interval_minutes)
            if last_started_at
            else None
        )
        return ApiCenterMaintenanceRead(
            enabled=bool(getattr(settings, "api_center_maintenance_enabled", False)),
            interval_minutes=interval_minutes,
            startup_delay_seconds=max(
                0,
                int(getattr(settings, "api_center_maintenance_startup_delay_seconds", 300)),
            ),
            max_credentials_per_cycle=max(
                1,
                int(getattr(settings, "api_center_maintenance_max_credentials_per_cycle", 20)),
            ),
            call_trace_retention_days=max(
                1,
                int(getattr(settings, "api_center_call_trace_retention_days", 30)),
            ),
            health_check_retention_days=max(
                1,
                int(getattr(settings, "api_center_health_check_retention_days", 90)),
            ),
            last_started_at=last_started_at,
            last_finished_at=last_finished_at,
            last_status=str(payload.get("last_status") or "idle"),
            last_error=(
                str(payload["last_error"])
                if payload.get("last_error") is not None
                else None
            ),
            last_checked_count=_optional_int(payload.get("last_checked_count")) or 0,
            last_ok_count=_optional_int(payload.get("last_ok_count")) or 0,
            last_failed_count=_optional_int(payload.get("last_failed_count")) or 0,
            last_deleted_call_trace_count=(
                _optional_int(payload.get("last_deleted_call_trace_count")) or 0
            ),
            last_deleted_health_check_count=(
                _optional_int(payload.get("last_deleted_health_check_count")) or 0
            ),
            next_run_at=next_run_at,
        )

    def run_maintenance_cycle(
        self,
        *,
        interval_minutes: int | None = None,
        max_credentials_per_cycle: int | None = None,
        call_trace_retention_days: int | None = None,
        health_check_retention_days: int | None = None,
        only_due: bool = True,
    ) -> ApiCenterMaintenanceRunResult:
        settings = get_settings()
        started_at = datetime.now(timezone.utc)
        interval = max(
            1,
            int(
                interval_minutes
                if interval_minutes is not None
                else getattr(settings, "api_center_maintenance_interval_minutes", 360)
            ),
        )
        max_credentials = max(
            1,
            int(
                max_credentials_per_cycle
                if max_credentials_per_cycle is not None
                else getattr(settings, "api_center_maintenance_max_credentials_per_cycle", 20)
            ),
        )
        trace_days = max(
            1,
            int(
                call_trace_retention_days
                if call_trace_retention_days is not None
                else getattr(settings, "api_center_call_trace_retention_days", 30)
            ),
        )
        health_days = max(
            1,
            int(
                health_check_retention_days
                if health_check_retention_days is not None
                else getattr(settings, "api_center_health_check_retention_days", 90)
            ),
        )
        self._write_maintenance_status(
            {
                "last_started_at": started_at.isoformat(),
                "last_finished_at": None,
                "last_status": "running",
                "last_error": None,
                "last_checked_count": 0,
                "last_ok_count": 0,
                "last_failed_count": 0,
                "last_deleted_call_trace_count": 0,
                "last_deleted_health_check_count": 0,
            }
        )
        try:
            self.initialize_runtime()
            due_cutoff = started_at - timedelta(minutes=interval)
            due_credentials = self.repo.list_credentials_due_for_health_check(
                cutoff=due_cutoff,
                limit=max_credentials,
            )
            due_credentials = (
                due_credentials
                if only_due
                else [
                    credential
                    for credential in self.repo.list_credentials()
                    if credential.status == "active"
                ][:max_credentials]
            )
            checks: list[ApiHealthCheckRead] = []
            for credential in due_credentials:
                checks.append(
                    self.test_credential(
                        credential.id,
                        ApiHealthCheckCreate(
                            task=_representative_task_for_scope(
                                _loads_list(credential.task_scope_json)
                            )
                        ),
                    )
                )

            deleted_call_traces = self.repo.delete_call_traces_before(
                started_at - timedelta(days=trace_days)
            )
            deleted_health_checks = self.repo.delete_health_checks_before(
                started_at - timedelta(days=health_days)
            )
            finished_at = datetime.now(timezone.utc)
            result = ApiCenterMaintenanceRunResult(
                status="ok",
                started_at=started_at,
                finished_at=finished_at,
                checked_count=len(checks),
                ok_count=sum(1 for item in checks if item.status == "ok"),
                failed_count=sum(1 for item in checks if item.status != "ok"),
                deleted_call_trace_count=deleted_call_traces,
                deleted_health_check_count=deleted_health_checks,
            )
            self._write_maintenance_status(_maintenance_result_payload(result))
            return result
        except Exception as exc:
            finished_at = datetime.now(timezone.utc)
            result = ApiCenterMaintenanceRunResult(
                status="failed",
                started_at=started_at,
                finished_at=finished_at,
                checked_count=0,
                ok_count=0,
                failed_count=0,
                deleted_call_trace_count=0,
                deleted_health_check_count=0,
            )
            self._write_maintenance_status(
                {
                    **_maintenance_result_payload(result),
                    "last_error": _safe_error(exc),
                }
            )
            raise

    def _write_maintenance_status(self, payload: dict[str, Any]) -> None:
        self.repo.set_setting(
            MAINTENANCE_STATUS_SETTING_KEY,
            json.dumps(payload, ensure_ascii=False),
        )
        self.uow.commit()

    def list_call_traces(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        task: str | None = None,
        status: str | None = None,
        provider: str | None = None,
        credential_id: str | None = None,
        request_id: str | None = None,
        keyword: str | None = None,
    ) -> ApiCallTraceListResponse:
        total, traces = self.repo.list_call_traces_filtered(
            limit=limit,
            offset=offset,
            task=_bounded(task or "", 80) or None,
            status=_bounded(status or "", 24) or None,
            provider=_bounded(provider or "", 120) or None,
            credential_id=_bounded(credential_id or "", 36) or None,
            request_id=_bounded(request_id or "", 64) or None,
            keyword=_bounded(keyword or "", 120) or None,
        )
        search_context = self.repo.search_context_by_ids(
            {
                item.search_log_id
                for item in traces
                if item.search_log_id is not None
            }
        )
        safe_limit = min(max(1, int(limit)), 500)
        safe_offset = max(0, int(offset))
        return ApiCallTraceListResponse(
            items=[
                self._call_trace_read(
                    item,
                    search_context=search_context.get(item.search_log_id)
                    if item.search_log_id
                    else None,
                )
                for item in traces
            ],
            total=total,
            limit=safe_limit,
            offset=safe_offset,
            has_more=safe_offset + len(traces) < total,
        )

    def initialize_runtime(self) -> None:
        """Create defaults and migrate legacy environment credentials once."""
        self.ensure_default_slots()
        self.import_environment_credentials_once()
        self.normalize_legacy_credential_statuses()
        self.normalize_legacy_credential_fingerprints()

    def normalize_legacy_credential_statuses(self) -> None:
        changed = False
        for credential in self.repo.list_credentials():
            if credential.status not in {"cooling", "invalid"}:
                continue
            credential.status = "active"
            credential.updated_at = datetime.now(timezone.utc)
            changed = True
        if changed:
            self.uow.commit()

    def normalize_legacy_credential_fingerprints(self) -> None:
        changed = False
        for credential in self.repo.list_credentials():
            if credential.api_key_fingerprint:
                continue
            credential.api_key_fingerprint = _api_key_fingerprint(
                credential.api_key_secret,
            )
            credential.updated_at = datetime.now(timezone.utc)
            changed = True
        if changed:
            self.uow.commit()

    def ensure_default_slots(self) -> None:
        changed = False
        for task, label, timeout_seconds, hedging_delay_ms in DEFAULT_ROUTING_SLOTS:
            slot = self.repo.get_slot_by_task(task)
            is_upload_task = task in UPLOAD_TASK_MIN_SLOT_TIMEOUT_SECONDS
            default_parallel = (
                UPLOAD_TASK_MIN_PARALLEL
                if is_upload_task
                else 4 if task in SEARCH_TASKS else 2
            )
            if slot:
                has_manual_routing = bool(
                    slot.primary_credential_id
                    or _loads_list(slot.backup_credential_ids_json)
                )
                if not slot.auto_select_enabled and not has_manual_routing:
                    slot.auto_select_enabled = True
                    slot.max_parallel = max(slot.max_parallel, default_parallel)
                    changed = True
                if is_upload_task and slot.auto_select_enabled and not has_manual_routing:
                    min_timeout = UPLOAD_TASK_MIN_SLOT_TIMEOUT_SECONDS[task]
                    if slot.timeout_seconds < min_timeout:
                        slot.timeout_seconds = min_timeout
                        changed = True
                    if slot.hedging_delay_ms < hedging_delay_ms:
                        slot.hedging_delay_ms = hedging_delay_ms
                        changed = True
                    if slot.max_parallel < UPLOAD_TASK_MIN_PARALLEL:
                        slot.max_parallel = UPLOAD_TASK_MIN_PARALLEL
                        changed = True
                if slot.label != label:
                    slot.label = label
                    changed = True
                continue
            self.repo.add_slot(
                ModelRoutingSlot(
                    task=task,
                    label=label,
                    timeout_seconds=timeout_seconds,
                    hedging_delay_ms=hedging_delay_ms,
                    max_parallel=default_parallel,
                    auto_select_enabled=True,
                    backup_credential_ids_json="[]",
                    excluded_credential_ids_json="[]",
                )
            )
            changed = True
        if changed:
            self.uow.commit()

    def import_environment_credentials_once(self) -> None:
        """Import legacy .env credentials only when the API Center is empty.

        The API Center database is the runtime source of truth. Environment
        variables are retained only as a one-time migration path for existing
        deployments that have not configured the API Center yet.
        """

        setting = self.repo.get_setting(ENV_IMPORT_SETTING_KEY)
        if setting and setting.value == "true":
            return
        if self.repo.list_credentials():
            self.repo.set_setting(ENV_IMPORT_SETTING_KEY, "true")
            self.uow.commit()
            return

        with _ENVIRONMENT_IMPORT_LOCK:
            setting = self.repo.get_setting(ENV_IMPORT_SETTING_KEY)
            if setting and setting.value == "true":
                return
            if self.repo.list_credentials():
                self.repo.set_setting(ENV_IMPORT_SETTING_KEY, "true")
                self.uow.commit()
                return
            self._import_environment_credentials()
            self.repo.set_setting(ENV_IMPORT_SETTING_KEY, "true")
            self.uow.commit()

    def _import_environment_credentials(self) -> None:
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
                        api_key_fingerprint=_api_key_fingerprint(api_key),
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
                "api_key_fingerprint": _api_key_fingerprint(api_key),
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
        default_request_id: str | None = None,
    ) -> ModelProvider:
        return ApiCenterScheduledModelProvider(
            self,
            default_request_id=default_request_id,
        )

    def scheduler_selection_snapshot(self) -> _SchedulerSelectionSnapshot:
        credentials = self.repo.list_credentials()
        slots = self.repo.list_slots()
        return _SchedulerSelectionSnapshot(
            credentials=credentials,
            auto_credentials=[
                credential
                for credential in credentials
                if credential.status == "active" and credential.auto_assign_enabled
            ],
            slots_by_task={slot.task: slot for slot in slots},
            metrics=_SCHEDULE_METRICS_CACHE.get(self.repo),
        )

    def select_credentials_for_task(
        self,
        task: str,
        *,
        snapshot: _SchedulerSelectionSnapshot | None = None,
    ) -> tuple[ModelRoutingSlot | None, list[ModelApiCredential]]:
        snapshot = snapshot or self.scheduler_selection_snapshot()
        slot = snapshot.slots_by_task.get(task)
        credentials = snapshot.credentials
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
                if credential and credential_is_available(
                    credential,
                    require_auto_assign=False,
                ):
                    selected.append(credential)
            return slot, selected

        excluded_credential_ids = (
            set(_loads_list(slot.excluded_credential_ids_json)) if slot else set()
        )
        candidates = [
            item
            for item in snapshot.auto_credentials
            if credential_is_available(item)
            and item.id not in excluded_credential_ids
            and _credential_can_auto_run_task(item, task)
        ]
        metrics = snapshot.metrics
        runtime = _CAPACITY_TRACKER.snapshot([item.id for item in candidates])
        provider_runtime = provider_runtime_snapshot(candidates, runtime)
        selected = sorted(
            candidates,
            key=lambda credential: credential_schedule_key(
                credential,
                metrics,
                runtime,
                provider_runtime,
            ),
        )
        return slot, selected

    def disable_provider_group(
        self,
        provider_group: str,
        *,
        actor_user_id: str | None = None,
    ) -> ApiProviderGroupRead:
        del actor_user_id
        credentials = self.repo.list_credentials()
        matched = [
            credential
            for credential in credentials
            if _provider_host_label(credential.base_url) == provider_group
        ]
        if not matched:
            raise NotFoundError("provider_group_not_found", "中转站不存在")
        now = datetime.now(timezone.utc)
        for credential in matched:
            if credential.status == "disabled":
                continue
            credential.status = "disabled"
            credential.updated_at = now
            _CAPACITY_TRACKER.discard(credential.id)
        self.uow.commit()
        refreshed = self.repo.list_credentials()
        traces = self.repo.list_call_traces_since(hours=24, limit=2000)
        for group in _build_provider_groups(refreshed, traces):
            if group.provider_group == provider_group:
                return group
        raise NotFoundError("provider_group_not_found", "中转站不存在")

    def credential_audit_snapshot(self, credential_id: str) -> dict[str, Any] | None:
        credential = self.repo.get_credential(credential_id)
        if credential is None:
            return None
        return _credential_audit_snapshot(credential)

    def credential_create_audit_details(
        self,
        credential: ApiCredentialRead,
    ) -> dict[str, Any]:
        return {
            "label": credential.label,
            "providerType": credential.provider_type,
            "providerGroup": _provider_host_label(credential.base_url),
            "modelName": credential.model_name,
            "status": credential.status,
            "autoAssignEnabled": credential.auto_assign_enabled,
            "priority": credential.priority,
            "timeoutSeconds": credential.timeout_seconds,
            "temperatureEnabled": credential.temperature_enabled,
            "maxConcurrency": credential.max_concurrency,
        }

    def provider_group_audit_snapshot(self, provider_group: str) -> list[dict[str, Any]]:
        return [
            _credential_audit_snapshot(credential)
            | {"id": credential.id}
            for credential in self.repo.list_credentials()
            if _provider_host_label(credential.base_url) == provider_group
        ]

    def credential_update_audit_details(
        self,
        before: dict[str, Any] | None,
        after: ApiCredentialRead,
        *,
        api_key_changed: bool = False,
    ) -> dict[str, Any]:
        after_snapshot = {
            "label": after.label,
            "providerType": after.provider_type,
            "providerGroup": _provider_host_label(after.base_url),
            "baseUrl": after.base_url,
            "modelName": after.model_name,
            "status": after.status,
            "autoAssignEnabled": after.auto_assign_enabled,
            "priority": after.priority,
            "timeoutSeconds": after.timeout_seconds,
            "temperature": after.temperature,
            "temperatureEnabled": after.temperature_enabled,
            "maxConcurrency": after.max_concurrency,
        }
        before = before or {}
        changed_fields = [
            field
            for field, value in after_snapshot.items()
            if before.get(field) != value
        ]
        if api_key_changed:
            changed_fields.append("apiKey")
        return {
            "changedFields": changed_fields,
            "before": {field: before.get(field) for field in changed_fields if field != "apiKey"},
            "after": {
                field: after_snapshot.get(field)
                for field in changed_fields
                if field != "apiKey"
            },
            "apiKeyChanged": api_key_changed,
        }

    def record_runtime_attempt(
        self,
        credential_id: str,
        *,
        task: str | None = None,
        status: str,
        duration_ms: int,
        error_summary: str | None,
        error_code: str | None = None,
    ) -> None:
        if self.trace_session_factory is not None:
            with self.trace_session_factory() as runtime_db:
                runtime_service = ApiCenterService(runtime_db)
                runtime_service.record_runtime_attempt(
                    credential_id,
                    task=task,
                    status=status,
                    duration_ms=duration_ms,
                    error_summary=error_summary,
                    error_code=error_code,
                )
                runtime_service.uow.commit()
            return
        credential = self.repo.get_credential(credential_id)
        if not credential:
            return
        credential.last_status = status
        credential.last_latency_ms = duration_ms
        credential.last_error = error_summary
        checked_at = datetime.now(timezone.utc)
        credential.last_checked_at = checked_at
        if task:
            credential.capability_profile_json = _capability_profile_with_result(
                credential.capability_profile_json,
                task=task,
                status=status,
                duration_ms=duration_ms,
                error_summary=error_summary,
                checked_at=checked_at,
                error_code=error_code,
            )
        _CAPACITY_TRACKER.record(credential_id, status=status, duration_ms=duration_ms)
        credential.updated_at = checked_at
        self.db.flush()

    def create_credential(
        self,
        payload: ApiCredentialCreate,
        *,
        actor_user_id: str | None,
        require_probe: bool = False,
    ) -> ApiCredentialRead:
        self.normalize_legacy_credential_fingerprints()
        api_key = payload.api_key.strip()
        if not api_key:
            raise AppError("api_key_required", "API key 不能为空")
        provider_type = _validate_provider_type(payload.provider_type)
        base_url = _validate_api_base_url(payload.base_url)
        model_name = _validate_model_name(payload.model_name)
        api_key_fingerprint = _api_key_fingerprint(api_key)
        self._ensure_unique_inventory_identity(
            provider_type=provider_type,
            base_url=base_url,
            model_name=model_name,
            api_key_fingerprint=api_key_fingerprint,
        )
        selected_temperature = payload.temperature
        selected_temperature_enabled = payload.temperature_enabled
        capability_profile_json = "{}"
        last_status: str | None = None
        last_latency_ms: int | None = None
        last_error: str | None = None
        last_checked_at: datetime | None = None
        if require_probe and payload.status == "active":
            probe = self._probe_credential_before_save(
                label=payload.label,
                provider_type=provider_type,
                base_url=base_url,
                model_name=model_name,
                api_key=api_key,
                temperature=payload.temperature,
                temperature_enabled=payload.temperature_enabled,
                task=_representative_task_for_scope(payload.task_scope),
            )
            selected_temperature = (
                probe.temperature
                if probe.temperature is not None
                else payload.temperature
            )
            selected_temperature_enabled = probe.temperature_enabled
            probe_checked_at = datetime.now(timezone.utc)
            capability_profile_json = _capability_profile_with_result(
                "{}",
                task=_representative_task_for_scope(payload.task_scope),
                status=probe.status,
                duration_ms=probe.duration_ms,
                error_summary=None,
                checked_at=probe_checked_at,
            )
            last_status = probe.status
            last_latency_ms = probe.duration_ms
            last_checked_at = probe_checked_at
        credential = self.repo.add_credential(
            ModelApiCredential(
                label=_bounded(payload.label, 120),
                provider_type=provider_type,
                base_url=base_url,
                model_name=model_name,
                api_key_secret=api_key,
                api_key_fingerprint=api_key_fingerprint,
                api_key_preview=_api_key_preview(api_key),
                task_scope_json=json.dumps(payload.task_scope, ensure_ascii=False),
                status=payload.status,
                priority=payload.priority,
                timeout_seconds=max(0.5, payload.timeout_seconds),
                temperature=selected_temperature,
                temperature_enabled=selected_temperature_enabled,
                max_concurrency=normalize_max_concurrency(payload.max_concurrency),
                auto_assign_enabled=payload.auto_assign_enabled,
                capability_profile_json=capability_profile_json,
                last_status=last_status,
                last_latency_ms=last_latency_ms,
                last_error=last_error,
                last_checked_at=last_checked_at,
                created_by=actor_user_id,
            )
        )
        self.repo.set_setting(ENV_IMPORT_SETTING_KEY, "true")
        self.uow.commit()
        return self._credential_read(credential)

    def _ensure_unique_inventory_identity(
        self,
        *,
        provider_type: str,
        base_url: str,
        model_name: str,
        api_key_fingerprint: str,
        exclude_id: str | None = None,
    ) -> None:
        duplicate = self.repo.find_credential_by_inventory_identity(
            provider_type=provider_type,
            base_url=base_url,
            model_name=model_name,
            api_key_fingerprint=api_key_fingerprint,
            exclude_id=exclude_id,
        )
        if duplicate is None:
            return
        raise ConflictError(
            "api_credential_duplicate",
            f"同一个中转站、模型和密钥已存在：{duplicate.label}",
        )

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
        error_code: str | None = None,
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
                    error_code=error_code,
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
                error_code=_bounded(error_code or "", 80) or None,
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
        *,
        require_probe: bool = False,
    ) -> ApiCredentialRead:
        self.normalize_legacy_credential_fingerprints()
        credential = self.repo.get_credential(credential_id)
        if not credential:
            raise NotFoundError("api_credential_not_found", "API key 不存在")
        next_provider_type = (
            _validate_provider_type(payload.provider_type)
            if payload.provider_type is not None
            else credential.provider_type
        )
        next_base_url = (
            _validate_api_base_url(payload.base_url)
            if payload.base_url is not None
            else credential.base_url
        )
        next_model_name = (
            _validate_model_name(payload.model_name)
            if payload.model_name is not None
            else credential.model_name
        )
        next_api_key = (
            payload.api_key.strip()
            if payload.api_key is not None and payload.api_key.strip()
            else credential.api_key_secret
        )
        next_api_key_fingerprint = _api_key_fingerprint(next_api_key)
        self._ensure_unique_inventory_identity(
            provider_type=next_provider_type,
            base_url=next_base_url,
            model_name=next_model_name,
            api_key_fingerprint=next_api_key_fingerprint,
            exclude_id=credential.id,
        )
        next_status = payload.status if payload.status is not None else credential.status
        next_temperature = (
            payload.temperature if payload.temperature is not None else credential.temperature
        )
        next_temperature_enabled = (
            payload.temperature_enabled
            if payload.temperature_enabled is not None
            else credential.temperature_enabled
        )
        critical_changed = any(
            (
                payload.provider_type is not None
                and next_provider_type != credential.provider_type,
                payload.base_url is not None
                and next_base_url != credential.base_url,
                payload.model_name is not None
                and next_model_name != credential.model_name,
                payload.api_key is not None and payload.api_key.strip(),
                payload.temperature is not None
                and next_temperature != credential.temperature,
                payload.temperature_enabled is not None
                and next_temperature_enabled != credential.temperature_enabled,
                payload.status == "active" and credential.status != "active",
            )
        )
        probe: _CredentialSaveProbeResult | None = None
        if require_probe and critical_changed and next_status == "active":
            probe = self._probe_credential_before_save(
                label=payload.label or credential.label,
                provider_type=next_provider_type,
                base_url=next_base_url,
                model_name=next_model_name,
                api_key=next_api_key,
                temperature=next_temperature,
                temperature_enabled=next_temperature_enabled,
                task=_representative_task_for_scope(
                    payload.task_scope
                    if payload.task_scope is not None
                    else _loads_list(credential.task_scope_json)
                ),
            )
            next_temperature = (
                probe.temperature
                if probe.temperature is not None
                else next_temperature
            )
            next_temperature_enabled = probe.temperature_enabled
        if payload.label is not None:
            credential.label = _bounded(payload.label, 120)
        if payload.provider_type is not None:
            credential.provider_type = next_provider_type
        if payload.base_url is not None:
            credential.base_url = next_base_url
        if payload.model_name is not None:
            credential.model_name = next_model_name
        if payload.api_key is not None and payload.api_key.strip():
            credential.api_key_secret = next_api_key
            credential.api_key_fingerprint = next_api_key_fingerprint
            credential.api_key_preview = _api_key_preview(next_api_key)
        if payload.task_scope is not None:
            credential.task_scope_json = json.dumps(payload.task_scope, ensure_ascii=False)
        if payload.status is not None:
            credential.status = next_status
        if payload.priority is not None:
            credential.priority = payload.priority
        if payload.timeout_seconds is not None:
            credential.timeout_seconds = max(0.5, payload.timeout_seconds)
        if payload.temperature is not None:
            credential.temperature = next_temperature
        if payload.temperature_enabled is not None:
            credential.temperature_enabled = next_temperature_enabled
        if payload.max_concurrency is not None:
            credential.max_concurrency = normalize_max_concurrency(payload.max_concurrency)
        if payload.auto_assign_enabled is not None:
            credential.auto_assign_enabled = payload.auto_assign_enabled
        if critical_changed:
            if probe:
                probe_checked_at = datetime.now(timezone.utc)
                credential.capability_profile_json = _capability_profile_with_result(
                    "{}",
                    task=_representative_task_for_scope(
                        payload.task_scope
                        if payload.task_scope is not None
                        else _loads_list(credential.task_scope_json)
                    ),
                    status=probe.status,
                    duration_ms=probe.duration_ms,
                    error_summary=None,
                    checked_at=probe_checked_at,
                )
                credential.last_status = probe.status
                credential.last_latency_ms = probe.duration_ms
                credential.last_error = None
                credential.last_checked_at = probe_checked_at
            else:
                credential.capability_profile_json = "{}"
                credential.last_status = None
                credential.last_latency_ms = None
                credential.last_error = None
                credential.last_checked_at = None
        credential.updated_at = datetime.now(timezone.utc)
        self.uow.commit()
        return self._credential_read(credential)

    def _probe_credential_before_save(
        self,
        *,
        label: str,
        provider_type: str,
        base_url: str,
        model_name: str,
        api_key: str,
        temperature: float,
        temperature_enabled: bool,
        task: ModelTaskName,
    ) -> _CredentialSaveProbeResult:
        if provider_type != "openai_compatible":
            raise AppError(
                "unsupported_provider_type",
                "当前只支持 OpenAI-compatible API 协议",
            )
        credential = ModelApiCredential(
            id="save-probe",
            label=_bounded(label, 120) or "未保存 API",
            provider_type=provider_type,
            base_url=base_url,
            model_name=model_name,
            api_key_secret=api_key,
            api_key_preview=_api_key_preview(api_key),
            task_scope_json=json.dumps([task], ensure_ascii=False),
            status="active",
            priority=100,
            timeout_seconds=HEALTH_PROBE_TIMEOUT_SECONDS,
            temperature=temperature,
            temperature_enabled=temperature_enabled,
            max_concurrency=1,
            auto_assign_enabled=True,
        )
        pending_settings = _temperature_probe_settings(
            temperature,
            None,
            temperature_enabled=temperature_enabled,
        )
        last_error = "API 入库验证失败"
        last_error_code = "api_probe_failed"
        while pending_settings:
            probe_temperature, probe_temperature_enabled = pending_settings.pop(0)
            for probe_index in range(HEALTH_PROBE_MAX_ATTEMPTS):
                status, error, duration_ms, _, error_code = self._run_health_probe(
                    credential,
                    task=task,
                    timeout_seconds=HEALTH_PROBE_TIMEOUT_SECONDS,
                    temperature=probe_temperature,
                )
                if status == "ok":
                    return _CredentialSaveProbeResult(
                        status=status,
                        duration_ms=duration_ms,
                        temperature=probe_temperature,
                        temperature_enabled=probe_temperature_enabled,
                    )
                last_error = error or last_error
                last_error_code = error_code or last_error_code
                if (
                    error_code not in TRANSIENT_HEALTH_ERROR_CODES
                    or probe_index + 1 >= HEALTH_PROBE_MAX_ATTEMPTS
                ):
                    break
            if last_error_code == "temperature_not_supported":
                pending_settings = [(None, False)]
                continue
            if last_error_code == "temperature_value_unsupported":
                continue
            raise AppError(last_error_code, last_error)
        raise AppError(last_error_code, last_error)

    def delete_credential(self, credential_id: str) -> None:
        credential = self.repo.get_credential(credential_id)
        if not credential:
            raise NotFoundError("api_credential_not_found", "API key 不存在")
        for slot in self.repo.list_slots():
            changed = False
            if slot.primary_credential_id == credential_id:
                slot.primary_credential_id = None
                changed = True
            backup_ids = [
                item
                for item in _loads_list(slot.backup_credential_ids_json)
                if item != credential_id
            ]
            if backup_ids != _loads_list(slot.backup_credential_ids_json):
                slot.backup_credential_ids_json = json.dumps(backup_ids, ensure_ascii=False)
                changed = True
            excluded_ids = [
                item
                for item in _loads_list(slot.excluded_credential_ids_json)
                if item != credential_id
            ]
            if excluded_ids != _loads_list(slot.excluded_credential_ids_json):
                slot.excluded_credential_ids_json = json.dumps(
                    excluded_ids,
                    ensure_ascii=False,
                )
                changed = True
            if changed:
                slot.updated_at = datetime.now(timezone.utc)
        _CAPACITY_TRACKER.discard(credential_id)
        self.repo.delete_credential(credential)
        self.repo.set_setting(ENV_IMPORT_SETTING_KEY, "true")
        self.uow.commit()

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
            if payload.primary_credential_id:
                _ensure_credential_can_be_assigned(
                    credentials[payload.primary_credential_id],
                    "主 API",
                )
            slot.primary_credential_id = payload.primary_credential_id or None
        if payload.backup_credential_ids is not None:
            backup_ids = []
            for credential_id in payload.backup_credential_ids:
                if credential_id not in credentials:
                    raise AppError("credential_not_found", "备用 API key 不存在")
                _ensure_credential_can_be_assigned(
                    credentials[credential_id],
                    "备用 API",
                )
                if credential_id not in backup_ids:
                    backup_ids.append(credential_id)
            slot.backup_credential_ids_json = json.dumps(backup_ids, ensure_ascii=False)
        if payload.excluded_credential_ids is not None:
            excluded_ids = []
            for credential_id in payload.excluded_credential_ids:
                if credential_id not in credentials:
                    raise AppError("credential_not_found", "屏蔽 API key 不存在")
                if credential_id not in excluded_ids:
                    excluded_ids.append(credential_id)
            slot.excluded_credential_ids_json = json.dumps(excluded_ids, ensure_ascii=False)
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
        total_duration_ms = 0
        successful_duration_ms = 0
        provider_attempts: tuple[dict[str, Any], ...] = ()
        for probe_index in range(HEALTH_PROBE_MAX_ATTEMPTS):
            status, error, duration_ms, attempts, error_code = self._run_health_probe(
                credential,
                task=payload.task,
                timeout_seconds=HEALTH_PROBE_TIMEOUT_SECONDS,
                temperature=(
                    credential.temperature if credential.temperature_enabled else None
                ),
            )
            total_duration_ms += duration_ms
            provider_attempts += attempts
            if status == "ok":
                successful_duration_ms = duration_ms
                break
            if (
                error_code not in TRANSIENT_HEALTH_ERROR_CODES
                or probe_index + 1 >= HEALTH_PROBE_MAX_ATTEMPTS
            ):
                break
        if status == "ok":
            credential.timeout_seconds = max(
                credential.timeout_seconds,
                _recommended_api_call_timeout_seconds(successful_duration_ms),
            )
        elif error_code in {"response_timeout", "provider_timeout"}:
            error = (
                "健康探测自动重试后仍未收到完整响应，"
                "后续巡检会自动重试"
            )
        elif error_code in TRANSIENT_HEALTH_ERROR_CODES:
            error = f"{error or '模型服务暂时不可用'}；系统已自动重试，本轮仍未通过"
        check = self._persist_health_probe(
            credential,
            task=payload.task,
            status=status,
            error=error,
            duration_ms=total_duration_ms,
            provider_attempts=provider_attempts,
            layer_name="健康检查",
            output_kind="health_check",
            error_code=error_code,
        )
        self.uow.commit()
        return check

    def tune_credential_temperature(
        self,
        credential_id: str,
        payload: ApiTemperatureTuneRequest,
    ) -> ApiTemperatureTuneResult:
        credential = self.repo.get_credential(credential_id)
        if not credential:
            raise NotFoundError("api_credential_not_found", "API key 不存在")
        task = payload.task or _representative_task(credential)
        timeout_seconds = max(
            0.5,
            min(payload.timeout_seconds or credential.timeout_seconds, 30.0),
        )
        previous_temperature = credential.temperature
        previous_temperature_enabled = credential.temperature_enabled
        probes: list[ApiTemperatureProbeRead] = []
        selected_temperature: float | None = None
        selected_temperature_enabled: bool | None = None
        pending_settings = _temperature_probe_settings(
            previous_temperature,
            payload.candidate_temperatures,
            temperature_enabled=previous_temperature_enabled,
        )
        while pending_settings and len(probes) < TEMPERATURE_PROBE_MAX_CANDIDATES:
            temperature, temperature_enabled = pending_settings.pop(0)
            status, error, duration_ms, provider_attempts, error_code = (
                self._run_health_probe(
                    credential,
                    task=task,
                    timeout_seconds=timeout_seconds,
                    temperature=temperature,
                )
            )
            check = self._persist_health_probe(
                credential,
                task=task,
                status=status,
                error=error,
                duration_ms=duration_ms,
                provider_attempts=provider_attempts,
                layer_name="温度探测",
                output_kind="temperature_probe",
                error_code=error_code,
            )
            probes.append(
                ApiTemperatureProbeRead(
                    temperature=temperature,
                    temperature_enabled=temperature_enabled,
                    status=status,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    **_error_classification_fields(error_code),
                    error_summary=error,
                    checked_at=check.checked_at,
                )
            )
            if status == "ok":
                selected_temperature = temperature
                selected_temperature_enabled = temperature_enabled
                break
            if error_code == "temperature_not_supported":
                pending_settings = [(None, False)]
            elif error_code != "temperature_value_unsupported":
                break
        if selected_temperature_enabled is not None and payload.persist:
            if selected_temperature is not None:
                credential.temperature = selected_temperature
            credential.temperature_enabled = selected_temperature_enabled
            credential.updated_at = datetime.now(timezone.utc)
        self.uow.commit()
        return ApiTemperatureTuneResult(
            credential_id=credential.id,
            credential_label=credential.label,
            status="ok" if selected_temperature_enabled is not None else "failed",
            previous_temperature=previous_temperature,
            previous_temperature_enabled=previous_temperature_enabled,
            selected_temperature=selected_temperature,
            selected_temperature_enabled=selected_temperature_enabled,
            probes=probes,
        )

    def probe_credential_temperature(
        self,
        payload: ApiTemperatureProbeRequest,
    ) -> ApiTemperatureTuneResult:
        api_key = payload.api_key.strip()
        if not api_key:
            raise AppError("api_key_required", "API key 不能为空")
        base_url = _validate_api_base_url(payload.base_url)
        model_name = _validate_model_name(payload.model_name)
        credential = ModelApiCredential(
            id="temperature-probe",
            label="未保存 API",
            provider_type="openai_compatible",
            base_url=base_url,
            model_name=model_name,
            api_key_secret=api_key,
            api_key_preview=_api_key_preview(api_key),
            task_scope_json=json.dumps([payload.task], ensure_ascii=False),
            status="active",
            priority=100,
            timeout_seconds=max(0.5, payload.timeout_seconds or 20.0),
            temperature=payload.temperature,
            temperature_enabled=True,
            max_concurrency=1,
            auto_assign_enabled=True,
        )
        probes: list[ApiTemperatureProbeRead] = []
        selected_temperature: float | None = None
        selected_temperature_enabled: bool | None = None
        timeout_seconds = max(
            0.5,
            min(
                payload.timeout_seconds or credential.timeout_seconds,
                TEMPERATURE_PROBE_TIMEOUT_SECONDS,
            ),
        )
        pending_settings = _temperature_probe_settings(
            payload.temperature,
            payload.candidate_temperatures,
            temperature_enabled=True,
        )
        while pending_settings and len(probes) < TEMPERATURE_PROBE_MAX_CANDIDATES:
            temperature, temperature_enabled = pending_settings.pop(0)
            status, error, duration_ms, _, error_code = self._run_health_probe(
                credential,
                task=payload.task,
                timeout_seconds=timeout_seconds,
                temperature=temperature,
            )
            probes.append(
                ApiTemperatureProbeRead(
                    temperature=temperature,
                    temperature_enabled=temperature_enabled,
                    status=status,
                    duration_ms=duration_ms,
                    error_code=error_code,
                    **_error_classification_fields(error_code),
                    error_summary=error,
                    checked_at=datetime.now(timezone.utc),
                )
            )
            if status == "ok":
                selected_temperature = temperature
                selected_temperature_enabled = temperature_enabled
                break
            if error_code == "temperature_not_supported":
                pending_settings = [(None, False)]
            elif error_code != "temperature_value_unsupported":
                break
        return ApiTemperatureTuneResult(
            credential_id="",
            credential_label=None,
            status="ok" if selected_temperature_enabled is not None else "failed",
            previous_temperature=payload.temperature,
            previous_temperature_enabled=True,
            selected_temperature=selected_temperature,
            selected_temperature_enabled=selected_temperature_enabled,
            probes=probes,
        )

    def _run_health_probe(
        self,
        credential: ModelApiCredential,
        *,
        task: ModelTaskName,
        timeout_seconds: float,
        temperature: float | None,
    ) -> tuple[str, str | None, int, tuple[dict[str, Any], ...], str | None]:
        started = time.monotonic()
        status = "failed"
        error = None
        error_code = None
        provider_attempts: tuple[dict[str, Any], ...] = ()
        try:
            provider = OpenAICompatibleModelProvider(
                base_url=credential.base_url,
                api_key=credential.api_key_secret,
                model_name=credential.model_name,
                timeout_seconds=int(max(1, timeout_seconds)),
                temperature=temperature,
            )
            with _health_probe_request(
                task=task,
                timeout_seconds=timeout_seconds,
            ) as probe_request:
                call = provider.generate_json(probe_request)
            provider_attempts = call.attempts
            result = call.value
            if not isinstance(result, dict):
                raise AppError("invalid_model_response", "模型没有返回 JSON 对象")
            status = "ok"
        except Exception as exc:
            status = _status_for_exception(exc)
            error = _safe_error(exc)
            error_code = _provider_error_code(exc)
            provider_attempts = _error_attempts(exc)
        return status, error, _elapsed_ms(started), provider_attempts, error_code

    def _persist_health_probe(
        self,
        credential: ModelApiCredential,
        *,
        task: str,
        status: str,
        error: str | None,
        duration_ms: int,
        provider_attempts: tuple[dict[str, Any], ...],
        layer_name: str,
        output_kind: str,
        error_code: str | None = None,
    ) -> ApiHealthCheckRead:
        attempts = _health_check_attempts(
            provider_attempts,
            credential=credential,
            task=task,
            status=status,
            duration_ms=duration_ms,
            error=error or "",
            layer_name=layer_name,
            error_code=error_code,
        )
        check = self.repo.add_health_check(
            ModelApiHealthCheck(
                credential_id=credential.id,
                task=task,
                status=status,
                duration_ms=duration_ms,
                error_code=_bounded(error_code or "", 80) or None,
                error_summary=error,
            )
        )
        self.record_call_traces_from_attempts(
            search_log_id=None,
            request_id=None,
            branches=[
                {
                    "source": layer_name,
                    "status": status,
                    "attempts": attempts,
                }
            ],
            persist=True,
            output_kind=output_kind,
        )
        credential.last_status = status
        credential.last_latency_ms = duration_ms
        credential.last_error = error
        credential.last_checked_at = check.checked_at
        credential.capability_profile_json = _capability_profile_with_result(
            credential.capability_profile_json,
            task=task,
            status=status,
            duration_ms=duration_ms,
            error_summary=error,
            checked_at=check.checked_at,
            error_code=error_code,
        )
        _CAPACITY_TRACKER.record(credential.id, status=status, duration_ms=duration_ms)
        return self._health_check_read(check, [credential])

    def run_health_checks(
        self,
        payload: ApiHealthCheckRunRequest,
    ) -> ApiHealthCheckRunResult:
        self.initialize_runtime()
        credentials = [
            credential
            for credential in self.repo.list_credentials()
            if payload.include_disabled or credential.status != "disabled"
        ]
        probe_targets: list[_HealthProbeTarget] = [
            _HealthProbeTarget(
                credential_id=credential.id,
                task=payload.task or _representative_task(credential),
                provider_group=_provider_host_label(credential.base_url),
            )
            for credential in credentials
        ]
        bind = self.db.get_bind()
        can_run_in_parallel = (
            self.trace_session_factory is not None
            and getattr(getattr(bind, "dialect", None), "name", None) != "sqlite"
            and len(probe_targets) > 1
        )
        if can_run_in_parallel:
            session_factory = self.trace_session_factory
            assert session_factory is not None

            def run_probe(target: _HealthProbeTarget) -> ApiHealthCheckRead:
                with session_factory() as probe_db:
                    return ApiCenterService(
                        probe_db,
                        trace_session_factory=session_factory,
                    ).test_credential(
                        target.credential_id,
                        ApiHealthCheckCreate(
                            task=target.task,
                            timeout_seconds=payload.timeout_seconds,
                        ),
                    )

            def run_probe_group(
                targets: list[_HealthProbeTarget],
            ) -> list[ApiHealthCheckRead]:
                return [run_probe(target) for target in targets]

            target_groups = _group_health_probe_targets_by_provider(probe_targets)
            with ThreadPoolExecutor(
                max_workers=min(HEALTH_CHECK_MAX_WORKERS, len(target_groups))
            ) as executor:
                checks = [
                    check
                    for group_checks in executor.map(run_probe_group, target_groups)
                    for check in group_checks
                ]
        else:
            checks = [
                self.test_credential(
                    target.credential_id,
                    ApiHealthCheckCreate(
                        task=target.task,
                        timeout_seconds=payload.timeout_seconds,
                    ),
                )
                for target in probe_targets
            ]
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
                trace_service = ApiCenterService(trace_db)
                added = trace_service.record_call_traces_from_attempts(
                    search_log_id=search_log_id,
                    request_id=request_id,
                    branches=branches,
                    persist=True,
                    output_kind=output_kind,
                )
                trace_service.uow.commit()
                return added
        if search_log_id is None and request_id:
            search_log_id = self.repo.get_search_log_id_by_request_id(request_id)
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
                        error_code=(
                            _bounded(
                                str(
                                    attempt.get("error_code")
                                    or attempt.get("errorCode")
                                    or ""
                                ),
                                80,
                            )
                            or None
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
        max_concurrency = normalize_max_concurrency(item.max_concurrency)
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
            temperature_enabled=item.temperature_enabled,
            max_concurrency=max_concurrency,
            auto_assign_enabled=item.auto_assign_enabled,
            capability_profile=_capability_reads(item.capability_profile_json),
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
        excluded_ids = _loads_list(item.excluded_credential_ids_json)
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
            excluded_credential_ids=excluded_ids,
            excluded_credential_labels=[labels.get(item, item) for item in excluded_ids],
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
            error_code=item.error_code,
            **_error_classification_fields(item.error_code),
            error_summary=item.error_summary,
            checked_at=item.checked_at,
        )

    def _call_trace_read(
        self,
        item: ModelCallTrace,
        *,
        search_context: tuple[str, int, bool] | None = None,
    ) -> ApiCallTraceRead:
        return ApiCallTraceRead(
            id=item.id,
            search_log_id=item.search_log_id,
            request_id=item.request_id,
            search_keyword=search_context[0] if search_context else None,
            search_result_count=search_context[1] if search_context else None,
            search_timed_out=search_context[2] if search_context else None,
            task=item.task,
            layer_name=item.layer_name,
            credential_id=item.credential_id,
            credential_label=item.credential_label,
            provider=item.provider,
            model=item.model,
            status=item.status,
            duration_ms=item.duration_ms,
            fallback_index=item.fallback_index,
            error_code=item.error_code,
            **_error_classification_fields(item.error_code),
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
        *,
        default_request_id: str | None = None,
    ) -> None:
        self.api_center = api_center
        self.default_request_id = default_request_id

    @property
    def configured(self) -> bool:
        return any(
            credential.status == "active"
            for credential in self.api_center.repo.list_credentials()
        )

    @property
    def attempt_count(self) -> int:
        # The scheduler owns internal fallbacks; outer search budgets should not be
        # multiplied by the number of keys, otherwise slow providers stretch the
        # whole search chain.
        return 1

    def generate_json(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[dict[str, Any]]:
        return self._run(request)

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any],
    ) -> ModelCallResult[Any]:
        return self._run(request, validator=validator)

    def _run(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any] | None = None,
    ) -> ModelCallResult[Any]:
        if request.request_id is None and self.default_request_id:
            request = replace(request, request_id=self.default_request_id)
        attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
        if request.cancellation is not None and request.cancellation.cancelled:
            self._raise_cancelled(request)
        selection_snapshot = self.api_center.scheduler_selection_snapshot()
        slot, credentials = self.api_center.select_credentials_for_task(
            request.task,
            snapshot=selection_snapshot,
        )
        if not credentials:
            return self._run_unconfigured(request)

        total_timeout = _task_timeout(request, slot)
        deadline = time.monotonic() + total_timeout
        max_parallel = _scheduler_max_parallel(slot)
        hedging_delay_seconds = _scheduler_hedging_delay_seconds(slot)
        attempted_credential_ids: set[str] = set()
        active_attempts: dict[Future[_ScheduledAttemptOutcome], _RunningScheduledAttempt] = {}
        fallback_index = 0
        next_launch_at = time.monotonic()
        executor = ThreadPoolExecutor(max_workers=max_parallel)
        try:
            while time.monotonic() < deadline:
                if request.cancellation is not None and request.cancellation.cancelled:
                    _cancel_active_attempts(
                        running.cancellation for running in active_attempts.values()
                    )
                    self._raise_cancelled(request)
                _, credentials = self.api_center.select_credentials_for_task(
                    request.task,
                    snapshot=selection_snapshot,
                )
                pending_credentials = [
                    credential
                    for credential in credentials
                    if credential.id not in attempted_credential_ids
                ]
                if not pending_credentials and not active_attempts:
                    break
                launched = False
                while (
                    pending_credentials
                    and len(active_attempts) < max_parallel
                    and time.monotonic() >= next_launch_at
                ):
                    credential = pending_credentials.pop(0)
                    if not _CAPACITY_TRACKER.try_acquire(
                        credential.id,
                        normalize_max_concurrency(credential.max_concurrency),
                    ):
                        continue
                    attempted_credential_ids.add(credential.id)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        _CAPACITY_TRACKER.release(credential.id)
                        break
                    attempt_timeout = _scheduled_attempt_timeout_seconds(
                        credential,
                        task=request.task,
                        remaining_seconds=remaining,
                        remaining_candidate_count=max(
                            0,
                            len(credentials) - len(attempted_credential_ids),
                        ),
                    )
                    attempt_cancellation = CancellationSignal()
                    future = executor.submit(
                        self._run_single_attempt,
                        request,
                        credential,
                        fallback_index,
                        attempt_timeout,
                        attempt_cancellation,
                        validator,
                    )
                    active_attempts[future] = _RunningScheduledAttempt(
                        credential=credential,
                        fallback_index=fallback_index,
                        started_at=time.monotonic(),
                        cancellation=attempt_cancellation,
                    )
                    fallback_index += 1
                    launched = True
                    next_launch_at = (
                        time.monotonic() + hedging_delay_seconds
                        if hedging_delay_seconds > 0
                        else time.monotonic()
                    )
                if launched:
                    continue
                if not active_attempts:
                    wait_seconds = min(
                        SCHEDULER_IDLE_WAIT_SECONDS,
                        max(0.0, deadline - time.monotonic()),
                    )
                    if request.cancellation is not None:
                        request.cancellation.wait(wait_seconds)
                    else:
                        time.sleep(wait_seconds)
                    continue

                wait_seconds = max(0.0, deadline - time.monotonic())
                if pending_credentials and len(active_attempts) < max_parallel:
                    wait_seconds = min(
                        wait_seconds,
                        max(0.0, next_launch_at - time.monotonic()),
                    )
                if request.cancellation is not None:
                    wait_seconds = min(wait_seconds, SCHEDULER_IDLE_WAIT_SECONDS)
                completed, _ = wait(
                    tuple(active_attempts),
                    timeout=wait_seconds,
                    return_when=FIRST_COMPLETED,
                )
                if not completed:
                    continue
                for future in completed:
                    active_attempts.pop(future, None)
                    outcome = future.result()
                    current_attempts = _scheduled_attempts(
                        outcome.provider_attempts,
                        credential=outcome.credential,
                        fallback_index=outcome.fallback_index,
                        status=outcome.status,
                        duration_ms=outcome.duration_ms,
                        task=request.task,
                        error=outcome.error_summary or "",
                        error_code=outcome.error_code,
                    )
                    attempts.extend(current_attempts)
                    self._record_traces(request, current_attempts, status=outcome.status)
                    self.api_center.record_runtime_attempt(
                        outcome.credential.id,
                        task=request.task,
                        status=outcome.status,
                        duration_ms=outcome.duration_ms,
                        error_summary=outcome.error_summary,
                        error_code=outcome.error_code,
                    )
                    if outcome.status == "ok":
                        _cancel_active_attempts(
                            running.cancellation for running in active_attempts.values()
                        )
                        executor.shutdown(wait=False, cancel_futures=True)
                        return ModelCallResult(outcome.result, tuple(attempts))
                    last_error = outcome.error
                    if not active_attempts:
                        next_launch_at = time.monotonic()
                    if isinstance(outcome.error, ModelProviderCancelled) and (
                        request.cancellation is not None
                        and request.cancellation.cancelled
                    ):
                        _cancel_active_attempts(
                            running.cancellation for running in active_attempts.values()
                        )
                        self._raise_cancelled(request)
        finally:
            _cancel_active_attempts(
                running.cancellation for running in active_attempts.values()
            )
            executor.shutdown(wait=False, cancel_futures=True)

        if active_attempts:
            budget_attempts = _scheduler_budget_timeout_attempts(
                request,
                active_attempts.values(),
            )
            attempts.extend(budget_attempts)
            self._record_traces(request, budget_attempts, status="timed_out")
            for running in active_attempts.values():
                self.api_center.record_runtime_attempt(
                    running.credential.id,
                    task=request.task,
                    status="timed_out",
                    duration_ms=_elapsed_ms(running.started_at),
                    error_summary="任务预算已用尽，本机已停止等待该候选 API",
                    error_code="scheduler_budget_exhausted",
                )
            active_attempts.clear()

        if attempts:
            raise ModelProviderError(
                f"API 中心调度的 {len(attempts)} 次模型调用均失败："
                f"{_format_attempts(attempts)}",
                attempts=tuple(attempts),
            ) from last_error
        timeout_attempt = _scheduler_terminal_attempt(
            request,
            status="timed_out",
            error="API 中心可用 API 当前都已达到并发上限，超过任务时间预算",
            duration_ms=round(total_timeout * 1000),
            error_code="scheduler_capacity_timeout",
        )
        self._record_traces(request, [timeout_attempt], status="timed_out")
        raise ModelProviderError(
            "API 中心可用 API 当前都已达到并发上限，请稍后重试",
            attempts=(timeout_attempt,),
        )

    def _run_single_attempt(
        self,
        request: ModelRequest,
        credential: ModelApiCredential,
        fallback_index: int,
        attempt_timeout: float,
        attempt_cancellation: CancellationSignal,
        validator: Callable[[dict[str, Any]], Any] | None,
    ) -> _ScheduledAttemptOutcome:
        provider = OpenAICompatibleModelProvider(
            base_url=credential.base_url,
            api_key=credential.api_key_secret,
            model_name=credential.model_name,
            timeout_seconds=int(max(1, attempt_timeout)),
            temperature=credential.temperature if credential.temperature_enabled else None,
        )
        started = time.monotonic()
        call: ModelCallResult[dict[str, Any]] | None = None
        try:
            attempt_request = replace(
                request,
                timeout_seconds=max(0.5, attempt_timeout),
                cancellation=attempt_cancellation,
            )
            call = provider.generate_json(attempt_request)
            payload = call.value
            result = validator(payload) if validator else payload
            return _ScheduledAttemptOutcome(
                credential=credential,
                fallback_index=fallback_index,
                status="ok",
                duration_ms=_elapsed_ms(started),
                provider_attempts=call.attempts,
                result=result,
            )
        except Exception as exc:
            return _ScheduledAttemptOutcome(
                credential=credential,
                fallback_index=fallback_index,
                status=_status_for_exception(exc),
                duration_ms=_elapsed_ms(started),
                provider_attempts=call.attempts if call is not None else _error_attempts(exc),
                error=exc,
                error_summary=_safe_error(exc),
                error_code=_provider_error_code(exc),
            )
        finally:
            _CAPACITY_TRACKER.release(credential.id)

    def _raise_cancelled(self, request: ModelRequest) -> NoReturn:
        attempt = _scheduler_terminal_attempt(
            request,
            status="timed_out",
            error="API 中心调度收到取消信号，未继续等待或尝试其他 API",
            duration_ms=0,
            error_code="scheduler_cancelled",
        )
        self._record_traces(request, [attempt], status="timed_out")
        raise ModelProviderCancelled(
            "API 中心模型调用已取消",
            attempts=(attempt,),
        )

    def _run_unconfigured(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[Any]:
        attempt = _scheduler_terminal_attempt(
            request,
            status="skipped",
            error="API 中心没有可用的已启用 API",
            duration_ms=0,
            error_code="api_center_unconfigured",
        )
        self._record_traces(request, [attempt], status="skipped")
        raise ModelProviderNotConfigured(
            "API 中心没有可用的已启用 API",
            attempts=(attempt,),
        )

    def _record_traces(
        self,
        request: ModelRequest,
        attempts: list[dict[str, Any]],
        *,
        status: str,
    ) -> None:
        self.api_center.record_call_traces_from_attempts(
            search_log_id=None,
            request_id=request.request_id,
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


def _api_key_fingerprint(api_key: str) -> str:
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()


def _bounded(value: str, limit: int) -> str:
    return value.strip()[:limit]


def _validate_api_base_url(value: str) -> str:
    base_url = _bounded(value, 500).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError("invalid_base_url", "API 地址必须是 http 或 https 开头的有效地址")
    if parsed.params or parsed.query or parsed.fragment:
        raise AppError("invalid_base_url", "API 地址不能包含查询参数或片段")
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[-2:] == ["chat", "completions"]:
        normalized_path = "/" + "/".join(path_parts[:-2]) if path_parts[:-2] else ""
        parsed = parsed._replace(path=normalized_path)
        base_url = urlunparse(parsed).rstrip("/")
    return base_url


def _validate_provider_type(value: str) -> str:
    provider_type = _bounded(value, 40) or "openai_compatible"
    if provider_type not in SUPPORTED_PROVIDER_TYPES:
        raise AppError(
            "unsupported_provider_type",
            "当前只支持 OpenAI-compatible API 协议",
        )
    return provider_type


def _validate_model_name(value: str) -> str:
    model_name = _bounded(value, 120)
    if not model_name:
        raise AppError("model_name_required", "模型不能为空")
    return model_name


def _ensure_credential_can_be_assigned(
    credential: ModelApiCredential,
    role: str,
) -> None:
    if credential_is_available(credential, require_auto_assign=False):
        return
    raise AppError(
        "credential_not_active",
        f"{role}「{credential.label}」未启用，不能指定到当前任务",
    )


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:300]


def _provider_error_code(exc: Exception) -> str | None:
    code = getattr(exc, "code", None)
    if code and code != "provider_error":
        return str(code)
    message = str(exc).lower()
    if "temperature" in message:
        if any(
            marker in message
            for marker in ("unsupported parameter", "does not support", "not support", "不接受参数")
        ):
            return "temperature_not_supported"
        return "temperature_value_unsupported"
    if "超时" in message or "timeout" in message or "timed out" in message:
        return "provider_timeout"
    return str(code) if code else None


def _error_classification_fields(error_code: str | None) -> dict[str, object]:
    classification = classify_api_error(error_code)
    if classification is None:
        return {
            "error_category": None,
            "error_severity": None,
            "error_retryable": None,
            "error_operator_action": None,
            "error_system_action": None,
        }
    return {
        "error_category": classification.category,
        "error_severity": classification.severity,
        "error_retryable": classification.retryable,
        "error_operator_action": classification.operator_action,
        "error_system_action": classification.system_action,
    }


def _maintenance_result_payload(result: ApiCenterMaintenanceRunResult) -> dict[str, object]:
    return {
        "last_started_at": result.started_at.isoformat(),
        "last_finished_at": result.finished_at.isoformat(),
        "last_status": result.status,
        "last_error": None,
        "last_checked_count": result.checked_count,
        "last_ok_count": result.ok_count,
        "last_failed_count": result.failed_count,
        "last_deleted_call_trace_count": result.deleted_call_trace_count,
        "last_deleted_health_check_count": result.deleted_health_check_count,
    }


def _status_for_exception(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, ModelProviderCancelled)):
        return "timed_out"
    if _provider_error_code(exc) in {
        "connection_timeout",
        "provider_timeout",
        "response_timeout",
    }:
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


@contextmanager
def _health_probe_request(
    *,
    task: ModelTaskName,
    timeout_seconds: float,
) -> Iterator[ModelRequest]:
    if _required_capability_for_task(task) != "vision_json":
        yield ModelRequest(
            task=task,
            prompt='请只返回 {"ok": true} 这个 JSON 对象，用于健康检查。',
            input_text="health check",
            timeout_seconds=timeout_seconds,
        )
        return

    with tempfile.NamedTemporaryFile(suffix=".png") as probe_image:
        probe_image.write(_TINY_PNG_BYTES)
        probe_image.flush()
        yield ModelRequest(
            task=task,
            prompt='请只返回 {"ok": true} 这个 JSON 对象，用于图片输入能力健康检查。',
            input_text="vision health check",
            image_path=Path(probe_image.name),
            image_media_type="image/png",
            timeout_seconds=timeout_seconds,
        )


def _required_capability_for_task(task: str) -> str:
    return TASK_CAPABILITY_REQUIREMENTS.get(task, "text_json")


def _read_capability_profile(raw: str) -> dict[str, dict[str, Any]]:
    source = _loads_dict(raw)
    profile: dict[str, dict[str, Any]] = {}
    for capability in MODEL_CAPABILITY_LABELS:
        payload = source.get(capability)
        if not isinstance(payload, dict):
            continue
        profile[capability] = {
            "status": _capability_status(payload.get("status")),
            "last_task": payload.get("last_task") or payload.get("lastTask"),
            "duration_ms": payload.get("duration_ms") or payload.get("durationMs"),
            "error_summary": payload.get("error_summary") or payload.get("errorSummary"),
            "error_code": payload.get("error_code") or payload.get("errorCode"),
            "checked_at": payload.get("checked_at") or payload.get("checkedAt"),
        }
    return profile


def _capability_profile_with_result(
    raw: str,
    *,
    task: str,
    status: str,
    duration_ms: int,
    error_summary: str | None,
    checked_at: datetime,
    error_code: str | None = None,
) -> str:
    capability = _required_capability_for_task(task)
    profile = _read_capability_profile(raw)
    previous = profile.get(capability, {})
    next_status = str(previous.get("status") or "unknown")
    if status == "ok":
        next_status = "ok"
    elif error_code in CAPABILITY_FAILURE_ERROR_CODES:
        next_status = "failed"
    elif status in {"failed", "timed_out"}:
        next_status = "unknown"
    elif next_status not in {"ok", "failed", "unknown"}:
        next_status = "unknown"
    profile[capability] = {
        "status": next_status,
        "last_task": task,
        "duration_ms": max(0, int(duration_ms)),
        "error_summary": _bounded(error_summary or "", 300) or None,
        "error_code": error_code,
        "checked_at": checked_at.isoformat(),
    }
    return json.dumps(profile, ensure_ascii=False)


def _capability_reads(raw: str) -> list[ApiCredentialCapabilityRead]:
    profile = _read_capability_profile(raw)
    return [
        ApiCredentialCapabilityRead(
            capability=capability,
            label=label,
            status=_capability_status(payload.get("status")),
            last_task=(
                str(payload["last_task"])
                if payload.get("last_task") is not None
                else None
            ),
            duration_ms=_optional_int(payload.get("duration_ms")),
            error_summary=(
                str(payload["error_summary"])
                if payload.get("error_summary") is not None
                else None
            ),
            checked_at=_parse_datetime(payload.get("checked_at")),
        )
        for capability, label in MODEL_CAPABILITY_LABELS.items()
        for payload in [profile.get(capability, {"status": "unknown"})]
    ]


def _credential_can_auto_run_task(
    credential: ModelApiCredential,
    task: str,
) -> bool:
    capability = _required_capability_for_task(task)
    capability_status = _read_capability_profile(
        credential.capability_profile_json
    ).get(capability, {}).get("status", "unknown")
    if capability_status == "failed":
        return False
    if capability == "vision_json":
        return capability_status == "ok"
    return True


def _capability_status(value: object) -> CapabilityStatus:
    raw_status = str(value or "unknown")
    if raw_status in {"ok", "failed", "unknown"}:
        return cast(CapabilityStatus, raw_status)
    return "unknown"


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _temperature_probe_candidates(
    current_temperature: float,
    requested_temperatures: list[float] | None,
) -> list[float]:
    raw_candidates = [
        current_temperature,
        *(requested_temperatures or DEFAULT_TEMPERATURE_PROBE_CANDIDATES),
    ]
    candidates: list[float] = []
    seen = set()
    for raw in raw_candidates:
        temperature = float(raw)
        if temperature < 0 or temperature > 2:
            raise AppError("invalid_temperature", "输出稳定度必须在 0 到 2 之间")
        key = round(temperature, 3)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(temperature)
    return candidates


def _temperature_probe_settings(
    current_temperature: float,
    requested_temperatures: list[float] | None,
    *,
    temperature_enabled: bool,
) -> list[tuple[float | None, bool]]:
    if not temperature_enabled:
        return [(None, False)]
    numeric = _temperature_probe_candidates(current_temperature, requested_temperatures)
    settings: list[tuple[float | None, bool]] = [
        (temperature, True)
        for temperature in numeric[: TEMPERATURE_PROBE_MAX_CANDIDATES - 1]
    ]
    settings.append((None, False))
    return settings


def _task_timeout(request: ModelRequest, slot: ModelRoutingSlot | None) -> float:
    if slot:
        return max(0.5, slot.timeout_seconds)
    if request.timeout_seconds is not None:
        return max(0.5, request.timeout_seconds)
    return 20.0


def _recommended_api_call_timeout_seconds(duration_ms: int) -> float:
    measured_seconds = max(0, duration_ms) / 1000
    recommended = math.ceil(measured_seconds * 2 + 10)
    return min(
        MAX_API_CALL_TIMEOUT_SECONDS,
        max(MIN_API_CALL_TIMEOUT_SECONDS, float(recommended)),
    )


def _scheduler_max_parallel(slot: ModelRoutingSlot | None) -> int:
    if slot is None:
        return 1
    return min(max(1, int(slot.max_parallel or 1)), 4)


def _scheduler_hedging_delay_seconds(slot: ModelRoutingSlot | None) -> float:
    if slot is None or slot.max_parallel <= 1:
        return 0.0
    return max(0.0, (slot.hedging_delay_ms or 0) / 1000)


def _scheduled_attempt_timeout_seconds(
    credential: ModelApiCredential,
    *,
    task: str,
    remaining_seconds: float,
    remaining_candidate_count: int,
) -> float:
    credential_limit = max(
        0.5,
        credential.timeout_seconds,
        TASK_MIN_ATTEMPT_TIMEOUT_SECONDS.get(task, 0.0),
    )
    if remaining_candidate_count <= 0:
        return max(0.5, min(credential_limit, remaining_seconds))

    relay_reserve = min(
        max(0.0, remaining_seconds - 0.5),
        remaining_candidate_count * MIN_FALLBACK_RELAY_SECONDS,
    )
    protected_budget = max(0.5, remaining_seconds - relay_reserve)
    latency_hint = (
        (max(0, credential.last_latency_ms) / 1000) * 2 + 8
        if credential.last_latency_ms is not None
        else credential_limit
    )
    desired = max(MIN_SCHEDULER_ATTEMPT_SECONDS, latency_hint)
    return max(
        0.5,
        min(
            credential_limit,
            remaining_seconds,
            max(protected_budget, MIN_SCHEDULER_ATTEMPT_SECONDS),
            desired,
        ),
    )


def _cancel_active_attempts(cancellations: Iterable[CancellationSignal]) -> None:
    for cancellation in tuple(cancellations):
        cancellation.cancel()


def _scheduler_budget_timeout_attempts(
    request: ModelRequest,
    active_attempts: Iterable[_RunningScheduledAttempt],
) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for running in active_attempts:
        attempts.extend(
            _scheduled_attempts(
                (),
                credential=running.credential,
                fallback_index=running.fallback_index,
                status="timed_out",
                duration_ms=_elapsed_ms(running.started_at),
                task=request.task,
                error="任务预算已用尽，本机已停止等待该候选 API",
                error_code="scheduler_budget_exhausted",
            )
        )
    return attempts


def _capacity_status(
    *,
    status: str,
    last_status: str | None,
    current_concurrency: int,
    max_concurrency: int,
    failure_rate: float,
) -> str:
    if status == "disabled" or last_status in {"failed", "timed_out"}:
        return "degraded"
    if current_concurrency >= max(1, max_concurrency):
        return "saturated"
    if current_concurrency > 0:
        return "busy"
    if failure_rate >= 0.5:
        return "degraded"
    return "idle"


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


def _build_provider_groups(
    credentials: list[ModelApiCredential],
    traces: list[ModelCallTrace],
) -> list[ApiProviderGroupRead]:
    credentials_by_group: dict[str, list[ModelApiCredential]] = {}
    for credential in credentials:
        credentials_by_group.setdefault(
            _provider_host_label(credential.base_url),
            [],
        ).append(credential)

    trace_totals: dict[str, int] = {}
    trace_failures: dict[str, int] = {}
    trace_timeouts: dict[str, int] = {}
    credential_groups = {
        credential.id: _provider_host_label(credential.base_url)
        for credential in credentials
    }
    for trace in traces:
        if not trace.credential_id:
            continue
        group = credential_groups.get(trace.credential_id)
        if not group:
            continue
        trace_totals[group] = trace_totals.get(group, 0) + 1
        if trace.status in {"failed", "timed_out"}:
            trace_failures[group] = trace_failures.get(group, 0) + 1
        if trace.status == "timed_out":
            trace_timeouts[group] = trace_timeouts.get(group, 0) + 1

    runtime = _CAPACITY_TRACKER.snapshot([credential.id for credential in credentials])
    provider_groups: list[ApiProviderGroupRead] = []
    for group, group_credentials in credentials_by_group.items():
        recent_call_count = trace_totals.get(group, 0)
        recent_failure_count = trace_failures.get(group, 0)
        recent_timeout_count = trace_timeouts.get(group, 0)
        recent_failure_rate = (
            recent_failure_count / recent_call_count if recent_call_count else 0.0
        )
        recent_timeout_rate = (
            recent_timeout_count / recent_call_count if recent_call_count else 0.0
        )
        status: Literal["ok", "watch", "degraded"] = "ok"
        recommendation: str | None = None
        if recent_call_count >= 3 and (
            recent_failure_rate >= 0.8
            or (recent_timeout_count >= 3 and recent_timeout_rate >= 0.6)
        ):
            status = "degraded"
            recommendation = "该中转站最近异常集中，可一键停用该站全部 API 后切换其他站。"
        elif recent_call_count >= 3 and (
            recent_failure_rate >= 0.4 or recent_timeout_count >= 2
        ):
            status = "watch"
            recommendation = "该中转站最近有波动，建议继续观察或手动停用异常 Key。"

        provider_groups.append(
            ApiProviderGroupRead(
                provider_group=group,
                credential_count=len(group_credentials),
                active_credential_count=sum(
                    1 for credential in group_credentials if credential.status == "active"
                ),
                auto_assign_credential_count=sum(
                    1
                    for credential in group_credentials
                    if credential.status == "active" and credential.auto_assign_enabled
                ),
                current_concurrency=sum(
                    int(runtime.get(credential.id, {}).get("in_flight", 0))
                    for credential in group_credentials
                ),
                recent_call_count=recent_call_count,
                recent_failure_rate=round(recent_failure_rate, 4),
                recent_timeout_count=recent_timeout_count,
                status=status,
                recommendation=recommendation,
            )
        )

    status_rank = {"degraded": 0, "watch": 1, "ok": 2}
    return sorted(
        provider_groups,
        key=lambda item: (
            status_rank[item.status],
            -item.recent_failure_rate,
            -item.recent_timeout_count,
            -item.credential_count,
            item.provider_group,
        ),
    )


def _credential_audit_snapshot(credential: ModelApiCredential) -> dict[str, Any]:
    return {
        "label": credential.label,
        "providerType": credential.provider_type,
        "providerGroup": _provider_host_label(credential.base_url),
        "baseUrl": credential.base_url,
        "modelName": credential.model_name,
        "status": credential.status,
        "autoAssignEnabled": credential.auto_assign_enabled,
        "priority": credential.priority,
        "timeoutSeconds": credential.timeout_seconds,
        "temperature": credential.temperature,
        "temperatureEnabled": credential.temperature_enabled,
        "maxConcurrency": normalize_max_concurrency(credential.max_concurrency),
    }


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
    del credential
    return "search_system_routing"


def _representative_task_for_scope(
    task_scope: list[ModelTaskName] | list[str],
) -> ModelTaskName:
    for task in task_scope:
        if task in TASK_LAYER_LABELS:
            return cast(ModelTaskName, task)
    return "search_system_routing"


def _group_health_probe_targets_by_provider(
    targets: list[_HealthProbeTarget],
) -> list[list[_HealthProbeTarget]]:
    groups: dict[str, list[_HealthProbeTarget]] = {}
    for target in targets:
        groups.setdefault(target.provider_group, []).append(target)
    return list(groups.values())


def _scheduled_attempts(
    provider_attempts: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    credential: ModelApiCredential,
    fallback_index: int,
    status: str,
    duration_ms: int,
    task: str,
    error: str = "",
    error_code: str | None = None,
) -> list[dict[str, Any]]:
    raw_attempts = provider_attempts or [
        {
            "provider": _provider_host_label(credential.base_url),
            "model": credential.model_name,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
            "error_code": error_code,
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
                "error_code": error_code
                or attempt.get("error_code")
                or attempt.get("errorCode"),
            }
        )
    return attempts


def _error_attempts(exc: Exception) -> tuple[dict[str, Any], ...]:
    attempts = getattr(exc, "attempts", ())
    if not isinstance(attempts, (list, tuple)):
        return ()
    return tuple(item for item in attempts if isinstance(item, dict))


def _health_check_attempts(
    provider_attempts: tuple[dict[str, Any], ...],
    *,
    credential: ModelApiCredential,
    task: str,
    status: str,
    duration_ms: int,
    error: str,
    layer_name: str = "健康检查",
    error_code: str | None = None,
) -> list[dict[str, Any]]:
    raw_attempts = provider_attempts
    if not raw_attempts:
        raw_attempts = [
            {
                "provider": _provider_host_label(credential.base_url),
                "model": credential.model_name,
                "duration_ms": duration_ms,
                "error_code": error_code,
            }
        ]
    return [
        {
            **attempt,
            "task": task,
            "layer": layer_name,
            "credential_id": credential.id,
            "credential_label": credential.label,
            "status": status,
            "duration_ms": int(attempt.get("duration_ms") or duration_ms),
            "error": error or str(attempt.get("error") or ""),
            "error_code": error_code
            or attempt.get("error_code")
            or attempt.get("errorCode"),
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
    error_code: str | None = None,
) -> dict[str, Any]:
    return {
        "task": request.task,
        "layer": TASK_LAYER_LABELS.get(request.task, "模型调用"),
        "provider": "api_center_scheduler",
        "model": "未分配",
        "status": status,
        "duration_ms": max(0, duration_ms),
        "error": error,
        "error_code": error_code,
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
