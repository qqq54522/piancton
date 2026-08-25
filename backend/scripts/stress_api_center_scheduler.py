from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any, cast

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ai.contracts import ModelProviderNotConfigured, ModelRequest, ModelTask
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.db.session import SessionLocal
from app.models.api_provider import ModelApiCredential, ModelApiHealthCheck
from app.services.api_center_service import ApiCenterService


@dataclass(frozen=True)
class CredentialSnapshot:
    id: str
    label: str
    base_url: str
    model_name: str
    api_key_secret: str
    timeout_seconds: float
    temperature: float


@dataclass(frozen=True)
class ProbeAttempt:
    credential_id: str
    credential_label: str
    level: int
    status: str
    duration_ms: int
    error: str = ""


@dataclass(frozen=True)
class ScheduledAttempt:
    status: str
    duration_ms: int
    credential_id: str | None
    credential_label: str
    error: str = ""


class _UnconfiguredProvider:
    name = "unconfigured"
    last_attempts: list[dict[str, Any]] = []

    @property
    def configured(self) -> bool:
        return False

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        del request
        raise ModelProviderNotConfigured("stress test does not use fallback provider")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe API Center credential capacity and scheduler concurrency."
    )
    parser.add_argument("--task", default="search_system_routing")
    parser.add_argument("--max-level", type=int, default=2)
    parser.add_argument("--requests", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--no-update", action="store_true")
    args = parser.parse_args()

    task = _model_task(args.task)
    credentials = _load_credentials(task)
    if not credentials:
        raise SystemExit(f"没有可用于 {task} 的 active API")

    probe_results: dict[str, dict[str, Any]] = {}
    for credential in credentials:
        safe_level, attempts = _probe_credential_capacity(
            credential,
            task=task,
            max_level=max(1, args.max_level),
            timeout_seconds=args.timeout,
        )
        probe_results[credential.id] = {
            "label": credential.label,
            "safeConcurrency": safe_level,
            "attempts": [_attempt_dict(item) for item in attempts],
        }
        if not args.no_update:
            _persist_capacity_probe(
                credential.id,
                task=task,
                safe_level=safe_level,
                attempts=attempts,
            )

    scheduled_attempts = _run_scheduler_stress(
        task=task,
        request_count=max(1, args.requests),
        concurrency=max(1, args.concurrency),
        timeout_seconds=args.timeout,
    )

    print(
        json.dumps(
            {
                "task": task,
                "credentialCount": len(credentials),
                "capacityProbe": probe_results,
                "schedulerStress": _scheduled_summary(scheduled_attempts),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _model_task(task: str) -> ModelTask:
    valid_tasks = {
        "image_content_analysis",
        "asset_search_phrase_generation",
        "search_system_routing",
        "search_intent_understanding",
        "search_proof_point_understanding",
        "search_candidate_review",
        "search_result_recommendation_reason",
        "copy_selling_point_matching",
        "asset_agent_chat",
    }
    if task not in valid_tasks:
        raise SystemExit(f"未知任务：{task}")
    return cast(ModelTask, task)


def _load_credentials(task: ModelTask) -> list[CredentialSnapshot]:
    with SessionLocal() as db:
        service = ApiCenterService(db)
        service.ensure_default_slots()
        service.sync_environment_credentials()
        credentials = [
            item
            for item in service.repo.list_credentials()
            if item.status == "active"
            and item.auto_assign_enabled
            and _credential_can_run_task(item, task)
        ]
        return [
            CredentialSnapshot(
                id=item.id,
                label=item.label,
                base_url=item.base_url,
                model_name=item.model_name,
                api_key_secret=item.api_key_secret,
                timeout_seconds=item.timeout_seconds,
                temperature=item.temperature,
            )
            for item in credentials
        ]


def _credential_can_run_task(credential: ModelApiCredential, task: ModelTask) -> bool:
    try:
        scopes = json.loads(credential.task_scope_json or "[]")
    except json.JSONDecodeError:
        scopes = []
    if not isinstance(scopes, list):
        return False
    return not scopes or task in {str(item) for item in scopes}


def _probe_credential_capacity(
    credential: CredentialSnapshot,
    *,
    task: ModelTask,
    max_level: int,
    timeout_seconds: float,
) -> tuple[int, list[ProbeAttempt]]:
    safe_level = 1
    attempts: list[ProbeAttempt] = []
    for level in range(1, max_level + 1):
        level_attempts = _run_credential_level(
            credential,
            task=task,
            level=level,
            timeout_seconds=timeout_seconds,
        )
        attempts.extend(level_attempts)
        level_ok = all(item.status == "ok" for item in level_attempts)
        p95 = _p95([item.duration_ms for item in level_attempts])
        if level_ok and p95 <= timeout_seconds * 1000:
            safe_level = level
            continue
        break
    return safe_level, attempts


def _run_credential_level(
    credential: CredentialSnapshot,
    *,
    task: ModelTask,
    level: int,
    timeout_seconds: float,
) -> list[ProbeAttempt]:
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [
            pool.submit(
                _call_single_credential,
                credential,
                task,
                level,
                timeout_seconds,
            )
            for _ in range(level)
        ]
        return [future.result() for future in as_completed(futures)]


def _call_single_credential(
    credential: CredentialSnapshot,
    task: ModelTask,
    level: int,
    timeout_seconds: float,
) -> ProbeAttempt:
    started = time.monotonic()
    status = "failed"
    error = ""
    try:
        provider = OpenAICompatibleModelProvider(
            base_url=credential.base_url,
            api_key=credential.api_key_secret,
            model_name=credential.model_name,
            timeout_seconds=int(max(1, timeout_seconds)),
            temperature=credential.temperature,
        )
        payload = provider.generate_json(
            ModelRequest(
                task=task,
                prompt='请只返回 {"ok": true} 这个 JSON 对象，用于 API 容量压测。',
                input_text=f"api-center-capacity-probe-level-{level}",
                timeout_seconds=timeout_seconds,
            )
        )
        if not isinstance(payload, dict):
            raise RuntimeError("模型没有返回 JSON 对象")
        status = "ok"
    except Exception as exc:
        error = _safe_error(exc)
    return ProbeAttempt(
        credential_id=credential.id,
        credential_label=credential.label,
        level=level,
        status=status,
        duration_ms=_elapsed_ms(started),
        error=error,
    )


def _persist_capacity_probe(
    credential_id: str,
    *,
    task: ModelTask,
    safe_level: int,
    attempts: list[ProbeAttempt],
) -> None:
    with SessionLocal() as db:
        service = ApiCenterService(db)
        credential = service.repo.get_credential(credential_id)
        if not credential:
            return
        credential.max_concurrency = safe_level
        last_attempt = attempts[-1] if attempts else None
        if last_attempt:
            credential.last_status = last_attempt.status
            credential.last_latency_ms = last_attempt.duration_ms
            credential.last_error = last_attempt.error or None
            for attempt in attempts:
                service.repo.add_health_check(
                    ModelApiHealthCheck(
                        credential_id=credential.id,
                        task=task,
                        status=attempt.status,
                        duration_ms=attempt.duration_ms,
                        error_summary=attempt.error or None,
                    )
                )
        service.uow.commit()


def _run_scheduler_stress(
    *,
    task: ModelTask,
    request_count: int,
    concurrency: int,
    timeout_seconds: float,
) -> list[ScheduledAttempt]:
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [
            pool.submit(_call_scheduler_once, task, timeout_seconds, index)
            for index in range(request_count)
        ]
        return [future.result() for future in as_completed(futures)]


def _call_scheduler_once(task: ModelTask, timeout_seconds: float, index: int) -> ScheduledAttempt:
    started = time.monotonic()
    with SessionLocal() as db:
        service = ApiCenterService(db)
        provider = service.build_scheduled_provider(fallback_provider=_UnconfiguredProvider())
        status = "failed"
        error = ""
        try:
            payload = provider.generate_json(
                ModelRequest(
                    task=task,
                    prompt='请只返回 {"ok": true} 这个 JSON 对象，用于 API 调度压测。',
                    input_text=f"api-center-scheduler-stress-{index}",
                    timeout_seconds=timeout_seconds,
                )
            )
            if not isinstance(payload, dict):
                raise RuntimeError("模型没有返回 JSON 对象")
            status = "ok"
        except Exception as exc:
            error = _safe_error(exc)
        finally:
            service.uow.commit()
        provider_attempts = getattr(provider, "last_attempts", [])
        attempt = provider_attempts[-1] if provider_attempts else {}
        return ScheduledAttempt(
            status=status,
            duration_ms=_elapsed_ms(started),
            credential_id=(
                str(attempt.get("credential_id"))
                if attempt.get("credential_id")
                else None
            ),
            credential_label=str(attempt.get("credential_label") or "未分配"),
            error=error or str(attempt.get("error") or ""),
        )


def _scheduled_summary(attempts: list[ScheduledAttempt]) -> dict[str, Any]:
    durations = [item.duration_ms for item in attempts]
    by_credential = Counter(item.credential_label for item in attempts)
    failures_by_credential: dict[str, int] = defaultdict(int)
    for item in attempts:
        if item.status != "ok":
            failures_by_credential[item.credential_label] += 1
    return {
        "requestCount": len(attempts),
        "okCount": sum(1 for item in attempts if item.status == "ok"),
        "failedCount": sum(1 for item in attempts if item.status != "ok"),
        "p50Ms": int(median(durations)) if durations else 0,
        "p95Ms": _p95(durations),
        "byCredential": dict(by_credential),
        "failuresByCredential": dict(failures_by_credential),
        "errors": [
            {
                "credential": item.credential_label,
                "error": item.error,
            }
            for item in attempts
            if item.status != "ok"
        ][:10],
    }


def _attempt_dict(item: ProbeAttempt) -> dict[str, Any]:
    return {
        "level": item.level,
        "status": item.status,
        "durationMs": item.duration_ms,
        "error": item.error,
    }


def _p95(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * 0.95))
    return int(ordered[index])


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:300]


if __name__ == "__main__":
    main()
