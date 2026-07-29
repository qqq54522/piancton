from __future__ import annotations

from app.domain.asset_text_relevance import (
    AssetSelectionEvidence,
    best_proof_asset_match,
    best_text_match,
    policy_evidence_terms,
    query_contexts,
)
from app.domain.search_policy import SearchPolicyCatalog
from app.schemas.ai import SearchUnderstanding
from app.services.image_semantic_profile_service import ImageSemanticProfileService
from app.services.search_models import SearchHit


class AssetSelectionEvidenceService:
    """Build asset-specific evidence for a reviewed selling-point route."""

    def __init__(self, search_policy: SearchPolicyCatalog):
        self.search_policy = search_policy
        self.semantic_profile = ImageSemanticProfileService()

    def build(
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
        auxiliary_values = self._auxiliary_values(hit)
        auxiliary_score, auxiliary = best_text_match(contexts, auxiliary_values)
        raw_query_auxiliary_score, _ = best_text_match([keyword], auxiliary_values)
        rules = self.search_policy.asset_selection
        active_codes = concept_codes or set()
        proof = best_proof_asset_match(
            understanding,
            active_codes,
            phrases,
            auxiliary_values,
            query_phrase_score=raw_query_phrase_score,
            phrase_threshold=rules.accepted_phrase_match_threshold,
            auxiliary_threshold=rules.auxiliary_match_threshold,
            policy_evidence_terms=policy_evidence_terms(
                keyword,
                active_codes,
                self.search_policy.asset_evidence_requirements,
            ),
        )
        facet_matched, facet_mismatch = self._facet_state(group, understanding)
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

    def _auxiliary_values(self, hit: SearchHit) -> list[tuple[str, float]]:
        group = hit.image.asset_group
        profile = self.semantic_profile.profile_from_image(hit.image)
        return [
            (hit.image.title, 1.0),
            (group.title, 1.0) if group else ("", 0.0),
            (hit.image.image_summary or "", 0.85),
            *((value, 0.8) for value in (profile.visual_facts if profile else [])),
            *((value, 0.8) for value in (profile.scenes if profile else [])),
        ]

    def _facet_state(
        self,
        group,
        understanding: SearchUnderstanding | None,
    ) -> tuple[bool, bool]:
        if not group or not understanding:
            return False, False
        matched_proof_codes = {item.code for item in understanding.matched_proof_points}
        matched_evidence_codes = {
            item.code for item in understanding.matched_evidence_points
        }
        matched = (
            group.primary_evidence_point_code in matched_evidence_codes
            or (
                not matched_evidence_codes
                and group.primary_proof_point_code in matched_proof_codes
            )
        )
        mismatch = (
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
        return bool(matched), bool(mismatch)
