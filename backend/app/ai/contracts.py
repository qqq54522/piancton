from __future__ import annotations

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
    runtime_checkable,
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

    def wait(self, timeout: float | None = None) -> bool:
        """Wait until cancellation or timeout and return the signal state."""

        return self._event.wait(timeout)

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
    request_id: Optional[str] = None


T = TypeVar("T", covariant=True)


@dataclass(frozen=True)
class ModelCallResult(Generic[T]):
    """A request-scoped result that keeps the provider attempts with the value."""

    value: T
    attempts: tuple[dict[str, Any], ...] = ()


class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[dict[str, Any]]: ...

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], T],
    ) -> ModelCallResult[T]: ...


@runtime_checkable
class BasicSearchModelCapabilities(Protocol):
    @property
    def provider(self) -> ModelProvider: ...

    def understand_search(
        self,
        keyword: str,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...


@runtime_checkable
class StagedSearchModelCapabilities(Protocol):
    @property
    def provider(self) -> ModelProvider: ...

    def route_search_system(
        self,
        keyword: str,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...

    def understand_selling_points_from_route(
        self,
        keyword: str,
        routing: Any,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...

    def understand_proof_points(
        self,
        keyword: str,
        selling_points: Any,
        *,
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...

    def routed_system_codes(
        self,
        routing: Any,
    ) -> tuple[str, ...]: ...


@runtime_checkable
class CandidateReviewCapabilities(Protocol):
    @property
    def provider(self) -> ModelProvider: ...

    def review_search_candidates(
        self,
        *,
        keyword: str,
        understanding: Any,
        candidates: list[dict[str, Any]],
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...


@runtime_checkable
class ResultRecommendationCapabilities(Protocol):
    @property
    def provider(self) -> ModelProvider: ...

    def recommend_search_result_reasons(
        self,
        *,
        keyword: str,
        understanding: Any,
        candidates: list[dict[str, Any]],
        cancellation: CancellationSignal | None = None,
    ) -> ModelCallResult[Any]: ...


class ModelProviderNotConfigured(RuntimeError):
    """Raised until the user selects and configures a real model provider."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
        code: str = "provider_not_configured",
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.code = code


class ModelProviderError(RuntimeError):
    """Raised when a configured provider cannot produce a valid model response."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
        code: str = "provider_error",
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.code = code


class ModelProviderValidationError(ModelProviderError):
    """Raised when a provider response fails the request validator."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
        cause: Exception,
    ) -> None:
        super().__init__(message, attempts=attempts, code="validation_error")
        self.cause = cause


class ModelProviderCancelled(ModelProviderError):
    """Raised when a caller cancels an in-flight provider request."""

    def __init__(
        self,
        message: str,
        *,
        attempts: tuple[dict[str, Any], ...] = (),
        code: str = "request_cancelled",
    ) -> None:
        super().__init__(message, attempts=attempts, code=code)
