from __future__ import annotations

import json
import time
from typing import Any

import httpx


class MeilisearchClientError(RuntimeError):
    pass


MEILISEARCH_SEARCHABLE_ATTRIBUTES = (
    "title",
    "acceptedConceptNames",
    "acceptedConceptPhrases",
    "assetSearchPhrases",
    "caption",
    "semanticProfileBusinessIntent",
    "semanticProfileVisualFacts",
    "semanticProfileScenes",
    "semanticProfileSearchPhrases",
    "searchableText",
    "pendingConceptNames",
)


class MeilisearchClient:
    def __init__(
        self,
        *,
        url: str,
        api_key: str = "",
        index: str = "images",
        timeout_seconds: float = 10.0,
    ):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.index = index
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def ensure_index(self) -> str | None:
        self._require_configured()
        if self._index_exists():
            return None
        payload = {"uid": self.index, "primaryKey": "id"}
        return self._request("POST", "/indexes", json=payload).get("taskUid")

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def configure_index(self) -> str | None:
        self._require_configured()
        self.ensure_index()
        settings = {
            "searchableAttributes": list(MEILISEARCH_SEARCHABLE_ATTRIBUTES),
            "filterableAttributes": [
                "status",
                "assetGroupId",
                "assetRole",
                "acceptedConceptCodes",
                "acceptedConceptSystems",
                "manualConceptCodes",
                "acceptedAiConceptCodes",
                "pendingAiConceptCodes",
                "excludedConceptCodes",
                "channel",
            ],
            "sortableAttributes": ["createdAt", "downloadCount"],
            "rankingRules": [
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
            ],
        }
        return self._request(
            "PATCH",
            f"/indexes/{self.index}/settings",
            json=settings,
        ).get("taskUid")

    def add_documents(self, documents: list[dict[str, Any]]) -> str | None:
        self._require_configured()
        if not documents:
            return None
        return self._request(
            "POST",
            f"/indexes/{self.index}/documents",
            params={"primaryKey": "id"},
            json=documents,
        ).get("taskUid")

    def delete_documents(self, image_ids: list[str]) -> str | None:
        self._require_configured()
        if not image_ids:
            return None
        return self._request(
            "POST",
            f"/indexes/{self.index}/documents/delete-batch",
            json=image_ids,
        ).get("taskUid")

    def delete_index(self) -> str | None:
        self._require_configured()
        return self._request("DELETE", f"/indexes/{self.index}").get("taskUid")

    def search(self, query: str, *, limit: int = 10) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/indexes/{self.index}/search",
            json={
                "q": query,
                "limit": limit,
                "attributesToRetrieve": ["id", "title", "manualPrimaryLabelCode"],
                "showRankingScore": True,
            },
        )

    def get_task(self, task_uid: str | int) -> dict[str, Any]:
        return self._request("GET", f"/tasks/{task_uid}")

    def wait_task(
        self,
        task_uid: str | int | None,
        *,
        timeout_seconds: float = 15.0,
    ) -> dict[str, Any] | None:
        if task_uid is None:
            return None
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            task = self.get_task(task_uid)
            status = task.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                if status != "succeeded":
                    raise MeilisearchClientError(f"Meilisearch task failed: {task}")
                return task
            time.sleep(0.2)
        raise MeilisearchClientError(f"Meilisearch task timed out: {task_uid}")

    def _index_exists(self) -> bool:
        try:
            self._request("GET", f"/indexes/{self.index}")
            return True
        except MeilisearchClientError as exc:
            if "404" in str(exc):
                return False
            raise

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        self._require_configured()
        headers = kwargs.pop("headers", {})
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.request(
                    method,
                    f"{self.url}{path}",
                    headers=headers,
                    **kwargs,
                )
                response.raise_for_status()
                if not response.content:
                    return {}
                data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise MeilisearchClientError(str(exc)) from exc
        if not isinstance(data, dict):
            raise MeilisearchClientError("Meilisearch 返回格式无效")
        return data

    def _require_configured(self) -> None:
        if not self.url:
            raise MeilisearchClientError("MEILISEARCH_URL 未配置")
