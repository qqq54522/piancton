from __future__ import annotations

from app.repositories.image_repository import ImageRepository
from app.services.embedding_index import cosine_similarity, load_vector
from app.services.search_models import SearchHit
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
            query_vector = self.embedding_client.embed([query])[0]
            rows = self.repo.list_embeddings(model_name=self.embedding_client.model_name)
            scored = []
            for row in rows:
                similarity = cosine_similarity(query_vector, load_vector(row.vector_json))
                if similarity <= 0:
                    continue
                scored.append((row.image_id, max(0.0, min((similarity + 1) / 2, 1.0))))
        except (IndexError, ValueError, TypeError, SemanticSearchClientError):
            return []
        scored.sort(key=lambda item: item[1], reverse=True)
        image_ids = [image_id for image_id, _score in scored[:limit]]
        score_by_id = dict(scored[:limit])
        return [
            SearchHit(
                image=image,
                score=score_by_id.get(image.id, 0.65),
                reasons=("Embedding 语义召回",),
            )
            for image in self.repo.get_many_by_ids(image_ids)
        ]
