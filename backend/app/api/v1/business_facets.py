from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.models.user import User
from app.schemas.business_facets import (
    BusinessFacetCatalogRead,
    EvidencePointFacetRead,
    ProofPointFacetRead,
)

router = APIRouter(prefix="/business-facets", tags=["business-facets"])


@router.get("", response_model=BusinessFacetCatalogRead)
def get_business_facets(_: User = Depends(get_current_user)):
    proofs = load_proof_point_catalog()
    evidence = load_evidence_point_catalog()
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
        ],
        evidence_points=[
            EvidencePointFacetRead(
                code=item.code,
                name=item.name,
                proof_point_code=item.proof_point_code,
                system_code=item.system_code,
                concept_code=item.concept_code,
                source_ref=item.source_ref,
            )
            for item in evidence.points
        ],
    )
