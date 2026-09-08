from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.base import ApiModel


class AssetImageRead(ApiModel):
    id: str
    asset_code: Optional[str] = None
    version_code: Optional[str] = None
    share_path: Optional[str] = None
    title: str
    file_name: str
    thumbnail_url: str
    content_url: str
    download_url: str
    media_type: str
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


class AssetSourceLinkRead(ApiModel):
    id: str
    label: str
    url: str
    link_type: str
    note: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class AssetGroupRead(ApiModel):
    id: str
    asset_code: Optional[str] = None
    share_path: Optional[str] = None
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
    source_links: List[AssetSourceLinkRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AssetGroupBundleExportRequest(ApiModel):
    group_ids: List[str] = Field(min_length=1, max_length=50)


class AssetConceptConfirmation(ApiModel):
    concept_id: str
    relation_role: Literal["expresses", "supports", "visual_related", "excludes"]
    evidence_reason: Optional[str] = Field(default=None, max_length=3000)


class AssetConceptRelationInput(ApiModel):
    concept_id: str
    relation_role: Literal["expresses", "supports"]


class AssetReplaceConceptRelations(ApiModel):
    relations: List[AssetConceptRelationInput] = Field(default_factory=list, max_length=16)


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


class AssetSourceLinkCreate(ApiModel):
    label: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=2048)
    link_type: Literal[
        "figma",
        "design_file",
        "cloud_drive",
        "reference_doc",
        "asset_package",
        "other",
    ] = "figma"
    note: Optional[str] = Field(default=None, max_length=500)


class AssetSourceLinkUpdate(ApiModel):
    label: Optional[str] = Field(default=None, min_length=1, max_length=120)
    url: Optional[str] = Field(default=None, min_length=1, max_length=2048)
    link_type: Optional[
        Literal[
            "figma",
            "design_file",
            "cloud_drive",
            "reference_doc",
            "asset_package",
            "other",
        ]
    ] = None
    note: Optional[str] = Field(default=None, max_length=500)
