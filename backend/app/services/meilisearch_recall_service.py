from __future__ import annotations

import json
import time
from urllib.parse import urlparse

import httpx

from app.repositories.image_repository import ImageRepository
from app.services.search_models import (
    ExternalSearchCandidate,
    SearchHit,
    SearchUnavailable,
)


class MeilisearchRecallService:
    def __init__(
        self,
        repo: ImageRepository,
        *,
        url: str = "",
        api_key: str = "",
        index: str = "images",
        timeout_seconds: float = 2.0,
    ):
        self.repo = repo
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.index = index
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def search(self, keyword: str, limit: int) -> list[SearchHit]:
        return self.hydrate(self.recall_candidates(keyword, limit))

    def recall_candidates(
        self,
        keyword: str,
        limit: int,
    ) -> list[ExternalSearchCandidate]:
        if not self.url:
            raise SearchUnavailable("Meilisearch URL 未配置")

        url = f"{self.url}/indexes/{self.index}/search"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "q": keyword,
            "limit": limit,
            "attributesToRetrieve": ["id"],
            "showRankingScore": True,
            "filter": "status = active",
        }
        started = time.monotonic()
        status = "failed"
        error = ""
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_hits = data.get("hits", [])
                if not isinstance(raw_hits, list):
                    status = "failed"
                    error = "Meilisearch 返回格式无效"
                    raise SearchUnavailable(error)
                status = "ok"
        except httpx.TimeoutException as exc:
            status = "timed_out"
            error = "Meilisearch 调用超时"
            raise SearchUnavailable(error) from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            error = f"Meilisearch 不可用：{exc}"
            raise SearchUnavailable(error) from exc
        finally:
            _record_meilisearch_trace(
                provider=urlparse(self.url).hostname or self.url,
                model=self.index,
                status=status,
                duration_ms=round((time.monotonic() - started) * 1000),
                error=error,
            )

        ids: list[str] = []
        score_by_id: dict[str, float] = {}
        for raw_hit in raw_hits:
            if not isinstance(raw_hit, dict):
                continue
            image_id = raw_hit.get("id") or raw_hit.get("image_id")
            if not isinstance(image_id, str):
                continue
            ids.append(image_id)
            score = raw_hit.get("_rankingScore")
            if isinstance(score, (int, float)):
                score_by_id[image_id] = max(0.0, min(float(score), 1.0))

        return [
            ExternalSearchCandidate(
                image_id=image_id,
                score=score_by_id.get(image_id, 0.9),
                reasons=("Meilisearch 匹配",),
            )
            for image_id in ids
        ]

    def hydrate(
        self,
        candidates: list[ExternalSearchCandidate],
    ) -> list[SearchHit]:
        images = self.repo.get_many_by_ids([item.image_id for item in candidates])
        by_id = {item.image_id: item for item in candidates}
        return [
            SearchHit(
                image=image,
                score=by_id[image.id].score,
                reasons=by_id[image.id].reasons,
            )
            for image in images
        ]


def _record_meilisearch_trace(
    *,
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
                task="search_index",
                layer_name="搜索索引：Meilisearch",
                provider=provider,
                model=model,
                status=status,
                duration_ms=duration_ms,
                error_summary=error,
            )
    except Exception:
        return
