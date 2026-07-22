from __future__ import annotations

import logging
from typing import Any

from app.ai.contracts import ModelProviderError, ModelRequest

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

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            try:
                result = provider.generate_json(request)
                if i > 0:
                    logger.info(
                        "fallback provider #%d (%s) succeeded after earlier failures",
                        i,
                        provider.model_name,
                    )
                return result
            except (ModelProviderError, Exception) as exc:
                logger.warning(
                    "provider #%d (%s) failed: %s — trying next",
                    i,
                    provider.model_name,
                    exc,
                )
                last_error = exc
        raise ModelProviderError(f"all {len(self.providers)} providers failed") from last_error
