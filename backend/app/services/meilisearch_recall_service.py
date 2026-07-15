from __future__ import annotations

import json

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
        try:
            with httpx.Client(timeout=self.timeout_seconds, trust_env=False) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise SearchUnavailable(f"Meilisearch 不可用：{exc}") from exc

        raw_hits = data.get("hits", [])
        if not isinstance(raw_hits, list):
            raise SearchUnavailable("Meilisearch 返回格式无效")

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
