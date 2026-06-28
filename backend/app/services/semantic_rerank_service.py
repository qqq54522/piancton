from __future__ import annotations

from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.query_expansion_service import unique
from app.services.search_models import SearchHit
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

    def rerank_hits(
        self,
        keyword: str,
        hits: list[SearchHit],
        limit: int,
    ) -> list[SearchHit]:
        if not self.reranker or not self.reranker.configured or len(hits) <= 1:
            return hits
        candidate_limit = min(max(limit, self.reranker_top_n), len(hits))
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
        reranked.extend(hits[candidate_limit:])
        return reranked
