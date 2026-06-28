from __future__ import annotations

from app.domain.search_query_expansion import ExpandedQuery
from app.models.image import Image
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
                match_score = database_match_score(image, query.term)
                score = (
                    match_score
                    if query.score is None
                    else min(match_score, query.score)
                )
                if existing is None:
                    hits_by_id[image.id] = SearchHit(
                        image=image,
                        score=score,
                        reasons=query.reasons,
                    )
                    continue
                scores = [
                    score
                    for score in (existing.score, score)
                    if score is not None
                ]
                hits_by_id[image.id] = SearchHit(
                    image=image,
                    score=max(scores) if scores else None,
                    reasons=tuple(unique([*existing.reasons, *query.reasons])),
                )
        return list(hits_by_id.values())


def database_match_score(image: Image, term: str) -> float:
    needle = term.strip().lower()
    if not needle:
        return 0.65
    title = image.title.lower()
    if needle in title or title in needle:
        return 1.0
    summary = image.image_summary.lower() if image.image_summary else ""
    if summary and (needle in summary or summary in needle):
        return 0.9
    tag_names = [link.tag.name.lower() for link in image.tag_links]
    content_tags = [item.tag_name.lower() for item in image.content_tags]
    if any(needle in name for name in [*tag_names, *content_tags]):
        return 0.8
    category_names = [item.category_name.lower() for item in image.level2_categories]
    business_labels = [
        label
        for label in image.business_labels
        if label.review_status != "rejected"
    ]
    business_terms = [
        label.label_code.lower()
        for label in business_labels
    ]
    business_terms.extend(label.tag.name.lower() for label in business_labels)
    if any(needle in name for name in [*category_names, *business_terms]):
        return 0.86
    return 0.65
