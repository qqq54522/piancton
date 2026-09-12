from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
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
    item_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VolcAiSearchStreamEvent:
    step: str = ""
    content: str = ""
    item_ids: tuple[str, ...] = ()
    suggestions: tuple[str, ...] = ()
    done: bool = False
    response: dict[str, Any] | None = None


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
        recommend_path: str = "",
        behavior_dataset_id: str = "",
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
        self.recommend_path = _normalize_path(recommend_path)
        self.behavior_dataset_id = behavior_dataset_id.strip()
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

    @property
    def recommend_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.recommend_path)

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
        answer_parts: list[str] = []
        suggestions: list[str] = []
        item_ids: list[str] = []
        frames: list[dict[str, Any]] = []
        for event in self.stream_chat_search(
            query,
            session_id=session_id,
            user_id=user_id,
            dataset_ids=dataset_ids,
            page_size=page_size,
            enable_suggestions=enable_suggestions,
            image_url=image_url,
        ):
            if event.content:
                answer_parts.append(event.content)
            suggestions.extend(event.suggestions)
            item_ids.extend(event.item_ids)
            if event.response:
                frames.append(event.response)
        answer = "".join(answer_parts).strip()
        if not answer:
            raise VolcAiSearchClientError("AI Search 对话返回未包含可用回答")
        return VolcAiSearchChatResult(
            session_id=session_id,
            query=query,
            answer=answer,
            response={"events": frames},
            suggestions=list(dict.fromkeys(item for item in suggestions if item))[:6],
            item_ids=list(dict.fromkeys(item for item in item_ids if item)),
        )

    def chat_opening(
        self,
        *,
        session_id: str,
        user_id: str = "",
    ) -> VolcAiSearchChatResult:
        """Load the opening configured for the AI Search application."""
        answer_parts: list[str] = []
        suggestions: list[str] = []
        item_ids: list[str] = []
        frames: list[dict[str, Any]] = []
        for event in self.stream_chat_opening(
            session_id=session_id,
            user_id=user_id,
        ):
            if event.content:
                answer_parts.append(event.content)
            suggestions.extend(event.suggestions)
            item_ids.extend(event.item_ids)
            if event.response:
                frames.append(event.response)
        answer = "".join(answer_parts).strip()
        suggestions = list(dict.fromkeys(item for item in suggestions if item))[:6]
        item_ids = list(dict.fromkeys(item for item in item_ids if item))
        if not any((answer, suggestions, item_ids)):
            raise VolcAiSearchClientError("AI Search 对话开场未包含可用内容")
        return VolcAiSearchChatResult(
            session_id=session_id,
            query="",
            answer=answer,
            response={"events": frames},
            suggestions=suggestions,
            item_ids=item_ids,
        )

    def stream_chat_search(
        self,
        query: str,
        *,
        session_id: str,
        user_id: str = "",
        dataset_ids: list[str] | None = None,
        page_size: int = 10,
        enable_suggestions: bool = True,
        image_url: str = "",
    ) -> Iterator[VolcAiSearchStreamEvent]:
        """Yield native ChatSearch frames instead of buffering and re-chunking text."""
        if not self.chat_search_configured:
            raise VolcAiSearchClientError("AI Search 对话接口尚未配置完整")
        payload = self._chat_payload(
            query,
            session_id=session_id,
            user_id=user_id,
            dataset_ids=dataset_ids,
            page_size=page_size,
            enable_suggestions=enable_suggestions,
            image_url=image_url,
        )
        yield from self._stream_chat_payload(payload, allow_content_before_reply=False)

    def stream_chat_opening(
        self,
        *,
        session_id: str,
        user_id: str = "",
    ) -> Iterator[VolcAiSearchStreamEvent]:
        if not self.chat_search_configured:
            raise VolcAiSearchClientError("AI Search 对话接口尚未配置完整")
        payload = {
            "session_id": session_id,
            "user": {"_user_id": user_id},
            "context": {"location": {}},
            "opening_remarks": True,
        }
        yield from self._stream_chat_payload(payload, allow_content_before_reply=True)

    def query_recommendations(
        self,
        *,
        user_id: str = "",
        page_size: int = 8,
    ) -> list[str]:
        """Return the application-level phrases used by the search placeholder."""
        if not self.search_configured:
            raise VolcAiSearchClientError("AI Search 搜索接口尚未配置完整")
        response = self._post_json(
            f"{self.search_path.rstrip('/')}/query_recommendation",
            {
                "user": {"_user_id": user_id},
                "page_size": max(1, min(page_size, 20)),
            },
        )
        return _extract_recommendation_queries(response)[:page_size]

    def recommend_items(
        self,
        *,
        user_id: str,
        parent_item_id: str,
        page_size: int = 12,
        disable_personalize: bool = False,
    ) -> list[str]:
        """Return item ids from a configured AI Search recommendation scene."""
        if not self.recommend_configured:
            raise VolcAiSearchClientError("AI Search 推荐场景尚未配置完整")
        response = self._post_json(
            self.recommend_path,
            {
                "user": {"_user_id": user_id},
                "parent_items": [{"_id": parent_item_id}],
                "page_size": max(1, min(page_size, 400)),
                "disable_personalize": disable_personalize,
                "output_fields": ["image_id", "identity_code"],
            },
        )
        return _extract_recommendation_item_ids(response)[:page_size]

    def _stream_chat_payload(
        self,
        payload: dict[str, Any],
        *,
        allow_content_before_reply: bool,
    ) -> Iterator[VolcAiSearchStreamEvent]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        reply_started = False
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}{self.chat_search_path}",
                    headers=headers,
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    for raw_line in response.iter_lines():
                        line = raw_line.strip()
                        if not line or line.startswith(("event:", ":")):
                            continue
                        if line.startswith("data:"):
                            line = line[5:].strip()
                        if not line or line == "[DONE]":
                            continue
                        try:
                            frame = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise VolcAiSearchClientError(
                                "AI Search 对话流包含无法解析的数据"
                            ) from exc
                        if not isinstance(frame, dict):
                            continue
                        result = frame.get("result")
                        result = result if isinstance(result, dict) else frame
                        step_info = result.get("step_info")
                        step_info = step_info if isinstance(step_info, dict) else {}
                        step = str(step_info.get("step") or "").strip()
                        if step:
                            reply_started = _normalize_step(step) == "reply"
                        content = result.get("content")
                        text = (
                            str(content)
                            if isinstance(content, str)
                            and (reply_started or allow_content_before_reply)
                            else ""
                        )
                        suggestions = tuple(_extract_suggestions(result))
                        item_ids = tuple(_extract_chat_item_ids(result))
                        done = bool(result.get("stop_reason"))
                        if step or text or suggestions or item_ids or done:
                            yield VolcAiSearchStreamEvent(
                                step=step,
                                content=text,
                                item_ids=item_ids,
                                suggestions=suggestions,
                                done=done,
                                response=frame,
                            )
        except httpx.HTTPStatusError as exc:
            detail = _http_error_detail(exc.response)
            raise VolcAiSearchClientError(
                f"AI Search 返回异常状态：{exc.response.status_code}{detail}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise VolcAiSearchClientError("AI Search 对话调用超时") from exc
        except httpx.HTTPError as exc:
            raise VolcAiSearchClientError(f"AI Search 对话调用失败：{exc}") from exc

    def write_behavior_events(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        if not (self.base_url and self.api_key and self.behavior_dataset_id):
            raise VolcAiSearchClientError("AI Search 用户行为数据集尚未配置完整")
        if not events:
            return {"submitted": 0}
        return self._post_json(
            f"/api/v1/dataset/{self.behavior_dataset_id}/write",
            {"fields": events},
        )

    def _chat_payload(
        self,
        query: str,
        *,
        session_id: str,
        user_id: str,
        dataset_ids: list[str] | None,
        page_size: int,
        enable_suggestions: bool,
        image_url: str,
    ) -> dict[str, Any]:
        content: list[dict[str, Any]] = [{"type": "text", "text": query}]
        if image_url.strip():
            content.append(
                {"type": "image_url", "image_url": {"url": image_url.strip()}}
            )
        return {
            "session_id": session_id,
            "input_message": {"content": content},
            "user": {"_user_id": user_id},
            "search_param": {
                "page_size": max(1, min(page_size, 50)),
                "dataset_ids": dataset_ids or self.chat_dataset_ids,
            },
            "enable_suggestions": enable_suggestions,
        }

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
        "recommendation_results",
        "recommend_results",
        "rec_results",
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


def _extract_recommendation_item_ids(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 10:
            return
        if isinstance(value, dict):
            fields = next(
                (
                    value.get(key)
                    for key in ("fields", "display_fields", "item", "doc", "document")
                    if isinstance(value.get(key), dict)
                ),
                None,
            )
            candidates = [fields, value] if fields is not None else [value]
            for candidate in candidates:
                item_id = str(
                    candidate.get("image_id")
                    or candidate.get("_id")
                    or candidate.get("item_id")
                    or ""
                ).strip()
                if item_id:
                    values.append(item_id)
                    break
            for item in value.values():
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth + 1)

    visit(payload)
    return list(dict.fromkeys(values))


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


def _extract_recommendation_queries(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []

    def visit(value: Any, depth: int = 0) -> None:
        if depth > 8:
            return
        if isinstance(value, dict):
            for key in ("recommendation_queries", "recommendationQueries"):
                items = value.get(key)
                if not isinstance(items, list):
                    continue
                for item in items:
                    if isinstance(item, str):
                        query = item.strip()
                    elif isinstance(item, dict):
                        query = str(
                            item.get("query")
                            or item.get("text")
                            or item.get("keyword")
                            or ""
                        ).strip()
                    else:
                        query = ""
                    if query:
                        values.append(query)
            for item in value.values():
                visit(item, depth + 1)
        elif isinstance(value, list):
            for item in value:
                visit(item, depth + 1)

    visit(payload)
    return list(dict.fromkeys(values))


def _normalize_step(value: str) -> str:
    return value.strip().lower().replace("_", " ").replace("-", " ")


def _extract_chat_item_ids(payload: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    citation = payload.get("citation")
    citations = citation if isinstance(citation, list) else [citation]
    for item in citations:
        if not isinstance(item, dict) or item.get("type") not in {None, "item"}:
            continue
        item_id = str(item.get("_id") or item.get("item_id") or "").strip()
        if item_id:
            ids.append(item_id)

    nested_sources: list[Any] = []
    nested_payload = payload.get("payload")
    if isinstance(nested_payload, dict):
        nested_sources.extend(
            nested_payload.get(key)
            for key in ("related_rec_items", "search_results", "items", "results")
        )
        rec = nested_payload.get("rec")
        if isinstance(rec, dict):
            nested_sources.append(rec.get("rec_results"))
    for source in nested_sources:
        if not isinstance(source, list):
            continue
        for item in source:
            if not isinstance(item, dict):
                continue
            display_fields = item.get("display_fields")
            display_fields = display_fields if isinstance(display_fields, dict) else {}
            item_id = str(
                item.get("_id")
                or item.get("item_id")
                or display_fields.get("image_id")
                or display_fields.get("_id")
                or ""
            ).strip()
            if item_id:
                ids.append(item_id)
    return list(dict.fromkeys(ids))


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
