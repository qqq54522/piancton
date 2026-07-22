from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.base import ApiModel


class AssetImageRead(ApiModel):
    id: str
    title: str
    file_name: str
    thumbnail_url: str
    content_url: str
    download_url: str
    asset_role: str
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    channel: Optional[str] = None
    version_no: int
    is_current: bool


class AssetConceptLinkRead(ApiModel):
    id: str
    concept_id: str
    concept_code: str
    concept_name: str
    relation_role: str
    origin: str
    review_status: str
    confidence: Optional[float] = None
    evidence_reason: Optional[str] = None
    source_ref: Optional[str] = None


class AssetSearchPhraseRead(ApiModel):
    id: str
    phrase: str
    origin: str
    review_status: str
    weight: float


class AssetGroupRead(ApiModel):
    id: str
    title: str
    primary_image_id: Optional[str] = None
    approval_status: str
    publish_status: str
    style_label: Optional[str] = None
    is_scene_image: Optional[bool] = None
    primary_proof_point_code: Optional[str] = None
    primary_evidence_point_code: Optional[str] = None
    created_by: str
    images: List[AssetImageRead] = Field(default_factory=list)
    concept_links: List[AssetConceptLinkRead] = Field(default_factory=list)
    search_phrases: List[AssetSearchPhraseRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AssetConceptConfirmation(ApiModel):
    concept_id: str
    relation_role: Literal["expresses", "supports", "visual_related", "excludes"]
    evidence_reason: Optional[str] = Field(default=None, max_length=3000)


class AssetBusinessClassificationUpdate(ApiModel):
    concept_id: Optional[str] = None
    proof_point_code: Optional[str] = Field(default=None, max_length=120)
    evidence_point_code: Optional[str] = Field(default=None, max_length=140)


class AssetConceptReview(ApiModel):
    review_status: Literal["accepted", "rejected"]
    relation_role: Optional[Literal["expresses", "supports", "visual_related", "excludes"]] = None


class AssetConceptBatchReview(ApiModel):
    link_ids: List[str] = Field(min_length=1, max_length=100)
    review_status: Literal["accepted", "rejected"]


class AssetSearchPhraseCreate(ApiModel):
    phrase: str = Field(min_length=1, max_length=300)
    weight: float = Field(default=1.0, ge=0, le=2)


class AssetSearchPhraseReview(ApiModel):
    review_status: Literal["accepted", "rejected"]
