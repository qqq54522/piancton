from __future__ import annotations

from app.domain.search_policy import SearchPolicyCatalog
from app.schemas.ai import SearchUnderstanding
from app.services.asset_selection_policy_service import AssetSelectionPolicyService
from app.services.search_concept_routing_helpers import (
    active_concept_matches,
    drop_query_excluded_hits,
    has_proof_point_intent,
    is_excluded,
    score_routed_hit,
)
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
        hits = drop_query_excluded_hits(hits, understanding)
        active_matches = active_concept_matches(concept_matches, understanding)
        if not active_matches:
            return ConceptRouteOutcome(hits=hits)
        assert understanding is not None
        matched_ids = {item.concept_id for item in active_matches}
        reviewed: list[tuple[SearchHit, list]] = []
        expressed_concept_ids: set[str] = set()
        for hit in hits:
            links = hit.image.asset_group.concept_links if hit.image.asset_group else []
            if is_excluded(links, matched_ids):
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
        evidence_by_image = {}
        broad_inventory_route = _is_vikingdb_selling_point_inventory_route(understanding)
        for hit, accepted in reviewed:
            evidence = self.asset_selection.evidence(
                hit, keyword, understanding, {link.concept.code for link in accepted}
            )
            evidence_by_image[hit.image.id] = evidence
            if not broad_inventory_route and not self.asset_selection.allows(
                hit,
                accepted,
                keyword,
                expressed_concept_ids,
                evidence,
            ):
                continue
            routed.append(
                score_routed_hit(
                    hit,
                    accepted,
                    evidence,
                    expressed_concept_ids,
                )
            )
        if not routed and has_proof_point_intent(understanding):
            for hit, accepted in reviewed:
                evidence = evidence_by_image[hit.image.id]
                if not self.asset_selection.allows(
                    hit,
                    accepted,
                    keyword,
                    expressed_concept_ids,
                    evidence,
                    relax_unfaceted_proof=True,
                ):
                    continue
                routed.append(
                    score_routed_hit(
                        hit,
                        accepted,
                        evidence,
                        expressed_concept_ids,
                        extra_reason="证明点素材字段未覆盖，保留卖点候选进入第四层复核",
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


def _is_vikingdb_selling_point_inventory_route(
    understanding: SearchUnderstanding | None,
) -> bool:
    return bool(
        understanding
        and "VikingDB" in (understanding.search_strategy or "")
        and understanding.matched_business_concepts
    )
