from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx


class SemanticSearchClientError(RuntimeError):
    def __init__(self, message: str, *, status: str = "failed"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class RerankResult:
    index: int
    score: float


class EmbeddingClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def embed(self, inputs: list[str]) -> list[list[float]]:
        if not self.configured:
            raise SemanticSearchClientError("Embedding API 尚未配置完整")
        payload = {"model": self.model_name, "input": inputs}
        data = self._post("/embeddings", payload)
        rows = data.get("data")
        if not isinstance(rows, list):
            raise SemanticSearchClientError("Embedding API 返回格式无效")
        vectors: list[list[float]] = []
        for row in rows:
            embedding = row.get("embedding") if isinstance(row, dict) else None
            if not isinstance(embedding, list):
                raise SemanticSearchClientError("Embedding API 缺少 embedding")
            vectors.append([float(value) for value in embedding])
        return vectors

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _post_json(
            f"{self.base_url}{path}",
            api_key=self.api_key,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            provider=_provider_label(self.base_url),
            model=self.model_name,
            task="search_embedding_recall",
            layer_name="搜索增强：Embedding 召回",
        )


class RerankerClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout_seconds: float = 5.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model_name)

    def rerank(
        self,
        *,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> list[RerankResult]:
        if not self.configured:
            raise SemanticSearchClientError("Reranker API 尚未配置完整")
        if not documents:
            return []
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
            "return_documents": False,
        }
        data = self._post("/rerank", payload)
        rows = data.get("results")
        if not isinstance(rows, list):
            raise SemanticSearchClientError("Reranker API 返回格式无效")
        results: list[RerankResult] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            index = row.get("index")
            score = row.get("relevance_score", row.get("score"))
            if isinstance(index, int) and isinstance(score, (int, float)):
                results.append(RerankResult(index=index, score=max(0.0, min(float(score), 1.0))))
        return results

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return _post_json(
            f"{self.base_url}{path}",
            api_key=self.api_key,
            payload=payload,
            timeout_seconds=self.timeout_seconds,
            provider=_provider_label(self.base_url),
            model=self.model_name,
            task="search_reranker",
            layer_name="搜索增强：Reranker 重排",
        )


def _post_json(
    url: str,
    *,
    api_key: str,
    payload: dict[str, Any],
    timeout_seconds: float,
    provider: str,
    model: str,
    task: str,
    layer_name: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    started = time.monotonic()
    status = "failed"
    error = ""
    try:
        with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                error = "语义搜索 API 返回格式无效"
                raise SemanticSearchClientError(error)
            status = "ok"
    except httpx.HTTPStatusError as exc:
        error = f"语义搜索 API 返回异常状态：{exc.response.status_code}"
        raise SemanticSearchClientError(error) from exc
    except httpx.TimeoutException as exc:
        status = "timed_out"
        error = "语义搜索 API 调用超时"
        raise SemanticSearchClientError(error, status=status) from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        error = "语义搜索 API 调用失败"
        raise SemanticSearchClientError(error) from exc
    finally:
        _record_semantic_trace(
            task=task,
            layer_name=layer_name,
            provider=provider,
            model=model,
            status=status,
            duration_ms=round((time.monotonic() - started) * 1000),
            error=error,
        )
    return data


def _record_semantic_trace(
    *,
    task: str,
    layer_name: str,
    provider: str,
    model: str,
    status: str,
    duration_ms: int,
    error: str,
) -> None:
    try:
        from app.db.session import SessionLocal
        from app.services.api_center_service import ApiCenterService

        with SessionLocal() as db:
            ApiCenterService(db).record_external_call(
                task=task,
                layer_name=layer_name,
                provider=provider,
                model=model,
                status=status,
                duration_ms=duration_ms,
                error_summary=error,
            )
    except Exception:
        # Telemetry must never turn a search enhancement failure into a request failure.
        return


def _provider_label(base_url: str) -> str:
    return urlparse(base_url).hostname or base_url[:120]
