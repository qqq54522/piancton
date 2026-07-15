from __future__ import annotations

from app.repositories.image_repository import ImageRepository
from app.services.embedding_index import cosine_similarity, load_vector
from app.services.search_models import ExternalSearchCandidate, SearchHit
from app.services.semantic_search_clients import EmbeddingClient, SemanticSearchClientError


class EmbeddingRecallService:
    def __init__(
        self,
        repo: ImageRepository,
        embedding_client: EmbeddingClient | None = None,
    ):
        self.repo = repo
        self.embedding_client = embedding_client

    def search(self, keyword: str, limit: int) -> list[SearchHit]:
        if not self.embedding_client or not self.embedding_client.configured:
            return []
        query = keyword.strip()
        if not query:
            return []
        try:
            query_vector = self.query_vector(query)
        except (IndexError, ValueError, TypeError, SemanticSearchClientError):
            return []
        return self.hydrate(self.score_candidates(query_vector, limit))

    @property
    def configured(self) -> bool:
        return bool(self.embedding_client and self.embedding_client.configured)

    @property
    def model_name(self) -> str:
        if not self.embedding_client:
            return ""
        return self.embedding_client.model_name

    def query_vector(self, keyword: str) -> list[float]:
        if not self.embedding_client or not self.embedding_client.configured:
            raise SemanticSearchClientError("Embedding API 尚未配置完整")
        return self.embedding_client.embed([keyword.strip()])[0]

    def score_candidates(
        self,
        query_vector: list[float],
        limit: int,
    ) -> list[ExternalSearchCandidate]:
        rows = self.repo.list_embeddings(model_name=self.model_name)
        scored: list[tuple[str, float]] = []
        for row in rows:
            similarity = cosine_similarity(query_vector, load_vector(row.vector_json))
            if similarity <= 0:
                continue
            scored.append(
                (row.image_id, max(0.0, min((similarity + 1) / 2, 1.0)))
            )
        scored.sort(key=lambda item: item[1], reverse=True)
        return [
            ExternalSearchCandidate(
                image_id=image_id,
                score=score,
                reasons=("Embedding 语义召回",),
            )
            for image_id, score in scored[:limit]
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
