from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Optional,
    Protocol,
    TypeVar,
)


class CancellationSignal:
    """Request-scoped signal used to close an in-flight provider transport."""

    def __init__(self) -> None:
        self._event = Event()
        self._lock = Lock()
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._next_callback_id = 0

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def cancel(self) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self._event.set()
            callbacks = tuple(self._callbacks.values())
            self._callbacks.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception:
                # Transport cleanup must not block the cancellation path.
                continue

    def add_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        with self._lock:
            if self._event.is_set():
                callback_id = None
            else:
                callback_id = self._next_callback_id
                self._next_callback_id += 1
                self._callbacks[callback_id] = callback

        if callback_id is None:
            try:
                callback()
            except Exception:
                pass
            return lambda: None

        def remove() -> None:
            with self._lock:
                self._callbacks.pop(callback_id, None)

        return remove


ModelTask = Literal[
    "image_content_analysis",
    "asset_search_phrase_generation",
    "search_system_routing",
    "search_intent_understanding",
    "search_proof_point_understanding",
    "search_candidate_review",
    "search_result_recommendation_reason",
    "copy_selling_point_matching",
    "asset_agent_chat",
]


@dataclass(frozen=True)
class ModelRequest:
    task: ModelTask
    prompt: str
    input_text: str = ""
    image_path: Optional[Path] = None
    image_media_type: Optional[str] = None
    timeout_seconds: Optional[float] = None
    cancellation: CancellationSignal | None = None


T = TypeVar("T")


@dataclass(frozen=True)
class ModelCallResult(Generic[T]):
    """A request-scoped result that keeps the provider attempts with the value."""

    value: T
    attempts: tuple[dict[str, Any], ...] = ()


class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(self, request: ModelRequest) -> dict[str, Any]: ...


class StagedSearchModelCapabilities(Protocol):
    def route_search_system(self, keyword: str) -> Any: ...

    def understand_selling_points_from_route(self, keyword: str, routing) -> Any: ...

    def understand_proof_points(self, keyword: str, selling_points) -> Any: ...


class RoutedSystemCodeCapabilities(Protocol):
    def routed_system_codes(self, routing) -> Any: ...


class CandidateReviewCapabilities(Protocol):
    def review_search_candidates(
        self,
        *,
        keyword: str,
        understanding,
        candidates,
    ) -> Any: ...


class ModelProviderNotConfigured(RuntimeError):
    """Raised until the user selects and configures a real model provider."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
    ) -> None:
        super().__init__(message)
        self.attempts = attempts


class ModelProviderError(RuntimeError):
    """Raised when a configured provider cannot produce a valid model response."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
    ) -> None:
        super().__init__(message)
        self.attempts = attempts


class ModelProviderCancelled(ModelProviderError):
    """Raised when a caller cancels an in-flight provider request."""


def call_with_optional_cancellation(
    method: Callable[..., T],
    *args: Any,
    cancellation: CancellationSignal | None = None,
    **kwargs: Any,
) -> T:
    """Call a capability while keeping older integrations source-compatible."""

    if cancellation is None:
        return method(*args, **kwargs)

    try:
        parameters = inspect.signature(method).parameters.values()
    except (TypeError, ValueError):
        # Most real callables expose a signature. For opaque callables, keep the
        # new contract available and let their own error surface normally.
        return method(*args, cancellation=cancellation, **kwargs)

    accepts_cancellation = any(
        parameter.name == "cancellation"
        or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )
    if accepts_cancellation:
        kwargs["cancellation"] = cancellation
    return method(*args, **kwargs)


def has_staged_search_capabilities(
    value: object,
) -> bool:
    return all(
        callable(getattr(value, name, None))
        for name in (
            "route_search_system",
            "understand_selling_points_from_route",
            "understand_proof_points",
        )
    )


def has_routed_system_code_capability(
    value: object,
) -> bool:
    return callable(getattr(value, "routed_system_codes", None))


def has_candidate_review_capability(
    value: object,
) -> bool:
    return callable(getattr(value, "review_search_candidates", None))


def generate_json_with_attempts(
    provider: ModelProvider,
    request: ModelRequest,
) -> ModelCallResult[dict[str, Any]]:
    """Call a provider while keeping legacy test doubles compatible."""

    runner = getattr(provider, "generate_json_with_attempts", None)
    if callable(runner):
        result = runner(request)
        if isinstance(result, ModelCallResult):
            return result
        if isinstance(result, dict):
            return ModelCallResult(result, _legacy_attempts(provider))
        raise TypeError("模型 Provider 返回了无效的请求结果")

    value = provider.generate_json(request)
    return ModelCallResult(value, _legacy_attempts(provider))


def generate_validated_json_with_attempts(
    provider: ModelProvider,
    request: ModelRequest,
    validator,
) -> ModelCallResult[Any]:
    """Validate a provider response without losing request-scoped telemetry."""

    runner = getattr(provider, "generate_validated_json_with_attempts", None)
    if callable(runner):
        result = runner(request, validator)
        if isinstance(result, ModelCallResult):
            return result
        return ModelCallResult(result, _legacy_attempts(provider))

    legacy_runner = getattr(provider, "generate_validated_json", None)
    if callable(legacy_runner):
        value = legacy_runner(request, validator)
        return ModelCallResult(value, _legacy_attempts(provider))

    raw = generate_json_with_attempts(provider, request)
    return ModelCallResult(validator(raw.value), raw.attempts)


def _legacy_attempts(provider: ModelProvider) -> tuple[dict[str, Any], ...]:
    attempts = getattr(provider, "last_attempts", ())
    if not isinstance(attempts, (list, tuple)):
        return ()
    return tuple(item.copy() for item in attempts if isinstance(item, dict))
