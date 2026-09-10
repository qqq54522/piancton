from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class VikingKnowledgeServiceClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class VikingKnowledgeServiceChatResult:
    query: str
    response: dict[str, Any]
    generated_answer: str
    reasoning_content: str
    result_list: list[dict[str, Any]]


class VikingKnowledgeServiceClient:
    """REST client for Volcengine Viking Knowledge Base service chat.

    This service is used as a selling-point judge only. The project database
    remains authoritative for images, publish status, permissions, and accepted
    asset relations.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        service_resource_id: str,
        chat_path: str = "/api/knowledge/service/chat",
        timeout_seconds: float = 12.0,
        result_limit: int = 6,
    ):
        self.base_url = _normalize_base_url(base_url)
        self.api_key = api_key.strip()
        self.service_resource_id = service_resource_id.strip()
        self.chat_path = chat_path if chat_path.startswith("/") else f"/{chat_path}"
        self.timeout_seconds = max(0.5, timeout_seconds)
        self.result_limit = max(1, min(result_limit, 20))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.service_resource_id)

    def chat(self, query: str) -> VikingKnowledgeServiceChatResult:
        question = query.strip()
        if not question:
            raise VikingKnowledgeServiceClientError("知识库服务查询不能为空")
        if not self.configured:
            raise VikingKnowledgeServiceClientError("知识库服务尚未配置完整")
        payload = {
            "service_resource_id": self.service_resource_id,
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ],
            "stream": False,
        }
        data = self._post_json(payload)
        service_code = data.get("code")
        if service_code not in (None, 0, "0"):
            message = str(data.get("message") or "知识库服务返回业务错误")
            raise VikingKnowledgeServiceClientError(message[:160])
        body = data.get("data") if isinstance(data.get("data"), dict) else data
        if not isinstance(body, dict):
            raise VikingKnowledgeServiceClientError("知识库服务返回格式无效")
        return VikingKnowledgeServiceChatResult(
            query=question,
            response=data,
            generated_answer=_string(body.get("generated_answer")),
            reasoning_content=_string(body.get("reasoning_content")),
            result_list=_result_list(body.get("result_list"))[: self.result_limit],
        )

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.post(
                    f"{self.base_url}{self.chat_path}",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise VikingKnowledgeServiceClientError(
                f"知识库服务返回异常状态：{exc.response.status_code}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise VikingKnowledgeServiceClientError("知识库服务调用超时") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise VikingKnowledgeServiceClientError(
                f"知识库服务调用失败：{exc}"
            ) from exc
        if not isinstance(data, dict):
            raise VikingKnowledgeServiceClientError("知识库服务返回格式无效")
        return data


def _normalize_base_url(value: str) -> str:
    stripped = value.strip().rstrip("/")
    if not stripped:
        return ""
    if stripped.startswith(("http://", "https://")):
        return stripped
    return f"https://{stripped}"


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _result_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
