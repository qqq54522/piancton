from __future__ import annotations

from app.domain.asset_text_relevance import (
    AssetSelectionEvidence,
    asset_selection_text,
    contains_any,
)
from app.domain.search_policy import SearchPolicyCatalog, load_search_policy
from app.schemas.ai import SearchUnderstanding
from app.services.asset_route_ordering import order_routed_assets
from app.services.asset_selection_evidence_service import AssetSelectionEvidenceService
from app.services.search_models import ConceptMatch, SearchHit


class AssetSelectionPolicyService:
    """Filter concrete images inside a reviewed selling-point route."""

    def __init__(self, search_policy: SearchPolicyCatalog | None = None):
        self.search_policy = search_policy or load_search_policy()
        self.evidence_service = AssetSelectionEvidenceService(self.search_policy)

    def evidence(
        self,
        hit: SearchHit,
        keyword: str,
        understanding: SearchUnderstanding | None,
        concept_codes: set[str] | None = None,
    ) -> AssetSelectionEvidence:
        return self.evidence_service.build(hit, keyword, understanding, concept_codes)

    def allows(
        self,
        hit: SearchHit,
        accepted_links,
        keyword: str,
        expressed_concept_ids: set[str],
        evidence: AssetSelectionEvidence,
        *,
        relax_unfaceted_proof: bool = False,
    ) -> bool:
        if evidence.business_facet_mismatch:
            return False
        accepted_codes = {link.concept.code for link in accepted_links}
        asset_text = asset_selection_text(hit)
        requirement_proves_asset = False
        for gate in self.search_policy.asset_specificity_gates:
            if (
                accepted_codes.intersection(gate.concept_codes)
                and contains_any(asset_text, gate.asset_terms)
                and not contains_any(keyword, gate.query_trigger_terms)
            ):
                return False
        for demand in self.search_policy.asset_evidence_requirements:
            if not (
                accepted_codes.intersection(demand.concept_codes)
                and contains_any(keyword, demand.query_trigger_terms)
            ):
                continue
            if not contains_any(asset_text, demand.asset_terms):
                return False
            requirement_proves_asset = True
        if (
            evidence.proof_point_code
            and not evidence.proof_asset_matched
            and not requirement_proves_asset
        ):
            if relax_unfaceted_proof:
                return True
            return False
        if any(link.relation_role == "expresses" for link in accepted_links):
            return True
        supported_ids = {link.concept_id for link in accepted_links}
        rules = self.search_policy.asset_selection
        if not rules.filter_supports_when_expresses_exist:
            return True
        if not supported_ids.intersection(expressed_concept_ids):
            return True
        return evidence.phrase_matched or evidence.auxiliary_matched

    def order(
        self,
        hits: list[SearchHit],
        active_matches: tuple[ConceptMatch, ...],
        understanding: SearchUnderstanding,
        evidence_by_image: dict[str, AssetSelectionEvidence] | None = None,
    ) -> list[SearchHit]:
        return order_routed_assets(
            hits,
            active_matches,
            understanding,
            evidence_by_image or {},
        )
