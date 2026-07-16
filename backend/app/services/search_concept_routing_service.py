from __future__ import annotations

from difflib import SequenceMatcher

from app.schemas.ai import SearchUnderstanding
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, ConceptRouteOutcome, SearchHit


class SearchConceptRoutingService:
    """Keeps trusted concept routing separate from global recall fallback."""

    def route(
        self,
        hits: list[SearchHit],
        concept_matches: list[ConceptMatch],
        *,
        keyword: str,
        understanding: SearchUnderstanding | None,
    ) -> ConceptRouteOutcome:
        active_matches = _active_concept_matches(concept_matches, understanding)
        if not active_matches:
            return ConceptRouteOutcome(hits=hits)
        matched_ids = {item.concept_id for item in active_matches}
        routed: list[SearchHit] = []
        fallback: list[SearchHit] = []
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
                fallback.append(_cap_fallback_hit(hit))
                continue
            routed.append(_score_routed_hit(hit, accepted, keyword))
        if routed:
            return ConceptRouteOutcome(
                hits=_sort_hits(routed),
                active_matches=active_matches,
            )
        reason = "卖点主通道暂无已确认素材，启用全局图片话术与画面语义兜底"
        return ConceptRouteOutcome(
            hits=_sort_hits(
                [
                    SearchHit(
                        image=hit.image,
                        score=hit.score,
                        reasons=tuple(unique([*hit.reasons, reason])),
                    )
                    for hit in fallback
                ]
            ),
            active_matches=active_matches,
            used_fallback=True,
        )


def _active_concept_matches(
    concept_matches: list[ConceptMatch],
    understanding: SearchUnderstanding | None,
) -> tuple[ConceptMatch, ...]:
    if understanding is None:
        return ()
    trusted = [
        item
        for item in understanding.matched_business_concepts
        if item.relation == "direct" and item.weight >= 0.85
    ]
    if not trusted:
        return ()
    if len(trusted) > 1 and understanding.query_type != "multi_business_intent_search":
        return ()
    trusted_keys = {_normalize_concept_name(item.concept) for item in trusted}
    active = tuple(
        match
        for match in concept_matches
        if match.score >= 0.84
        and (
            _normalize_concept_name(match.name) in trusted_keys
            or _normalize_concept_name(match.code) in trusted_keys
        )
    )
    return active if understanding.query_type == "multi_business_intent_search" else active[:1]


def _is_excluded(links, matched_ids: set[str]) -> bool:
    return any(
        link.concept_id in matched_ids
        and link.review_status == "accepted"
        and link.relation_role == "excludes"
        for link in links
    )


def _cap_fallback_hit(hit: SearchHit) -> SearchHit:
    base_score = hit.score if hit.score is not None else 0.65
    return SearchHit(
        image=hit.image,
        score=min(base_score, 0.82),
        reasons=hit.reasons,
    )


def _score_routed_hit(hit: SearchHit, accepted, keyword: str) -> SearchHit:
    base_score = hit.score if hit.score is not None else 0.65
    phrase_score, phrase = _asset_phrase_match(hit, keyword)
    best_link = max(accepted, key=_concept_link_rank)
    relation_bonus = 0.025 if best_link.relation_role == "expresses" else 0.015
    origin_bonus = 0.005 if best_link.origin in {"manual", "migrated"} else 0.0
    score = (
        0.86 + phrase_score * 0.09 + relation_bonus + origin_bonus
        + min(1.0, base_score) * 0.015
        if phrase_score > 0
        else 0.84 + relation_bonus + origin_bonus + min(1.0, base_score) * 0.04
    )
    relation_name = "主要表达" if best_link.relation_role == "expresses" else "可以支持"
    reasons = [*hit.reasons, f"进入卖点主通道：{relation_name}"]
    if phrase:
        reasons.append(f"卖点内素材独有话术命中：{phrase}")
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


def _asset_phrase_match(hit: SearchHit, keyword: str) -> tuple[float, str | None]:
    group = hit.image.asset_group
    if group is None:
        return 0.0, None
    query = _normalize_text(keyword)
    best_score = 0.0
    best_phrase: str | None = None
    for item in group.search_phrases:
        if item.review_status != "accepted":
            continue
        phrase = _normalize_text(item.phrase)
        if not query or not phrase:
            continue
        if query == phrase:
            score = 1.0
        elif phrase in query:
            score = 0.96
        elif query in phrase:
            score = 0.92
        else:
            similarity = SequenceMatcher(None, query, phrase).ratio()
            score = similarity if similarity >= 0.58 else 0.0
        score = min(score, max(0.0, min(1.0, item.weight)))
        if score > best_score:
            best_score = score
            best_phrase = item.phrase
    return best_score, best_phrase


def _sort_hits(hits: list[SearchHit]) -> list[SearchHit]:
    return sorted(
        hits,
        key=lambda hit: hit.score if hit.score is not None else 0.65,
        reverse=True,
    )


def _normalize_concept_name(value: str) -> str:
    return _normalize_text(value.rsplit(">", 1)[-1])


def _normalize_text(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)
