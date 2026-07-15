from __future__ import annotations

import asyncio

from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_models import RerankOutcome, SearchHit
from app.services.semantic_search_clients import RerankerClient, SemanticSearchClientError


class SemanticRerankService:
    def __init__(
        self,
        reranker: RerankerClient | None = None,
        reranker_top_n: int = 50,
        semantic_profile: ImageSemanticProfileService | None = None,
    ):
        self.reranker = reranker
        self.reranker_top_n = reranker_top_n
        self.semantic_profile = semantic_profile or ImageSemanticProfileService()

    @property
    def configured(self) -> bool:
        return bool(self.reranker and self.reranker.configured)

    def rerank_hits(
        self,
        keyword: str,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if not self.reranker or not self.reranker.configured or len(hits) <= 1:
            return hits
        candidate_limit = min(self.reranker_top_n, len(hits))
        candidates = hits[:candidate_limit]
        try:
            results = self.reranker.rerank(
                query=keyword,
                documents=[
                    self.semantic_profile.rerank_document(hit.image) for hit in candidates
                ],
                top_n=candidate_limit,
            )
        except SemanticSearchClientError:
            return hits
        return self._apply_results(candidates, hits, results)

    async def rerank_hits_async(
        self,
        keyword: str,
        hits: list[SearchHit],
    ) -> RerankOutcome:
        if not self.reranker or not self.reranker.configured or len(hits) <= 1:
            return RerankOutcome(hits=hits, used=False)
        candidate_limit = min(self.reranker_top_n, len(hits))
        candidates = hits[:candidate_limit]
        documents = [
            self.semantic_profile.rerank_document(hit.image) for hit in candidates
        ]
        try:
            results = await asyncio.to_thread(
                self.reranker.rerank,
                query=keyword,
                documents=documents,
                top_n=candidate_limit,
            )
        except SemanticSearchClientError as exc:
            return RerankOutcome(hits=hits, used=False, error=str(exc))
        return RerankOutcome(
            hits=self._apply_results(candidates, hits, results),
            used=True,
        )

    def _apply_results(self, candidates, hits, results) -> list[SearchHit]:
        hit_by_index = {index: hit for index, hit in enumerate(candidates)}
        reranked: list[SearchHit] = []
        used_indexes: set[int] = set()
        for result in results:
            hit = hit_by_index.get(result.index)
            if hit is None:
                continue
            used_indexes.add(result.index)
            reranked.append(
                SearchHit(
                    image=hit.image,
                    score=result.score,
                    reasons=tuple(unique([*hit.reasons, "Reranker 语义重排"])),
                )
            )
        reranked.extend(
            hit for index, hit in enumerate(candidates) if index not in used_indexes
        )
        reranked.extend(hits[len(candidates):])
        return reranked
