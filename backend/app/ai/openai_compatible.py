from __future__ import annotations

import base64
import json
import mimetypes
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
        "你是业务方搜索话术的第二层卖点决策员。"
        "你只能在第一层候选体系和当前启用目录内判断；"
        "必须区分主动作或产品入口、使用对象、目的结果与讲解方法，"
        "若句式是‘通过/借助/采用X，帮你/从而Y’，X是核心方法谓词，Y是结果；"
        "不得让通用结果词或方法细节覆盖更主要的入口证据；"
        "本层不得判断证明点、证据表达点或图片。"
    ),
    "search_proof_point_understanding": (
        "你是业务方搜索话术的第三层证明点决策员。"
        "你只能在第二层已经确认的卖点及其直属证明点目录内判断；"
        "不得新增、删除或改写卖点，也不得选择图片；"
        "只有原话明确点名功能、方法、案例、数据或具体证据时才输出证明点；"
        "每个证明点必须从现有搜索语言中原样选择一至三条 evidence_terms。"
    ),
    "search_candidate_review": (
        "你是图片搜索结果的第四层候选复核员。"
        "你不重新判断体系、卖点或证明点，不扩大候选范围；"
        "只比较用户原话、已确认搜索理解和候选图片文字证据，判断每张候选图是否承接本次需求。"
        "没有直接冲突时优先保留，只有候选图与已确认意图明显不一致时才排除。"
    ),
    "search_result_recommendation_reason": (
        "你是面向市场运营的图片推荐理由撰写员。"
        "你只能基于已确认的搜索意图、已召回图片事实、人工 accepted 卖点关系和素材话术，"
        "解释为什么这张图适合本次搜索和营销场景；不得重新排序、不得重判卖点、不得编造图片内容。"
    ),
    "asset_agent_chat": (
        "你是素材库里的业务解释助手。"
        "你帮助销售、运营和设计用素材库已确认事实解释图片、卖点、证明点和家长沟通话术；"
        "不得编造素材库未确认的信息。"
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
        self.last_attempts: list[dict[str, Any]] = []

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def generate_json(self, request: ModelRequest) -> dict[str, Any]:
        if not self.configured:
            raise ModelProviderNotConfigured("OpenAI-compatible 模型 Provider 尚未配置完整")

        started = time.monotonic()
        status = "failed"
        error = ""
        payload = {
            "model": self.model_name,
            "messages": self._messages(request),
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
        }
        try:
            if request.timeout_seconds is None:
                response_payload = self._post_chat_completions(payload)
            else:
                response_payload = self._post_chat_completions(
                    payload,
                    timeout_seconds=request.timeout_seconds,
                )
            result = self._extract_json(response_payload)
            status = "ok"
            return result
        except Exception as exc:
            error = _safe_attempt_error(exc)
            raise
        finally:
            self.last_attempts = [
                {
                    "provider": self.provider_label,
                    "model": self.model_name,
                    "status": status,
                    "duration_ms": _elapsed_ms(started),
                    "error": error,
                }
            ]

    @property
    def provider_label(self) -> str:
        host = urlparse(self.base_url).hostname or self.base_url
        if "laozhang" in host:
            return "laozhang"
        if "ohmygpt" in host:
            return "ohmygpt"
        return host

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


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


def _safe_attempt_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return message[:120]
