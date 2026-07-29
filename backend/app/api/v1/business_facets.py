from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.models.user import User
from app.schemas.business_facets import (
    BusinessFacetCatalogRead,
    EvidencePointFacetRead,
    EvidencePointSourcePathNodeRead,
    ProofPointFacetRead,
)

router = APIRouter(prefix="/business-facets", tags=["business-facets"])

BUSINESS_VISIBLE_PROOF_POINT_OVERRIDES = {
    "pp_selfstudy_photo_external_review",
}

BUSINESS_HIDDEN_PROOF_POINT_OVERRIDES = {
    "pp_planning_founder_ai_view",
}


@router.get("", response_model=BusinessFacetCatalogRead)
def get_business_facets(_: User = Depends(get_current_user)):
    proofs = load_proof_point_catalog()
    evidence = load_evidence_point_catalog()
    evidence_backed_proof_codes = {item.proof_point_code for item in evidence.points}
    visible_proof_codes = (
        evidence_backed_proof_codes | BUSINESS_VISIBLE_PROOF_POINT_OVERRIDES
    ) - BUSINESS_HIDDEN_PROOF_POINT_OVERRIDES
    return BusinessFacetCatalogRead(
        version=f"{proofs.version}+{evidence.version}",
        proof_points=[
            ProofPointFacetRead(
                code=item.code,
                name=item.name,
                system_code=item.system_code,
                concept_code=item.concept_code,
            )
            for item in proofs.points
            if item.code in visible_proof_codes
        ],
        evidence_points=[
            EvidencePointFacetRead(
                code=item.code,
                name=item.name,
                proof_point_code=item.proof_point_code,
                system_code=item.system_code,
                concept_code=item.concept_code,
                source_ref=item.source_ref,
                source_paths=[
                    [
                        EvidencePointSourcePathNodeRead(
                            level=node.level,
                            label=node.label,
                        )
                        for node in path
                    ]
                    for path in item.source_paths
                ],
                review_notes=list(item.review_notes),
            )
            for item in evidence.points
            if item.proof_point_code in visible_proof_codes
        ],
    )
