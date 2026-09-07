from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


class VikingDBClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class VikingDBUpsertResult:
    submitted: int
    response: dict[str, Any]


@dataclass(frozen=True)
class VikingDBSearchResult:
    query: str
    response: dict[str, Any]
    matches: list[dict[str, Any]]


@dataclass(frozen=True)
class VikingDBDeleteResult:
    response: dict[str, Any]


class VikingDBClient:
    """Small REST client for VikingDB raw-data upserts.

    The project database remains authoritative. VikingDB stores a derived,
    rebuildable search index and receives only metadata plus search text.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        collection_name: str,
        upsert_path: str = "/api/vikingdb/data/upsert",
        search_path: str = "/api/vikingdb/data/search/multi_modal",
        timeout_seconds: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.collection_name = collection_name.strip()
        self.upsert_path = upsert_path if upsert_path.startswith("/") else f"/{upsert_path}"
        self.search_path = search_path if search_path.startswith("/") else f"/{search_path}"
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.collection_name)

    def upsert_documents(
        self,
        documents: list[dict[str, Any]],
        *,
        async_write: bool = False,
    ) -> VikingDBUpsertResult:
        if not self.configured:
            raise VikingDBClientError("VikingDB 尚未配置完整")
        if len(documents) > 100:
            raise VikingDBClientError("VikingDB 单次写入最多 100 条，请分批提交")
        payload = {
            "collection_name": self.collection_name,
            "async": async_write,
            "data": documents,
        }
        data = self._post_json(self.upsert_path, payload)
        return VikingDBUpsertResult(submitted=len(documents), response=data)

    def delete_all_documents(self) -> VikingDBDeleteResult:
        if not self.configured:
            raise VikingDBClientError("VikingDB 尚未配置完整")
        payload = {
            "collection_name": self.collection_name,
            "del_all": True,
        }
        data = self._post_json("/api/vikingdb/data/delete", payload)
        return VikingDBDeleteResult(response=data)

    def search_text(
        self,
        query: str,
        *,
        index_name: str,
        limit: int = 8,
        filter_expression: dict[str, Any] | None = None,
        output_fields: list[str] | None = None,
    ) -> VikingDBSearchResult:
        if not self.configured or not index_name.strip():
            raise VikingDBClientError("VikingDB 尚未配置完整")
        payload: dict[str, Any] = {
            "collection_name": self.collection_name,
            "index_name": index_name.strip(),
            "text": query,
            "instruction": {"auto_fill": True},
            "limit": max(1, min(limit, 100)),
            "output_fields": output_fields
            or [
                "doc_id",
                "doc_type",
                "source_id",
                "concept_code",
                "channel",
                "status",
                "search_text",
            ],
        }
        if filter_expression:
            payload["filter"] = filter_expression
        response = self._post_json(self.search_path, payload)
        return VikingDBSearchResult(
            query=query,
            response=response,
            matches=_extract_matches(response),
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.post(f"{self.base_url}{path}", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            raise VikingDBClientError(
                f"VikingDB 返回异常状态：{exc.response.status_code}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise VikingDBClientError("VikingDB 调用超时") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise VikingDBClientError(f"VikingDB 调用失败：{exc}") from exc
        if not isinstance(data, dict):
            raise VikingDBClientError("VikingDB 返回格式无效")
        return data


def _extract_matches(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("data", "results", "result", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_matches(value)
            if nested:
                return nested
    return []
