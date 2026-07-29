from __future__ import annotations

from typing import Literal

from app.ai.contracts import ModelProvider
from app.ai.fallback import FallbackModelProvider
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.ai.placeholder import PlaceholderModelProvider
from app.core.config import get_settings

DEFAULT_PROVIDER_ORDER = ("primary", "fallback1", "fallback2")
ProviderPurpose = Literal["default", "image_analysis", "asset_phrase", "search"]


def _provider_order(raw_order: str) -> tuple[str, ...]:
    requested = [item.strip().lower() for item in raw_order.split(",") if item.strip()]
    if not requested:
        return DEFAULT_PROVIDER_ORDER
    order: list[str] = []
    for slot in requested:
        if slot in DEFAULT_PROVIDER_ORDER and slot not in order:
            order.append(slot)
    return tuple(order)


def _provider(
    *,
    model_name: str,
    base_url: str,
    api_key: str,
    temperature: float,
    timeout_seconds: int,
) -> OpenAICompatibleModelProvider:
    return OpenAICompatibleModelProvider(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
        temperature=temperature,
    )


def _single_purpose_provider(
    settings,
    purpose: Literal["image_analysis", "asset_phrase"],
    timeout_seconds: int,
) -> ModelProvider:
    prefix = "image_analysis" if purpose == "image_analysis" else "asset_phrase"
    provider = _provider(
        model_name=getattr(settings, f"{prefix}_model_name", "")
        or settings.model_name,
        base_url=getattr(settings, f"{prefix}_base_url", "")
        or settings.model_base_url,
        api_key=getattr(settings, f"{prefix}_api_key", "")
        or settings.model_api_key,
        temperature=getattr(settings, f"{prefix}_temperature", 0.2),
        timeout_seconds=timeout_seconds,
    )
    return provider if provider.configured else PlaceholderModelProvider()


def _search_provider(settings, timeout_seconds: int) -> ModelProvider:
    providers = [
        _provider(
            model_name=settings.model_name,
            base_url=settings.model_base_url,
            api_key=settings.model_api_key,
            temperature=settings.model_temperature,
            timeout_seconds=timeout_seconds,
        ),
        _provider(
            model_name=getattr(settings, "search_fallback_model_name", ""),
            base_url=getattr(settings, "search_fallback_base_url", ""),
            api_key=getattr(settings, "search_fallback_api_key", ""),
            temperature=getattr(settings, "search_fallback_temperature", 0.2),
            timeout_seconds=timeout_seconds,
        ),
    ]
    configured = [provider for provider in providers if provider.configured]
    if not configured:
        return PlaceholderModelProvider()
    return configured[0] if len(configured) == 1 else FallbackModelProvider(configured)


def get_model_provider(
    *,
    timeout_seconds: int | None = None,
    purpose: ProviderPurpose = "default",
) -> ModelProvider:
    """Return a task-scoped provider without leaking fallbacks across workloads."""

    settings = get_settings()
    if settings.model_provider == "placeholder":
        return PlaceholderModelProvider()
    if settings.model_provider not in {"openai_compatible", "openai-compatible"}:
        return PlaceholderModelProvider()

    effective_timeout = timeout_seconds or settings.model_timeout_seconds
    if purpose in {"image_analysis", "asset_phrase"}:
        return _single_purpose_provider(settings, purpose, effective_timeout)
    if purpose == "search":
        return _search_provider(settings, effective_timeout)

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
        _provider(
            model_name=provider_settings[slot][0],
            base_url=provider_settings[slot][1],
            api_key=provider_settings[slot][2],
            temperature=provider_settings[slot][3],
            timeout_seconds=effective_timeout,
        )
        for slot in _provider_order(settings.model_provider_order)
    ]
    configured = [provider for provider in providers if provider.configured]
    if not configured:
        return providers[0]
    if len(configured) == 1:
        return configured[0]
    return FallbackModelProvider(configured)
