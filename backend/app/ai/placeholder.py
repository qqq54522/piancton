from typing import Any

from app.ai.contracts import ModelProviderNotConfigured, ModelRequest


class PlaceholderModelProvider:
    name = "placeholder"

    @property
    def configured(self) -> bool:
        return False

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        raise ModelProviderNotConfigured(
            f"模型 Provider 尚未配置，无法执行任务：{request.task}"
        )
