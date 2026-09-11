from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class VolcAiSearchClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class VolcAiSearchResult:
    query: str
    response: dict[str, Any]
    matches: list[dict[str, Any]]


@dataclass(frozen=True)
class VolcAiSearchChatResult:
    session_id: str
    query: str
    answer: str
    response: dict[str, Any]
    suggestions: list[str]


class VolcAiSearchClient:
    """Small REST client for Volcengine AI Search.

    The project database remains the source of truth. AI Search stores a
    derived, rebuildable index used by the homepage search box.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        dataset_id: str,
        application_id: str = "",
        search_path: str = "",
        chat_search_path: str = "",
        chat_dataset_ids: str = "",
        timeout_seconds: float = 8.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = _normalize_bearer_token(api_key)
        self.dataset_id = dataset_id.strip()
        self.application_id = application_id.strip()
        self.search_path = _normalize_path(search_path)
        self.chat_search_path = _normalize_path(chat_search_path) or (
            f"/api/v1/application/{self.application_id}/chat_search" if self.application_id else ""
        )
        self.chat_dataset_ids = _parse_dataset_ids(chat_dataset_ids) or (
            [self.dataset_id] if self.dataset_id else []
        )
        self.timeout_seconds = max(0.5, timeout_seconds)

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.dataset_id)

    @property
    def search_configured(self) -> bool:
        return self.configured and bool(self.search_path)

    @property
    def chat_search_configured(self) -> bool:
        return bool(
            self.base_url and self.api_key and self.application_id and self.chat_search_path
        )

    def search(
        self,
        query: str,
        *,
        page_number: int = 1,
        page_size: int = 10,
        user_id: str = "",
    ) -> VolcAiSearchResult:
        if not self.search_configured:
            raise VolcAiSearchClientError("AI Search 搜索接口尚未配置完整")
        payload = {
            "query": {
                "text": query,
                "image_url": "",
            },
            "page_number": max(1, page_number),
            "page_size": max(1, min(page_size, 100)),
            "dataset_id": self.dataset_id,
            "user": {
                "_user_id": user_id,
            },
            "context": {
                "location": {},
            },
        }
        response = self._post_json(self.search_path, payload)
        return VolcAiSearchResult(
            query=query,
            response=response,
            matches=_extract_matches(response),
        )

    def chat_search(
        self,
        query: str,
        *,
        session_id: str,
        user_id: str = "",
        dataset_ids: list[str] | None = None,
        page_size: int = 10,
        enable_suggestions: bool = True,
        image_url: str = "",
    ) -> VolcAiSearchChatResult:
        if not self.chat_search_configured:
            raise VolcAiSearchClientError("AI Search 对话接口尚未配置完整")
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": query,
            }
        ]
        if image_url.strip():
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url.strip(),
                    },
                }
            )
        payload = {
            "session_id": session_id,
            "input_message": {
                "content": content,
            },
            "user": {
                "_user_id": user_id,
            },
            "search_param": {
                "page_size": max(1, min(page_size, 50)),
                "dataset_ids": dataset_ids or self.chat_dataset_ids,
            },
            "enable_suggestions": enable_suggestions,
        }
        response = self._post_json(self.chat_search_path, payload)
        answer = _extract_chat_answer(response)
        if not answer:
            raise VolcAiSearchClientError("AI Search 对话返回未包含可用回答")
        return VolcAiSearchChatResult(
            session_id=session_id,
            query=query,
            answer=answer,
            response=response,
            suggestions=_extract_suggestions(response),
        )

    def write_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.configured:
            raise VolcAiSearchClientError("AI Search 数据集接口尚未配置完整")
        if not documents:
            return {"submitted": 0}
        return self._post_json(
            f"/api/v1/dataset/{self.dataset_id}/write",
            {"fields": documents},
        )

    def delete_documents(self, ids: list[str]) -> dict[str, Any]:
        if not self.configured:
            raise VolcAiSearchClientError("AI Search 数据集接口尚未配置完整")
        ids = [item for item in dict.fromkeys(ids) if item]
        if not ids:
            return {"submitted": 0}
        return self._post_json(
            f"/api/v1/dataset/{self.dataset_id}/delete",
            {"_ids": ids},
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.post(
                    f"{self.base_url}{_normalize_path(path)}",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            detail = _http_error_detail(exc.response)
            raise VolcAiSearchClientError(
                f"AI Search 返回异常状态：{exc.response.status_code}{detail}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise VolcAiSearchClientError("AI Search 调用超时") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise VolcAiSearchClientError(f"AI Search 调用失败：{exc}") from exc
        if not isinstance(data, dict):
            raise VolcAiSearchClientError("AI Search 返回格式无效")
        return data


def _normalize_path(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    return value if value.startswith("/") else f"/{value}"


def _normalize_bearer_token(value: str) -> str:
    value = value.strip()
    if value.lower().startswith("bearer "):
        return value.split(" ", 1)[1].strip()
    return value


def _parse_dataset_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _extract_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in (
        "search_results",
        "results",
        "items",
        "data",
        "result",
        "records",
        "list",
    ):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_matches(value)
            if nested:
                return nested
    return []


def _extract_chat_answer(payload: dict[str, Any]) -> str:
    direct_paths = (
        ("answer",),
        ("content",),
        ("message",),
        ("response",),
        ("output_text",),
        ("data", "answer"),
        ("data", "content"),
        ("data", "message"),
        ("data", "response"),
        ("result", "answer"),
        ("result", "content"),
        ("result", "message"),
        ("result", "response"),
    )
    for path in direct_paths:
        value: Any = payload
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    recursive = _find_first_string(
        payload,
        preferred_keys={
            "answer",
            "content",
            "message",
            "response",
            "output",
            "text",
        },
    )
    return recursive.strip() if recursive else ""


def _extract_suggestions(payload: dict[str, Any]) -> list[str]:
    values = _find_first_string_list(
        payload,
        preferred_keys={
            "suggestions",
            "suggested_questions",
            "suggestedQuestions",
            "recommend_questions",
            "follow_up_questions",
        },
    )
    return list(dict.fromkeys(item.strip() for item in values if item.strip()))[:6]


def _find_first_string(value: Any, *, preferred_keys: set[str], depth: int = 0) -> str:
    if depth > 8:
        return ""
    if isinstance(value, dict):
        for key in preferred_keys:
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                return item
        for item in value.values():
            nested = _find_first_string(
                item,
                preferred_keys=preferred_keys,
                depth=depth + 1,
            )
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_first_string(
                item,
                preferred_keys=preferred_keys,
                depth=depth + 1,
            )
            if nested:
                return nested
    return ""


def _find_first_string_list(
    value: Any,
    *,
    preferred_keys: set[str],
    depth: int = 0,
) -> list[str]:
    if depth > 8:
        return []
    if isinstance(value, dict):
        for key in preferred_keys:
            item = value.get(key)
            if isinstance(item, list):
                strings = [str(child).strip() for child in item if str(child).strip()]
                if strings:
                    return strings
        for item in value.values():
            nested = _find_first_string_list(
                item,
                preferred_keys=preferred_keys,
                depth=depth + 1,
            )
            if nested:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_first_string_list(
                item,
                preferred_keys=preferred_keys,
                depth=depth + 1,
            )
            if nested:
                return nested
    return []


def _http_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        text = response.text.strip()
        return f"：{text[:200]}" if text else ""
    if not isinstance(payload, dict):
        return ""
    message = payload.get("message") or payload.get("Message") or payload.get("msg")
    code = payload.get("code") or payload.get("Code")
    parts = [str(item) for item in (code, message) if item]
    return f"：{' / '.join(parts)}" if parts else ""
