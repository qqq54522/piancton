from typing import Any, Callable, TypeVar

from app.ai.contracts import (
    ModelCallResult,
    ModelProviderNotConfigured,
    ModelRequest,
)

T = TypeVar("T")


class PlaceholderModelProvider:
    name = "placeholder"

    @property
    def configured(self) -> bool:
        return False

    def generate_json(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[dict[str, Any]]:
        raise ModelProviderNotConfigured(
            f"模型 Provider 尚未配置，无法执行任务：{request.task}"
        )

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], T],
    ) -> ModelCallResult[T]:
        raise ModelProviderNotConfigured(
            f"模型 Provider 尚未配置，无法执行任务：{request.task}"
        )
