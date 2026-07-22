from __future__ import annotations

from app.domain.asset_text_relevance import AssetSelectionEvidence, normalize_text
from app.domain.search_policy import SearchPolicyCatalog
from app.schemas.ai import SearchUnderstanding
from app.services.asset_selection_policy_service import AssetSelectionPolicyService
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, ConceptRouteOutcome, SearchHit


class SearchConceptRoutingService:
    """Keeps trusted concept routing separate from global recall fallback."""

    def __init__(self, search_policy: SearchPolicyCatalog | None = None):
        self.asset_selection = AssetSelectionPolicyService(search_policy)

    def route(
        self,
        hits: list[SearchHit],
        concept_matches: list[ConceptMatch],
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
    ) -> ConceptRouteOutcome:
        hits = _drop_query_excluded_hits(hits, understanding)
        active_matches = _active_concept_matches(concept_matches, understanding)
        if not active_matches:
            return ConceptRouteOutcome(hits=hits)
        matched_ids = {item.concept_id for item in active_matches}
        reviewed: list[tuple[SearchHit, list]] = []
        expressed_concept_ids: set[str] = set()
        for hit in hits:
            links = hit.image.asset_group.concept_links if hit.image.asset_group else []
            if _is_excluded(links, matched_ids):
                continue
            accepted = [
                link
                for link in links
                if link.concept_id in matched_ids
                and link.review_status == "accepted"
                and link.relation_role in {"expresses", "supports"}
            ]
            if not accepted:
                continue
            reviewed.append((hit, accepted))
            expressed_concept_ids.update(
                link.concept_id for link in accepted if link.relation_role == "expresses"
            )
        routed: list[SearchHit] = []
        evidence_by_image: dict[str, AssetSelectionEvidence] = {}
        for hit, accepted in reviewed:
            evidence = self.asset_selection.evidence(
                hit, keyword, understanding, {link.concept.code for link in accepted}
            )
            if not self.asset_selection.allows(
                hit,
                accepted,
                keyword,
                expressed_concept_ids,
                evidence,
            ):
                continue
            evidence_by_image[hit.image.id] = evidence
            routed.append(
                _score_routed_hit(
                    hit,
                    accepted,
                    evidence,
                    expressed_concept_ids,
                )
            )
        # D056: once a query has trusted selling-point routes, external/title
        # candidates cannot replace missing reviewed business relationships.
        # An empty route is a real inventory gap and must stay an empty result.
        return ConceptRouteOutcome(
            hits=self.asset_selection.order(
                routed,
                active_matches,
                understanding,
                evidence_by_image,
            ),
            active_matches=active_matches,
        )


MULTI_ROUTE_QUERY_TYPES = {
    "multi_business_intent_search",
    "exploratory_business_intent_search",
}


def _drop_query_excluded_hits(
    hits: list[SearchHit],
    understanding: SearchUnderstanding | None,
) -> list[SearchHit]:
    """Remove assets that primarily express a selling point the query rejected."""
    if understanding is None or not understanding.excluded_concepts:
        return hits
    excluded_keys = {_normalize_concept_name(item) for item in understanding.excluded_concepts}
    kept: list[SearchHit] = []
    for hit in hits:
        links = hit.image.asset_group.concept_links if hit.image.asset_group else []
        expressed = any(
            link.review_status == "accepted"
            and link.relation_role == "expresses"
            and (
                _normalize_concept_name(link.concept.name) in excluded_keys
                or _normalize_concept_name(link.concept.code) in excluded_keys
            )
            for link in links
        )
        if not expressed:
            kept.append(hit)
    return kept


def _active_concept_matches(
    concept_matches: list[ConceptMatch],
    understanding: SearchUnderstanding | None,
) -> tuple[ConceptMatch, ...]:
    if understanding is None:
        return ()
    # D080: 探索型理解本身就是“候选卖点集合”的裁决。即使模型把候选标为
    # related/低权重（表达不确定），结果仍必须封闭在候选卖点的已确认
    # 关系内合并召回，不允许退回全库融合让待审核关系或标题巧合混入。
    exploratory = understanding.query_type == "exploratory_business_intent_search"
    if exploratory:
        trusted = list(understanding.matched_business_concepts)
    else:
        trusted = [
            item
            for item in understanding.matched_business_concepts
            if item.relation == "direct" and item.weight >= 0.85
        ]
    if not trusted:
        return ()
    if len(trusted) > 1 and understanding.query_type not in MULTI_ROUTE_QUERY_TYPES:
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


def _is_excluded(links, matched_ids: set[str]) -> bool:
    return any(
        link.concept_id in matched_ids
        and link.review_status == "accepted"
        and link.relation_role == "excludes"
        for link in links
    )


def _score_routed_hit(
    hit: SearchHit,
    accepted,
    evidence: AssetSelectionEvidence,
    expressed_concept_ids: set[str],
) -> SearchHit:
    base_score = hit.score if hit.score is not None else 0.65
    best_link = max(accepted, key=_concept_link_rank)
    origin_bonus = 0.005 if best_link.origin in {"manual", "migrated"} else 0.0
    relation_base = 0.84 if best_link.relation_role == "expresses" else 0.78
    phrase_bonus = evidence.phrase_score * 0.14 if evidence.phrase_matched else 0.0
    auxiliary_bonus = evidence.auxiliary_score * 0.035 if evidence.auxiliary_matched else 0.0
    proof_bonus = evidence.proof_asset_score * 0.06 if evidence.proof_asset_matched else 0.0
    score = relation_base + phrase_bonus + auxiliary_bonus + proof_bonus + origin_bonus
    score += min(1.0, base_score) * 0.015
    relation_name = "主要表达" if best_link.relation_role == "expresses" else "可以支持"
    reasons = [*hit.reasons, f"进入卖点主通道：{relation_name}"]
    if evidence.phrase_matched and evidence.phrase:
        reasons.append(f"卖点内素材独有话术命中：{evidence.phrase}")
    elif evidence.auxiliary_matched and evidence.auxiliary:
        reasons.append(f"图片标题或画面内容辅助匹配：{evidence.auxiliary}")
    if evidence.proof_asset_matched and evidence.proof_point_name:
        reasons.append(
            f"证明点匹配：{evidence.proof_point_name}（{evidence.proof_asset_score:.0%}）"
        )
    if best_link.relation_role == "supports" and best_link.concept_id not in expressed_concept_ids:
        reasons.append("当前卖点暂无主要表达素材，保留可以支持素材")
    return SearchHit(
        image=hit.image,
        score=min(1.0, score),
        reasons=tuple(unique(reasons)),
    )


def _concept_link_rank(link) -> tuple[int, int]:
    return (
        2 if link.relation_role == "expresses" else 1,
        1 if link.origin in {"manual", "migrated"} else 0,
    )


def _normalize_concept_name(value: str) -> str:
    return normalize_text(value.rsplit(">", 1)[-1])
