from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from app.ai.contracts import CancellationSignal
from app.services.search_models import (
    SearchBranchDiagnostic,
    SearchBranchResult,
)

T = TypeVar("T")


def _call_with_signal(
    call: Callable[..., T],
    signal: CancellationSignal,
) -> T:
    """Support legacy no-argument branches during the cancellation rollout."""

    try:
        parameters = inspect.signature(call).parameters.values()
    except (TypeError, ValueError):
        return call(signal)

    accepts_positional_signal = any(
        parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
        for parameter in parameters
    )
    if accepts_positional_signal:
        return call(signal)
    return call()


class SearchBranchRunner:
    async def run_thread(
        self,
        source: str,
        call: Callable[..., T],
        *,
        timeout_seconds: float,
        retry_attempts: int = 0,
        retry_backoff_seconds: float = 0.0,
    ) -> SearchBranchResult[T]:
        started = time.monotonic()
        deadline = started + max(0.001, timeout_seconds)
        cancellation = CancellationSignal()
        last_error: Exception | None = None
        for attempt in range(max(0, retry_attempts) + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return self._timed_out(source, started)
            try:
                value = await asyncio.wait_for(
                    asyncio.to_thread(_call_with_signal, call, cancellation),
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
