from __future__ import annotations

from app.domain.asset_text_relevance import AssetSelectionEvidence, normalize_text
from app.schemas.ai import SearchUnderstanding
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, SearchHit

MULTI_ROUTE_QUERY_TYPES = {
    "multi_business_intent_search",
    "exploratory_business_intent_search",
}


def drop_query_excluded_hits(
    hits: list[SearchHit],
    understanding: SearchUnderstanding | None,
) -> list[SearchHit]:
    if understanding is None or not understanding.excluded_concepts:
        return hits
    excluded = {_normalize_concept_name(item) for item in understanding.excluded_concepts}
    return [hit for hit in hits if not _hit_expresses_excluded(hit, excluded)]


def active_concept_matches(
    concept_matches: list[ConceptMatch],
    understanding: SearchUnderstanding | None,
) -> tuple[ConceptMatch, ...]:
    if understanding is None:
        return ()
    exploratory = understanding.query_type == "exploratory_business_intent_search"
    trusted = (
        list(understanding.matched_business_concepts)
        if exploratory
        else [
            item
            for item in understanding.matched_business_concepts
            if item.relation == "direct" and item.weight >= 0.85
        ]
    )
    if not trusted or (
        len(trusted) > 1 and understanding.query_type not in MULTI_ROUTE_QUERY_TYPES
    ):
        return ()
    trusted_keys = {_normalize_concept_name(item.concept) for item in trusted}
    active = tuple(
        match
        for match in concept_matches
        if (exploratory or match.score >= 0.84)
        and (
            _normalize_concept_name(match.name) in trusted_keys
            or _normalize_concept_name(match.code) in trusted_keys
        )
    )
    return active if understanding.query_type in MULTI_ROUTE_QUERY_TYPES else active[:1]


def is_excluded(links, matched_ids: set[str]) -> bool:
    return any(
        link.concept_id in matched_ids
        and link.review_status == "accepted"
        and link.relation_role == "excludes"
        for link in links
    )


def score_routed_hit(
    hit: SearchHit,
    accepted,
    evidence: AssetSelectionEvidence,
    expressed_concept_ids: set[str],
    *,
    extra_reason: str | None = None,
) -> SearchHit:
    best_link = max(accepted, key=_concept_link_rank)
    score = _routed_score(hit, best_link, evidence)
    reasons = _routed_reasons(
        hit, best_link, evidence, expressed_concept_ids, extra_reason
    )
    return SearchHit(image=hit.image, score=min(1.0, score), reasons=tuple(unique(reasons)))


def has_proof_point_intent(understanding: SearchUnderstanding | None) -> bool:
    return bool(understanding and understanding.matched_proof_points)


def _hit_expresses_excluded(hit: SearchHit, excluded_keys: set[str]) -> bool:
    links = hit.image.asset_group.concept_links if hit.image.asset_group else []
    return any(
        link.review_status == "accepted"
        and link.relation_role == "expresses"
        and (
            _normalize_concept_name(link.concept.name) in excluded_keys
            or _normalize_concept_name(link.concept.code) in excluded_keys
        )
        for link in links
    )


def _routed_score(hit: SearchHit, best_link, evidence: AssetSelectionEvidence) -> float:
    base_score = hit.score if hit.score is not None else 0.65
    return (
        (0.84 if best_link.relation_role == "expresses" else 0.78)
        + (evidence.phrase_score * 0.14 if evidence.phrase_matched else 0.0)
        + (evidence.auxiliary_score * 0.035 if evidence.auxiliary_matched else 0.0)
        + (evidence.proof_asset_score * 0.06 if evidence.proof_asset_matched else 0.0)
        + (0.005 if best_link.origin in {"manual", "migrated"} else 0.0)
        + min(1.0, base_score) * 0.015
    )


def _routed_reasons(
    hit: SearchHit,
    best_link,
    evidence: AssetSelectionEvidence,
    expressed_concept_ids: set[str],
    extra_reason: str | None,
) -> list[str]:
    relation_name = "主要表达" if best_link.relation_role == "expresses" else "可以支持"
    reasons = [*hit.reasons, f"进入卖点主通道：{relation_name}"]
    if evidence.phrase_matched and evidence.phrase:
        reasons.append(f"卖点内素材独有话术命中：{evidence.phrase}")
    elif evidence.auxiliary_matched and evidence.auxiliary:
        reasons.append(f"图片标题或画面内容辅助匹配：{evidence.auxiliary}")
    if evidence.proof_asset_matched and evidence.proof_point_name:
        reasons.append(f"证明点匹配：{evidence.proof_point_name}（{evidence.proof_asset_score:.0%}）")
    if best_link.relation_role == "supports" and best_link.concept_id not in expressed_concept_ids:
        reasons.append("当前卖点暂无主要表达素材，保留可以支持素材")
    if extra_reason:
        reasons.append(extra_reason)
    return reasons


def _concept_link_rank(link) -> tuple[int, int]:
    return (
        2 if link.relation_role == "expresses" else 1,
        1 if link.origin in {"manual", "migrated"} else 0,
    )


def _normalize_concept_name(value: str) -> str:
    return normalize_text(value.rsplit(">", 1)[-1])
