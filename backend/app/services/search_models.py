from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from app.models.image import Image
from app.schemas.ai import SearchUnderstanding


class SearchUnavailable(RuntimeError):
    """Raised when an external search backend cannot serve a request."""


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
class SearchBranchDiagnostic:
    source: str
    status: BranchStatus
    duration_ms: int
    result_count: int = 0
    cache_hit: bool = False
    detail: str | None = None


T = TypeVar("T", covariant=True)


@dataclass(frozen=True)
class SearchBranchResult(Generic[T]):
    value: T | None
    diagnostic: SearchBranchDiagnostic


@dataclass(frozen=True)
class QueryUnderstandingOutcome:
    """Preserves a successful first-layer route if the second layer times out."""

    understanding: SearchUnderstanding | None
    routed_system_codes: tuple[str, ...] = ()
    route_completed: bool = False
    selling_point_completed: bool = False


@dataclass(frozen=True)
class RerankOutcome:
    hits: list[SearchHit]
    used: bool
    error: str | None = None
