from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from app.models.image import Image
from app.schemas.ai import SearchUnderstanding


class SearchUnavailable(RuntimeError):
    """Raised when an external search backend cannot serve a request."""


@dataclass(frozen=True)
class SearchDeadline:
    """Shared wall-clock budget for one online search request."""

    expires_at: float

    @classmethod
    def from_timeout(cls, timeout_seconds: float) -> "SearchDeadline":
        return cls(time.monotonic() + max(0.01, timeout_seconds))

    def remaining(self) -> float:
        return max(0.0, self.expires_at - time.monotonic())

    def clamp(self, configured_seconds: float) -> float:
        return min(max(0.01, configured_seconds), self.remaining())

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0


@dataclass(frozen=True)
class SearchHit:
    image: Image
    score: float | None = None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalSearchCandidate:
    image_id: str
    score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConceptMatch:
    concept_id: str
    code: str
    name: str
    score: float
    system_codes: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConceptRouteOutcome:
    hits: list[SearchHit]
    active_matches: tuple[ConceptMatch, ...] = ()
    used_fallback: bool = False


@dataclass(frozen=True)
class SearchQueryProfile:
    original_query: str
    normalized_query: str
    explicit_system_codes: tuple[str, ...] = ()
    candidate_concept_codes: tuple[str, ...] = ()
    pain_points: tuple[str, ...] = ()
    desired_outcomes: tuple[str, ...] = ()
    visual_constraints: tuple[str, ...] = ()
    channel_or_size: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()
    ambiguity: tuple[str, ...] = ()
    confidence: float = 0.0


BranchStatus = Literal["ok", "skipped", "timed_out", "failed"]


@dataclass(frozen=True)
class ModelAttemptDiagnostic:
    task: str
    layer: str
    provider: str
    model: str
    status: str
    duration_ms: int
    fallback_index: int | None = None
    error: str = ""


@dataclass(frozen=True)
class SearchBranchDiagnostic:
    source: str
    status: BranchStatus
    duration_ms: int
    result_count: int = 0
    cache_hit: bool = False
    detail: str | None = None
    attempts: tuple[ModelAttemptDiagnostic, ...] = ()


T = TypeVar("T", covariant=True)


@dataclass(frozen=True)
class SearchBranchResult(Generic[T]):
    value: T | None
    diagnostic: SearchBranchDiagnostic


@dataclass(frozen=True)
class QueryUnderstandingOutcome:
    """Preserves completed layers when a later understanding stage fails."""

    understanding: SearchUnderstanding | None
    routed_system_codes: tuple[str, ...] = ()
    route_completed: bool = False
    selling_point_completed: bool = False
    proof_point_completed: bool = False


@dataclass(frozen=True)
class RerankOutcome:
    hits: list[SearchHit]
    used: bool
    error: str | None = None
