from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, Protocol

ModelTask = Literal[
    "image_content_analysis",
    "secondary_selling_point_classification",
    "search_intent_understanding",
    "copy_selling_point_matching",
    "image_summary_match",
]


@dataclass(frozen=True)
class ModelRequest:
    task: ModelTask
    prompt: str
    input_text: str = ""
    image_path: Optional[Path] = None


class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(self, request: ModelRequest) -> dict[str, Any]: ...


class ModelProviderNotConfigured(RuntimeError):
    """Raised until the user selects and configures a real model provider."""


class ModelProviderError(RuntimeError):
    """Raised when a configured provider cannot produce a valid model response."""
