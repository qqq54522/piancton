from __future__ import annotations

from app.domain.asset_text_relevance import AssetSelectionEvidence, image_rank_key
from app.schemas.ai import SearchUnderstanding
from app.services.search_models import ConceptMatch, SearchHit

MULTI_ROUTE_QUERY_TYPES = {
    "multi_business_intent_search",
    "exploratory_business_intent_search",
}


def order_routed_assets(
    hits: list[SearchHit],
    active_matches: tuple[ConceptMatch, ...],
    understanding: SearchUnderstanding,
    evidence_by_image: dict[str, AssetSelectionEvidence],
) -> list[SearchHit]:
    ranked = sorted(
        hits,
        key=lambda hit: image_rank_key(
            evidence_by_image.get(hit.image.id),
            hit.score or 0.65,
        ),
        reverse=True,
    )
    if understanding.query_type not in MULTI_ROUTE_QUERY_TYPES:
        return ranked
    prioritized = _round_robin_by_concept(ranked, active_matches)
    used_ids = {hit.image.id for hit in prioritized}
    return [
        *prioritized,
        *(hit for hit in ranked if hit.image.id not in used_ids),
    ]


def _round_robin_by_concept(
    ranked: list[SearchHit],
    active_matches: tuple[ConceptMatch, ...],
) -> list[SearchHit]:
    buckets: dict[str, list[SearchHit]] = {
        match.concept_id: [] for match in active_matches
    }
    for hit in ranked:
        for match in active_matches:
            if _hit_has_concept(hit, match.concept_id):
                buckets[match.concept_id].append(hit)
                break

    ordered: list[SearchHit] = []
    used_ids: set[str] = set()
    while True:
        added = False
        for match in active_matches:
            bucket = buckets[match.concept_id]
            while bucket and bucket[0].image.id in used_ids:
                bucket.pop(0)
            if not bucket:
                continue
            hit = bucket.pop(0)
            ordered.append(hit)
            used_ids.add(hit.image.id)
            added = True
        if not added:
            break
    return ordered


def _hit_has_concept(hit: SearchHit, concept_id: str) -> bool:
    group = hit.image.asset_group
    return any(
        link.concept_id == concept_id
        and link.review_status == "accepted"
        and link.relation_role in {"expresses", "supports"}
        for link in (group.concept_links if group else [])
    )
