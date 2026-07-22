from __future__ import annotations

from app.ai.contracts import ModelProvider
from app.ai.fallback import FallbackModelProvider
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.ai.placeholder import PlaceholderModelProvider
from app.core.config import get_settings

DEFAULT_PROVIDER_ORDER = ("primary", "fallback1", "fallback2")


def _provider_order(raw_order: str) -> tuple[str, ...]:
    requested = [item.strip().lower() for item in raw_order.split(",")]
    order: list[str] = []
    for slot in [*requested, *DEFAULT_PROVIDER_ORDER]:
        if slot in DEFAULT_PROVIDER_ORDER and slot not in order:
            order.append(slot)
    return tuple(order)


def get_model_provider(*, timeout_seconds: int | None = None) -> ModelProvider:
    """Return the configured provider, with automatic fallback chain if set."""

    settings = get_settings()
    if settings.model_provider == "placeholder":
        return PlaceholderModelProvider()
    if settings.model_provider not in {"openai_compatible", "openai-compatible"}:
        return PlaceholderModelProvider()

    effective_timeout = timeout_seconds or settings.model_timeout_seconds

    provider_settings = {
        "primary": (
            settings.model_name,
            settings.model_base_url,
            settings.model_api_key,
            settings.model_temperature,
        ),
        "fallback1": (
            settings.fallback1_name,
            settings.fallback1_base_url,
            settings.fallback1_api_key,
            settings.fallback1_temperature,
        ),
        "fallback2": (
            settings.fallback2_name,
            settings.fallback2_base_url,
            settings.fallback2_api_key,
            settings.fallback2_temperature,
        ),
    }
    providers = [
        OpenAICompatibleModelProvider(
            base_url=provider_settings[slot][1],
            api_key=provider_settings[slot][2],
            model_name=provider_settings[slot][0],
            timeout_seconds=effective_timeout,
            temperature=provider_settings[slot][3],
        )
        for slot in _provider_order(settings.model_provider_order)
    ]
    configured = [provider for provider in providers if provider.configured]
    if not configured:
        return providers[0]
    if len(configured) == 1:
        return configured[0]
    return FallbackModelProvider(configured)
