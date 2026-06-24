from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.ai.contracts import ModelProviderError, ModelProviderNotConfigured, ModelRequest


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
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        if not self.configured:
            raise ModelProviderNotConfigured("OpenAI-compatible 模型 Provider 尚未配置完整")

        payload = {
            "model": self.model_name,
            "messages": self._messages(request),
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        response_payload = self._post_chat_completions(payload)
        return self._extract_json(response_payload)

    def _messages(self, request: ModelRequest) -> list[dict[str, Any]]:
        system_prompt = (
            "你是标签图片仓库的结构化分析引擎。"
            "必须只返回一个合法 JSON 对象，不要返回 Markdown、解释或代码块。"
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
                    "image_url": {"url": self._image_data_url(request.image_path)},
                },
            ]
        else:
            user_content = task_text
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

    def _image_data_url(self, image_path: Path) -> str:
        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
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
