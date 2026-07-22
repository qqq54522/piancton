from typing import List

from pydantic import Field

from app.schemas.base import ApiModel


class ProofPointFacetRead(ApiModel):
    code: str
    name: str
    system_code: str
    concept_code: str


class EvidencePointFacetRead(ApiModel):
    code: str
    name: str
    proof_point_code: str
    system_code: str
    concept_code: str
    source_ref: str


class BusinessFacetCatalogRead(ApiModel):
    version: str
    proof_points: List[ProofPointFacetRead] = Field(default_factory=list)
    evidence_points: List[EvidencePointFacetRead] = Field(default_factory=list)
