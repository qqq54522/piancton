from __future__ import annotations

from app.ai.contracts import ModelProvider
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.ai.placeholder import PlaceholderModelProvider
from app.core.config import get_settings


def get_model_provider(*, timeout_seconds: int | None = None) -> ModelProvider:
    """Return the configured provider.

    Business services must continue depending on ModelProvider, not vendor SDKs.
    """

    settings = get_settings()
    if settings.model_provider == "placeholder":
        return PlaceholderModelProvider()
    if settings.model_provider in {"openai_compatible", "openai-compatible"}:
        return OpenAICompatibleModelProvider(
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
            model_name=settings.model_name,
            timeout_seconds=timeout_seconds or settings.model_timeout_seconds,
        )
    return PlaceholderModelProvider()
