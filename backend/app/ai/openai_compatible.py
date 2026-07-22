from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.ai.contracts import (
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)

SEARCH_TASK_ROLES = {
    "search_system_routing": (
        "你是六大业务体系的第一层路由决策员。"
        "你只判断体系范围，必须先核对对象和主动作，再核对时间尺度、目的与执行主体；"
        "若句式是‘通过/借助/采用X，帮你/从而Y’，X是主手段证据，Y是结果；"
        "共享词不能被当作唯一体系证据，也不得提前判断卖点或具体图片。"
    ),
    "search_intent_understanding": (
        "你是业务方搜索话术的第二层卖点决策员，并负责可选的证明点识别。"
        "你只能在第一层候选体系和当前启用目录内判断；"
        "必须区分主动作或产品入口、使用对象、目的结果与讲解方法，"
        "若句式是‘通过/借助/采用X，帮你/从而Y’，X是核心方法谓词，Y是结果；"
        "不得让通用结果词或方法细节覆盖更主要的入口证据；"
        "只有原话明确点名功能、方法、案例、数据或具体证据时才输出证明点；"
        "每个证明点还必须从该证明点已有搜索语言中原样选择一至三条最具体的 evidence_terms。"
    ),
}


class OpenAICompatibleModelProvider:
    """OpenAI Chat Completions compatible provider.

    This adapter intentionally owns vendor envelope details. Services continue
    to depend only on the neutral ModelProvider protocol.
    """

    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: int = 120,
        temperature: float = 0.2,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        if not self.configured:
            raise ModelProviderNotConfigured("OpenAI-compatible 模型 Provider 尚未配置完整")

        payload = {
            "model": self.model_name,
            "messages": self._messages(request),
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        if request.timeout_seconds is None:
            response_payload = self._post_chat_completions(payload)
        else:
            response_payload = self._post_chat_completions(
                payload,
                timeout_seconds=request.timeout_seconds,
            )
        return self._extract_json(response_payload)

    def _messages(self, request: ModelRequest) -> list[dict[str, Any]]:
        role = SEARCH_TASK_ROLES.get(
            request.task,
            "你是标签图片仓库的结构化分析引擎。",
        )
        system_prompt = (
            role + "必须只返回一个合法 JSON 对象，不要返回 Markdown、解释或代码块。"
            "字段名称、枚举值和数组结构必须严格遵循用户给出的输出协议。"
        )
        task_text = "\n\n".join(
            section
            for section in (
                f"任务类型：{request.task}",
                request.prompt,
                f"输入文本：{request.input_text}" if request.input_text else "",
            )
            if section
        )
        user_content: str | list[dict[str, Any]]
        if request.image_path:
            user_content = [
                {"type": "text", "text": task_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": self._image_data_url(
                            request.image_path,
                            request.image_media_type,
                        )
                    },
                },
            ]
        else:
            user_content = task_text
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _image_data_url(
        self,
        image_path: Path,
        explicit_media_type: str | None = None,
    ) -> str:
        mime_type = (
            explicit_media_type
            or mimetypes.guess_type(image_path.name)[0]
            or "application/octet-stream"
        )
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _post_chat_completions(
        self,
        payload: dict[str, Any],
        *,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            request_timeout = (
                max(0.1, timeout_seconds) if timeout_seconds is not None else self.timeout_seconds
            )
            with httpx.Client(timeout=request_timeout) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 400 and "response_format" in payload:
                    fallback_payload = {**payload}
                    fallback_payload.pop("response_format", None)
                    response = client.post(url, headers=headers, json=fallback_payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise ModelProviderError(f"模型服务返回异常状态：{status}") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise ModelProviderError("模型服务调用失败") from exc
        if not isinstance(data, dict):
            raise ModelProviderError("模型服务返回格式无效")
        return data

    def _extract_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            message = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelProviderError("模型响应缺少 choices.message") from exc

        parsed = message.get("parsed")
        if isinstance(parsed, dict):
            return parsed

        content = message.get("content")
        if isinstance(content, dict):
            return content
        if isinstance(content, list):
            text = "\n".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and isinstance(part.get("text"), str)
            )
        elif isinstance(content, str):
            text = content
        else:
            raise ModelProviderError("模型响应内容为空")

        return self._parse_json_object(text)

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise ModelProviderError("模型没有返回可解析的 JSON 对象")
