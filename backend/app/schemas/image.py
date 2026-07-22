from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.ai import SearchUnderstanding
from app.schemas.asset import AssetImageRead
from app.schemas.base import ApiModel


class ImageTitleUpdate(ApiModel):
    title: str = Field(min_length=1, max_length=255)


class ImageTitleResolution(ApiModel):
    requested_title: str
    resolved_title: str
    changed: bool


class SemanticProfileRead(ApiModel):
    schema_version: Literal[3] = 3
    visual_facts: List[str] = Field(default_factory=list)
    scenes: List[str] = Field(default_factory=list)
    asset_search_phrases: List[str] = Field(default_factory=list)


class AnalysisRunRead(ApiModel):
    id: str
    task: str
    status: Literal["queued", "running", "succeeded", "failed"]
    taxonomy_version: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    created_at: datetime


class ImageRead(ApiModel):
    id: str
    title: str
    file_name: str
    content_url: str
    thumbnail_url: str
    download_url: str
    media_type: str
    size_bytes: int
    uploader: str
    download_count: int
    created_at: datetime
    deleted_at: Optional[datetime] = None
    asset_group_id: Optional[str] = None
    asset_role: str = "primary"
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    channel: Optional[str] = None
    style_label: Optional[str] = None
    is_scene_image: Optional[bool] = None
    version_no: int = 1
    is_current: bool = True
    variant_count: int = 1


class ImageDetailRead(ImageRead):
    image_summary: Optional[str] = None
    semantic_profile: Optional[SemanticProfileRead] = None
    related_images: List[ImageRead] = Field(default_factory=list)
    analysis_runs: List[AnalysisRunRead] = Field(default_factory=list)


class ImageListResponse(ApiModel):
    items: List[ImageRead]
    next_cursor: Optional[str] = None
    has_more: bool


class SearchRequest(ApiModel):
    keyword: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=12, ge=1, le=50)
    system_code: Optional[str] = Field(default=None, max_length=100)
    concept_code: Optional[str] = Field(default=None, max_length=100)
    proof_point_code: Optional[str] = Field(default=None, max_length=120)
    evidence_point_code: Optional[str] = Field(default=None, max_length=140)


class SearchResultConceptMatch(ApiModel):
    concept_code: str
    concept_name: str
    relation_role: Literal["expresses", "supports", "visual_related"]


class ScoredImage(ApiModel):
    image: ImageRead
    match_level: Literal["S", "A", "B", "C"]
    final_score: float
    match_reasons: List[str]
    matched_content_terms: List[str]
    matched_business_concepts: List[str]
    asset_group_id: Optional[str] = None
    asset_title: Optional[str] = None
    available_variants: List[AssetImageRead] = Field(default_factory=list)
    expressed_concepts: List[str] = Field(default_factory=list)
    supported_concepts: List[str] = Field(default_factory=list)
    matched_query_concepts: List[SearchResultConceptMatch] = Field(default_factory=list)
    primary_proof_point_code: Optional[str] = None
    primary_proof_point_name: Optional[str] = None
    primary_evidence_point_code: Optional[str] = None
    primary_evidence_point_name: Optional[str] = None


class SearchBranchStatusRead(ApiModel):
    source: str
    status: Literal["ok", "skipped", "timed_out", "failed"]
    duration_ms: int = 0
    result_count: int = 0
    cache_hit: bool = False
    detail: Optional[str] = None


class SearchDiagnosticsRead(ApiModel):
    total_duration_ms: int = 0
    timed_out: bool = False
    reranker_used: bool = False
    cache_hit: bool = False
    degraded_sources: List[str] = Field(default_factory=list)
    branches: List[SearchBranchStatusRead] = Field(default_factory=list)


class SearchResponse(ApiModel):
    results: List[ScoredImage]
    has_more: bool = False
    search_mode: Literal["fuzzy", "meilisearch"] = "fuzzy"
    fallback: bool = False
    fallback_reason: Optional[str] = None
    search_log_id: Optional[str] = None
    search_understanding: Optional[SearchUnderstanding] = None
    search_diagnostics: Optional[SearchDiagnosticsRead] = None
    match_summary: str
