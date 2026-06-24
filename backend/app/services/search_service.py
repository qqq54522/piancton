from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

import httpx
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.domain.search_query_expansion import ExpandedQuery, expand_search_queries
from app.models.image import Image, ImageBusinessLabel
from app.repositories.image_repository import ImageRepository
from app.schemas.ai import SearchUnderstanding
from app.schemas.image import ScoredImage, SearchResponse
from app.services.ai_service import AiService
from app.services.serializers import image_to_read


class SearchUnavailable(RuntimeError):
    """Raised when an external search backend cannot serve a request."""


@dataclass(frozen=True)
class SearchHit:
    image: Image
    score: float | None = None
    reasons: tuple[str, ...] = ()


class SearchService:
    """Search orchestration isolated from image CRUD.

    Database fuzzy search remains the safe default. External search backends are
    shadowed behind the same contract and fall back to the database path.
    """

    def __init__(
        self,
        db: Session,
        *,
        search_backend: str = "database",
        meilisearch_url: str = "",
        meilisearch_api_key: str = "",
        meilisearch_index: str = "images",
        search_timeout_seconds: float = 2.0,
        ai_service: AiService | None = None,
    ):
        self.repo = ImageRepository(db)
        self.search_backend = search_backend.strip().lower()
        self.meilisearch_url = meilisearch_url.rstrip("/")
        self.meilisearch_api_key = meilisearch_api_key
        self.meilisearch_index = meilisearch_index
        self.search_timeout_seconds = search_timeout_seconds
        self.ai_service = ai_service

    def search(
        self,
        keyword: str,
        limit: int,
        search_mode: Literal["configured", "precise", "smart"] = "configured",
    ) -> SearchResponse:
        needle = keyword.strip().lower()
        mode = search_mode.strip().lower()
        if mode == "smart":
            return self._search_smart(keyword, limit)
        if mode == "precise":
            return self._search_database(keyword, limit)
        if self.search_backend == "meilisearch":
            try:
                hits = self._search_meilisearch(needle, limit)
                return self._build_response(
                    keyword=keyword,
                    hits=hits,
                    search_mode="meilisearch",
                    fallback=False,
                )
            except SearchUnavailable as exc:
                return self._search_database(keyword, limit, fallback_reason=str(exc))
        return self._search_database(keyword, limit)

    def _search_smart(self, keyword: str, limit: int) -> SearchResponse:
        understanding = self._understand_search(keyword)
        ai_expanded_queries = self._queries_from_understanding(understanding)
        smart_keyword = self._smart_keyword(keyword, ai_expanded_queries)
        if self.meilisearch_url:
            try:
                hits = self._search_meilisearch(smart_keyword, limit)
                return self._build_response(
                    keyword=keyword,
                    hits=hits,
                    search_mode="meilisearch",
                    fallback=False,
                    search_understanding=understanding,
                )
            except SearchUnavailable as exc:
                return self._search_database(
                    keyword,
                    limit,
                    fallback_reason=f"智能搜索降级：{exc}",
                    extra_queries=ai_expanded_queries,
                    search_understanding=understanding,
                )
        return self._search_database(
            keyword,
            limit,
            fallback_reason="智能搜索未配置 Meilisearch，已使用精准搜索兜底",
            extra_queries=ai_expanded_queries,
            search_understanding=understanding,
        )

    def _search_database(
        self,
        keyword: str,
        limit: int,
        fallback_reason: str | None = None,
        extra_queries: list[ExpandedQuery] | None = None,
        search_understanding: SearchUnderstanding | None = None,
    ) -> SearchResponse:
        hits_by_id: dict[str, SearchHit] = {}
        for query in self._database_queries(keyword, extra_queries or []):
            for image in self.repo.search(query.term, max(limit * 3, limit)):
                existing = hits_by_id.get(image.id)
                if existing is None:
                    hits_by_id[image.id] = SearchHit(
                        image=image,
                        score=query.score,
                        reasons=query.reasons,
                    )
                    continue
                scores = [
                    score
                    for score in (existing.score, query.score)
                    if score is not None
                ]
                hits_by_id[image.id] = SearchHit(
                    image=image,
                    score=max(scores) if scores else None,
                    reasons=tuple(self._unique([*existing.reasons, *query.reasons])),
                )
        hits = sorted(
            hits_by_id.values(),
            key=lambda hit: hit.score if hit.score is not None else 0.65,
            reverse=True,
        )[:limit]
        return self._build_response(
            keyword=keyword,
            hits=hits,
            search_mode="fuzzy",
            fallback=fallback_reason is not None,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
        )

    def _search_meilisearch(self, keyword: str, limit: int) -> list[SearchHit]:
        if not self.meilisearch_url:
            raise SearchUnavailable("Meilisearch URL 未配置")

        url = f"{self.meilisearch_url}/indexes/{self.meilisearch_index}/search"
        headers = {}
        if self.meilisearch_api_key:
            headers["Authorization"] = f"Bearer {self.meilisearch_api_key}"
        payload = {
            "q": keyword,
            "limit": limit,
            "attributesToRetrieve": ["id"],
            "showRankingScore": True,
        }
        try:
            with httpx.Client(timeout=self.search_timeout_seconds, trust_env=False) as client:
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

        images = self.repo.get_many_by_ids(ids)
        return [
            SearchHit(
                image=image,
                score=score_by_id.get(image.id, 0.9),
                reasons=("Meilisearch 匹配",),
            )
            for image in images
        ]

    def _build_response(
        self,
        *,
        keyword: str,
        hits: list[SearchHit],
        search_mode: Literal["fuzzy", "meilisearch"],
        fallback: bool,
        fallback_reason: str | None = None,
        search_understanding: SearchUnderstanding | None = None,
    ) -> SearchResponse:
        needle = keyword.strip().lower()
        results = [
            self._build_scored_image(hit.image, needle, hit.score, list(hit.reasons))
            for hit in hits
        ]
        return SearchResponse(
            results=results,
            search_mode=search_mode,
            fallback=fallback,
            fallback_reason=fallback_reason,
            search_understanding=search_understanding,
            match_summary=f"找到 {len(results)} 张与“{keyword}”相关的图片",
        )

    def _build_scored_image(
        self,
        image: Image,
        needle: str,
        external_score: float | None,
        external_reasons: list[str],
    ) -> ScoredImage:
        tag_names = [link.tag.name for link in image.tag_links]
        content_tag_names = [item.tag_name for item in image.content_tags]
        category_names = [item.category_name for item in image.level2_categories]
        business_labels = [
            label for label in image.business_labels if label.review_status != "rejected"
        ]
        business_label_names = [self._business_label_name(label) for label in business_labels]
        business_label_codes = [label.label_code for label in business_labels]

        title = image.title.lower()
        exact_title = bool(needle and (needle in title or title in needle))
        summary_match = bool(image.image_summary and needle in image.image_summary.lower())
        matched_tags = self._matching_names(needle, tag_names + content_tag_names)
        matched_categories = self._matching_names(
            needle,
            category_names + business_label_names + business_label_codes,
        )

        reasons = list(external_reasons)
        if exact_title:
            reasons.append("标题匹配")
        if matched_tags:
            reasons.append("标签匹配")
        if matched_categories:
            reasons.append("业务标签匹配")
        if summary_match:
            reasons.append("图片摘要匹配")
        if not reasons:
            reasons.append("搜索索引匹配")

        score = external_score
        if score is None:
            score = 1.0 if exact_title else 0.8 if matched_tags else 0.65
        score = max(0.0, min(score, 1.0))

        return ScoredImage(
            image=image_to_read(image),
            match_level=self._match_level(score),
            final_score=score,
            match_reasons=self._unique(reasons),
            matched_level1_tags=matched_tags,
            matched_level2_categories=matched_categories,
        )

    def _business_label_name(self, label: ImageBusinessLabel) -> str:
        if label.tag.parent:
            return f"{label.tag.parent.name} > {label.tag.name}"
        return label.tag.name

    def _matching_names(self, needle: str, names: list[str]) -> list[str]:
        if not needle:
            return []
        return self._unique([name for name in names if needle in name.lower()])

    def _unique(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique_values: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            unique_values.append(value)
        return unique_values

    def _database_queries(
        self,
        keyword: str,
        extra_queries: list[ExpandedQuery],
    ) -> list[ExpandedQuery]:
        unique: list[ExpandedQuery] = []
        seen: set[str] = set()
        for query in [*expand_search_queries(keyword), *extra_queries]:
            term = query.term.strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(ExpandedQuery(term, query.score, query.reasons))
        return unique

    def _understand_search(self, keyword: str) -> SearchUnderstanding | None:
        if not self.ai_service or not self.ai_service.provider.configured:
            return None
        try:
            return self.ai_service.understand_search(keyword)
        except AppError:
            return None

    def _queries_from_understanding(
        self,
        understanding: SearchUnderstanding | None,
    ) -> list[ExpandedQuery]:
        if not understanding:
            return []
        queries: list[ExpandedQuery] = []
        if understanding.normalized_query.strip():
            queries.append(
                ExpandedQuery(
                    understanding.normalized_query,
                    0.86,
                    ("AI 意图理解：标准化查询",),
                )
            )
        for item in understanding.expanded_level1_tags:
            if not item.tag.strip():
                continue
            queries.append(
                ExpandedQuery(
                    item.tag,
                    max(0.65, min(item.weight, 0.95)),
                    (f"AI 意图扩展：{item.tag}",),
                )
            )
        for item in understanding.matched_level2_categories:
            if not item.category.strip():
                continue
            queries.append(
                ExpandedQuery(
                    item.category,
                    max(0.62, min(item.weight, 0.92)),
                    (f"AI 二级标签理解：{item.category}",),
                )
            )
        return queries

    def _smart_keyword(
        self,
        keyword: str,
        expanded_queries: list[ExpandedQuery],
    ) -> str:
        terms = [
            keyword,
            *(query.term for query in expand_search_queries(keyword)),
            *(query.term for query in expanded_queries),
        ]
        return " ".join(self._unique([term.strip() for term in terms if term.strip()]))

    def _match_level(self, score: float) -> Literal["S", "A", "B", "C"]:
        if score >= 0.95:
            return "S"
        if score >= 0.8:
            return "A"
        if score >= 0.65:
            return "B"
        return "C"
