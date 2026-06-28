from __future__ import annotations

from dataclasses import dataclass

from app.models.image import Image


class SearchUnavailable(RuntimeError):
    """Raised when an external search backend cannot serve a request."""


@dataclass(frozen=True)
class SearchHit:
    image: Image
    score: float | None = None
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class StrictSearchPolicy:
    primary_label: str
    primary_category: str
    confidence: float
    intent_reason: str
    exclude_terms: tuple[str, ...] = ()

    @property
    def enabled(self) -> bool:
        return self.confidence >= 0.85
