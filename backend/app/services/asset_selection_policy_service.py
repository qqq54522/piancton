from __future__ import annotations

from app.domain.asset_text_relevance import (
    AssetSelectionEvidence,
    asset_selection_text,
    best_proof_asset_match,
    best_text_match,
    contains_any,
    policy_evidence_terms,
    query_contexts,
)
from app.domain.search_policy import SearchPolicyCatalog, load_search_policy
from app.schemas.ai import SearchUnderstanding
from app.services.asset_route_ordering import order_routed_assets
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.search_models import ConceptMatch, SearchHit


class AssetSelectionPolicyService:
    """Filter concrete images inside a reviewed selling-point route."""

    def __init__(self, search_policy: SearchPolicyCatalog | None = None):
        self.search_policy = search_policy or load_search_policy()
        self.semantic_profile = ImageSemanticProfileService()

    def evidence(
        self,
        hit: SearchHit,
        keyword: str,
        understanding: SearchUnderstanding | None,
        concept_codes: set[str] | None = None,
    ) -> AssetSelectionEvidence:
        contexts = query_contexts(keyword, understanding)
        group = hit.image.asset_group
        phrases = [
            (item.phrase, item.weight)
            for item in (group.search_phrases if group else [])
            if item.review_status == "accepted"
        ]
        phrase_score, phrase = best_text_match(contexts, phrases)
        raw_query_phrase_score, _ = best_text_match([keyword], phrases)
        profile = self.semantic_profile.profile_from_image(hit.image)
        auxiliary_values = [
            (hit.image.title, 1.0),
            (group.title, 1.0) if group else ("", 0.0),
            (hit.image.image_summary or "", 0.85),
            *((value, 0.8) for value in (profile.visual_facts if profile else [])),
            *((value, 0.8) for value in (profile.scenes if profile else [])),
        ]
        auxiliary_score, auxiliary = best_text_match(contexts, auxiliary_values)
        raw_query_auxiliary_score, _ = best_text_match([keyword], auxiliary_values)
        rules = self.search_policy.asset_selection
        active_codes = concept_codes or set()
        proof_policy_terms = policy_evidence_terms(
            keyword,
            active_codes,
            self.search_policy.asset_evidence_requirements,
        )
        proof = best_proof_asset_match(
            understanding,
            active_codes,
            phrases,
            auxiliary_values,
            query_phrase_score=raw_query_phrase_score,
            phrase_threshold=rules.accepted_phrase_match_threshold,
            auxiliary_threshold=rules.auxiliary_match_threshold,
            policy_evidence_terms=proof_policy_terms,
        )
        matched_proof_codes = {
            item.code for item in (understanding.matched_proof_points if understanding else [])
        }
        matched_evidence_codes = {
            item.code
            for item in (understanding.matched_evidence_points if understanding else [])
        }
        facet_matched = bool(
            group
            and (
                group.primary_evidence_point_code in matched_evidence_codes
                or (
                    not matched_evidence_codes
                    and group.primary_proof_point_code in matched_proof_codes
                )
            )
        )
        facet_mismatch = bool(
            group
            and (
                matched_evidence_codes
                and group.primary_evidence_point_code
                and group.primary_evidence_point_code not in matched_evidence_codes
                or (
                    not matched_evidence_codes
                    and matched_proof_codes
                    and group.primary_proof_point_code
                    and group.primary_proof_point_code not in matched_proof_codes
                )
            )
        )
        return AssetSelectionEvidence(
            query_text_score=max(raw_query_phrase_score, raw_query_auxiliary_score),
            phrase_score=phrase_score,
            phrase=phrase,
            phrase_matched=phrase_score >= rules.accepted_phrase_match_threshold,
            auxiliary_score=auxiliary_score,
            auxiliary=auxiliary,
            auxiliary_matched=auxiliary_score >= rules.auxiliary_match_threshold,
            proof_point_code=proof[0],
            proof_point_name=proof[1],
            proof_point_confidence=proof[2],
            proof_asset_score=max(proof[3], 1.0 if facet_matched else 0.0),
            proof_asset_matched=proof[4] or facet_matched,
            business_facet_matched=facet_matched,
            business_facet_mismatch=facet_mismatch,
        )

    def allows(
        self,
        hit: SearchHit,
        accepted_links,
        keyword: str,
        expressed_concept_ids: set[str],
        evidence: AssetSelectionEvidence,
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
