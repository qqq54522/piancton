from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import replace
from typing import TypeVar

from app.services.search_models import (
    SearchBranchDiagnostic,
    SearchBranchResult,
)

T = TypeVar("T")


class SearchBranchRunner:
    async def run_thread(
        self,
        source: str,
        call: Callable[[], T],
        *,
        timeout_seconds: float,
    ) -> SearchBranchResult[T]:
        started = time.monotonic()
        try:
            value = await asyncio.wait_for(
                asyncio.to_thread(call),
                timeout=max(0.001, timeout_seconds),
            )
        except asyncio.TimeoutError:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source=source,
                    status="timed_out",
                    duration_ms=_elapsed_ms(started),
                    detail="超过分支时间预算",
                ),
            )
        except Exception as exc:
            return SearchBranchResult(
                value=None,
                diagnostic=SearchBranchDiagnostic(
                    source=source,
                    status="failed",
                    duration_ms=_elapsed_ms(started),
                    detail=_safe_error(exc),
                ),
            )
        return SearchBranchResult(
            value=value,
            diagnostic=SearchBranchDiagnostic(
                source=source,
                status="ok",
                duration_ms=_elapsed_ms(started),
                result_count=_result_count(value),
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
