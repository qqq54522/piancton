from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Protocol

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


class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(self, request: ModelRequest) -> dict[str, Any]: ...


class ModelProviderNotConfigured(RuntimeError):
    """Raised until the user selects and configures a real model provider."""


class ModelProviderError(RuntimeError):
    """Raised when a configured provider cannot produce a valid model response."""
