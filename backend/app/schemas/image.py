from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.ai import SearchUnderstanding
from app.schemas.base import ApiModel
from app.schemas.tag import TagRead


class ImageTitleUpdate(ApiModel):
    title: str = Field(min_length=1, max_length=255)


class ImageTagsUpdate(ApiModel):
    tag_ids: List[str]
    primary_tag_id: Optional[str] = None


class BusinessLabelReviewUpdate(ApiModel):
    review_status: Literal["accepted", "pending", "rejected"]


class ContentTagRead(ApiModel):
    id: str
    tag_name: str
    confidence: float
    dimension: Optional[str] = None


class Level2CategoryRead(ApiModel):
    id: str
    category_name: str
    confidence: float
    reason: Optional[str] = None


class SemanticProfileRead(ApiModel):
    visual_facts: List[str] = Field(default_factory=list)
    business_intent: str = ""
    search_phrases: List[str] = Field(default_factory=list)
    exclusion_boundaries: List[str] = Field(default_factory=list)


class BusinessLabelRead(ApiModel):
    id: str
    label_code: str
    tag_id: str
    tag_name: str
    system_name: Optional[str] = None
    origin: str
    role: str
    review_status: str
    confidence: Optional[float] = None
    evidence_level: Optional[str] = None
    reason: Optional[str] = None


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
    categories: List[str]
    created_at: datetime
    deleted_at: Optional[datetime] = None
    tags: List[TagRead]


class ImageDetailRead(ImageRead):
    image_summary: Optional[str] = None
    semantic_profile: Optional[SemanticProfileRead] = None
    related_images: List[ImageRead] = Field(default_factory=list)
    content_tags: List[ContentTagRead] = Field(default_factory=list)
    level2_categories: List[Level2CategoryRead] = Field(default_factory=list)
    business_labels: List[BusinessLabelRead] = Field(default_factory=list)
    analysis_runs: List[AnalysisRunRead] = Field(default_factory=list)


class ImageListResponse(ApiModel):
    items: List[ImageRead]
    next_cursor: Optional[str] = None
    has_more: bool


class SearchRequest(ApiModel):
    keyword: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=12, ge=1, le=50)
    search_mode: Literal["configured", "precise", "smart"] = "precise"


class ScoredImage(ApiModel):
    image: ImageRead
    match_level: Literal["S", "A", "B", "C"]
    final_score: float
    match_reasons: List[str]
    matched_level1_tags: List[str]
    matched_level2_categories: List[str]


class SearchResponse(ApiModel):
    results: List[ScoredImage]
    has_more: bool = False
    search_mode: Literal["fuzzy", "meilisearch"] = "fuzzy"
    fallback: bool = False
    fallback_reason: Optional[str] = None
    search_log_id: Optional[str] = None
    search_understanding: Optional[SearchUnderstanding] = None
    match_summary: str
