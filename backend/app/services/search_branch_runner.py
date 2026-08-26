from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from app.ai.contracts import CancellationSignal
from app.services.search_models import (
    ModelAttemptDiagnostic,
    SearchBranchDiagnostic,
    SearchBranchResult,
)

T = TypeVar("T")


class SearchBranchRunner:
    async def run_thread(
        self,
        source: str,
        call: Callable[..., T],
        *,
        timeout_seconds: float,
        retry_attempts: int = 0,
        retry_backoff_seconds: float = 0.0,
        attempt_task: str | None = None,
        attempt_layer: str | None = None,
    ) -> SearchBranchResult[T]:
        started = time.monotonic()
        deadline = started + max(0.001, timeout_seconds)
        cancellation = CancellationSignal()
        last_error: Exception | None = None
        failed_attempts: list[ModelAttemptDiagnostic] = []
        for attempt in range(max(0, retry_attempts) + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return self._timed_out(source, started)
            try:
                value = await asyncio.wait_for(
                    asyncio.to_thread(call, cancellation),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                cancellation.cancel()
                return self._timed_out(source, started)
            except asyncio.CancelledError:
                cancellation.cancel()
                raise
            except Exception as exc:
                last_error = exc
                failed_attempts.extend(
                    _attempt_diagnostics(
                        exc,
                        task=attempt_task,
                        layer=attempt_layer,
                    )
                )
                if attempt >= max(0, retry_attempts):
                    break
                backoff = min(
                    max(0.0, retry_backoff_seconds),
                    max(0.0, deadline - time.monotonic()),
                )
                if backoff:
                    await asyncio.sleep(backoff)
                continue
            return SearchBranchResult(
                value=value,
                diagnostic=SearchBranchDiagnostic(
                    source=source,
                    status="ok",
                    duration_ms=_elapsed_ms(started),
                    result_count=_result_count(value),
                ),
            )
        return SearchBranchResult(
            value=None,
            diagnostic=SearchBranchDiagnostic(
                source=source,
                status="failed",
                duration_ms=_elapsed_ms(started),
                detail=_safe_error(last_error or RuntimeError("分支调用失败")),
                attempts=tuple(failed_attempts),
            ),
        )

    def _timed_out(self, source: str, started: float) -> SearchBranchResult[T]:
        return SearchBranchResult(
            value=None,
            diagnostic=SearchBranchDiagnostic(
                source=source,
                status="timed_out",
                duration_ms=_elapsed_ms(started),
                detail="超过分支时间预算",
            ),
        )

    def skipped(self, source: str, detail: str) -> SearchBranchResult[object]:
        return SearchBranchResult(
            value=None,
            diagnostic=SearchBranchDiagnostic(
                source=source,
                status="skipped",
                duration_ms=0,
                detail=detail,
            ),
        )

    def cached(self, source: str, value: T) -> SearchBranchResult[T]:
        return SearchBranchResult(
            value=value,
            diagnostic=SearchBranchDiagnostic(
                source=source,
                status="ok",
                duration_ms=0,
                result_count=_result_count(value),
                cache_hit=True,
            ),
        )

    def with_result_count(
        self,
        result: SearchBranchResult[T],
        count: int,
    ) -> SearchBranchResult[T]:
        return replace(
            result,
            diagnostic=replace(result.diagnostic, result_count=max(0, count)),
        )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _result_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value)
    return 1


def _safe_error(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message[:160]


def _attempt_diagnostics(
    exc: Exception,
    *,
    task: str | None,
    layer: str | None,
) -> tuple[ModelAttemptDiagnostic, ...]:
    if not task or not layer:
        return ()
    attempts = getattr(exc, "attempts", ())
    if not isinstance(attempts, (list, tuple)):
        return ()
    return tuple(
        ModelAttemptDiagnostic(
            task=task,
            layer=layer,
            provider=str(item.get("provider") or "unknown")[:120],
            model=str(item.get("model") or "unknown")[:120],
            status=str(item.get("status") or "failed")[:24],
            duration_ms=int(item.get("duration_ms") or 0),
            fallback_index=(
                int(item["fallback_index"])
                if item.get("fallback_index") is not None
                else None
            ),
            error=str(item.get("error") or "")[:300],
        )
        for item in attempts
        if isinstance(item, dict)
    )
