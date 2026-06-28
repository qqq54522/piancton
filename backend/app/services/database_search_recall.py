from __future__ import annotations

from app.domain.search_query_expansion import ExpandedQuery
from app.repositories.image_repository import ImageRepository
from app.services.query_expansion_service import unique
from app.services.search_models import SearchHit


class DatabaseSearchRecallService:
    def __init__(self, repo: ImageRepository):
        self.repo = repo

    def search_queries(
        self,
        queries: list[ExpandedQuery],
        *,
        limit: int,
    ) -> list[SearchHit]:
        hits_by_id: dict[str, SearchHit] = {}
        for query in queries:
            for image in self.repo.search(query.term, limit):
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
                    reasons=tuple(unique([*existing.reasons, *query.reasons])),
                )
        return list(hits_by_id.values())
