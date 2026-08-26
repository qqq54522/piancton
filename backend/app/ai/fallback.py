from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from app.ai.contracts import (
    ModelCallResult,
    ModelProviderCancelled,
    ModelProviderError,
    ModelProviderValidationError,
    ModelRequest,
)

logger = logging.getLogger(__name__)


class FallbackModelProvider:
    """Tries a chain of OpenAI-compatible providers in order; first success wins."""

    name = "fallback_chain"

    def __init__(self, providers: list) -> None:
        self.providers = [p for p in providers if p.configured]

    @property
    def configured(self) -> bool:
        return bool(self.providers)

    @property
    def attempt_count(self) -> int:
        return max(1, len(self.providers))

    def generate_json(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[dict[str, Any]]:
        last_error: Exception | None = None
        attempts: list[dict[str, Any]] = []
        for i, provider in enumerate(self.providers):
            _raise_if_cancelled(request, attempts)
            started = time.monotonic()
            try:
                call = provider.generate_json(request)
                provider_attempts = _provider_attempts(
                    provider,
                    raw_attempts=call.attempts,
                    fallback_index=i,
                    started=started,
                    status="ok",
                )
                attempts.extend(provider_attempts)
                if i > 0:
                    logger.info(
                        "fallback provider #%d (%s) succeeded after earlier failures: %s",
                        i,
                        provider.model_name,
                        _format_attempts(attempts),
                    )
                return ModelCallResult(call.value, tuple(attempts))
            except (ModelProviderError, Exception) as exc:
                provider_attempts = _provider_attempts(
                    provider,
                    raw_attempts=_error_attempts(exc),
                    fallback_index=i,
                    started=started,
                    status="failed",
                    error=exc,
                )
                attempts.extend(provider_attempts)
                logger.warning(
                    "provider #%d (%s) failed: %s — trying next; attempts=%s",
                    i,
                    provider.model_name,
                    exc,
                    _format_attempts(attempts),
                )
                last_error = exc
                if isinstance(exc, ModelProviderCancelled) or (
                    request.cancellation is not None
                    and request.cancellation.cancelled
                ):
                    raise
        raise ModelProviderError(
            f"all {len(self.providers)} providers failed: {_format_attempts(attempts)}",
            attempts=tuple(attempts),
        ) from last_error

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], Any],
    ) -> ModelCallResult[Any]:
        last_error: Exception | None = None
        attempts: list[dict[str, Any]] = []
        for i, provider in enumerate(self.providers):
            _raise_if_cancelled(request, attempts)
            started = time.monotonic()
            call: ModelCallResult[dict[str, Any]] | None = None
            try:
                provider_call = provider.generate_json(request)
                call = provider_call
                try:
                    validated = validator(provider_call.value)
                except Exception as exc:
                    raise ModelProviderValidationError(
                        "模型返回内容未通过项目校验",
                        attempts=provider_call.attempts,
                        cause=exc,
                    ) from exc
                provider_attempts = _provider_attempts(
                    provider,
                    raw_attempts=provider_call.attempts,
                    fallback_index=i,
                    started=started,
                    status="ok",
                )
                attempts.extend(provider_attempts)
                if i > 0:
                    logger.info(
                        "fallback provider #%d (%s) produced a valid response after "
                        "earlier failures: %s",
                        i,
                        provider.model_name,
                        _format_attempts(attempts),
                    )
                return ModelCallResult(validated, tuple(attempts))
            except Exception as exc:
                provider_attempts = _provider_attempts(
                    provider,
                    raw_attempts=(
                        call.attempts
                        if call is not None
                        else _error_attempts(exc)
                    ),
                    fallback_index=i,
                    started=started,
                    status="failed",
                    error=exc,
                    override_status=True,
                )
                attempts.extend(provider_attempts)
                logger.warning(
                    "provider #%d (%s) failed validation or generation: %s — "
                    "trying next; attempts=%s",
                    i,
                    provider.model_name,
                    exc,
                    _format_attempts(attempts),
                )
                last_error = exc
                if isinstance(exc, ModelProviderCancelled) or (
                    request.cancellation is not None
                    and request.cancellation.cancelled
                ):
                    raise
        raise ModelProviderError(
            f"all {len(self.providers)} providers failed: {_format_attempts(attempts)}",
            attempts=tuple(attempts),
        ) from last_error


def _provider_attempts(
    provider,
    *,
    raw_attempts: tuple[dict[str, Any], ...],
    fallback_index: int,
    started: float,
    status: str,
    error: Exception | None = None,
    override_status: bool = False,
) -> list[dict[str, Any]]:
    attempts = raw_attempts
    if isinstance(attempts, (list, tuple)) and attempts:
        return [
            {
                **attempt,
                "fallback_index": fallback_index,
                **(
                    {"status": status, "error": _safe_error(error)}
                    if override_status
                    else {}
                ),
            }
            for attempt in attempts
            if isinstance(attempt, dict)
        ]
    return [
        {
            "fallback_index": fallback_index,
            "provider": getattr(provider, "provider_label", "unknown"),
            "model": getattr(provider, "model_name", "unknown"),
            "status": status,
            "duration_ms": _elapsed_ms(started),
            "error": _safe_error(error) if error else "",
        }
    ]


def _error_attempts(exc: Exception) -> tuple[dict[str, Any], ...]:
    attempts = getattr(exc, "attempts", ())
    if not isinstance(attempts, tuple):
        return ()
    return tuple(item for item in attempts if isinstance(item, dict))


def _format_attempts(attempts: list[dict[str, Any]]) -> str:
    parts = []
    for attempt in attempts:
        provider = str(attempt.get("provider") or "unknown")
        model = str(attempt.get("model") or "unknown")
        status = str(attempt.get("status") or "unknown")
        duration = int(attempt.get("duration_ms") or 0)
        error = str(attempt.get("error") or "").strip()
        suffix = f", {error}" if error else ""
        parts.append(f"{provider}/{model} {status} {duration}ms{suffix}")
    return " | ".join(parts)


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _safe_error(exc: Exception | None) -> str:
    if exc is None:
        return ""
    message = str(exc).strip() or exc.__class__.__name__
    return message[:120]


def _raise_if_cancelled(
    request: ModelRequest,
    attempts: list[dict[str, Any]],
) -> None:
    if request.cancellation is not None and request.cancellation.cancelled:
        raise ModelProviderCancelled(
            "模型调用已取消",
            attempts=tuple(attempts),
        )
