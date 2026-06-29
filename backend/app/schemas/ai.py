from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.base import ApiModel


class ProviderStatus(ApiModel):
    provider: str
    configured: bool
    model_name: str = ""


class ConfidenceTag(ApiModel):
    tag: str
    confidence: float = Field(ge=0, le=1)
    dimension: Optional[str] = None
    reason: Optional[str] = None


class SecondaryLabel(ApiModel):
    label_code: Optional[str] = None
    system: str
    label: str
    confidence: float = Field(ge=0, le=1)
    evidence_level: Literal["A", "B", "C"]
    role: Literal["primary", "secondary"]
    reason: str


class ImageSemanticProfile(ApiModel):
    visual_facts: List[str] = Field(default_factory=list)
    business_intent: str = ""
    search_phrases: List[str] = Field(default_factory=list)
    exclusion_boundaries: List[str] = Field(default_factory=list)


class ImageAnalysisResult(ApiModel):
    image_type: Literal["function", "scene_emotion", "scene_functional"]
    image_summary: str
    semantic_profile: ImageSemanticProfile = Field(default_factory=ImageSemanticProfile)
    content_tags: List[ConfidenceTag] = Field(default_factory=list)
    secondary_labels: List[SecondaryLabel] = Field(default_factory=list)
    recommended_search_words: List[str] = Field(default_factory=list)
    negative_tags: List[str] = Field(default_factory=list)


class SearchIntentRequest(ApiModel):
    keyword: str = Field(min_length=1, max_length=200)


class ExpandedSearchTag(ApiModel):
    tag: str
    relation: Literal["exact", "strong", "medium", "weak"]
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchCategoryMatch(ApiModel):
    category: str
    relation: Literal["direct", "related", "fallback"]
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchUnderstanding(ApiModel):
    original_query: str
    normalized_query: str
    search_intent: str
    query_type: str
    expanded_level1_tags: List[ExpandedSearchTag] = Field(default_factory=list)
    matched_level2_categories: List[SearchCategoryMatch] = Field(default_factory=list)
    exclude_tags: List[str] = Field(default_factory=list)
    search_strategy: str = ""


class SellingPointRequest(ApiModel):
    copy_text: str = Field(min_length=1, max_length=10000, alias="copy")


class SellingPoint(ApiModel):
    point_key: str
    point_name: str
    weight: float = Field(ge=0, le=1)


class SellingPointSystemMatch(ApiModel):
    system_key: str
    system_name: str
    points: List[SellingPoint]


class SellingPointMatchResult(ApiModel):
    matched: List[SellingPointSystemMatch] = Field(default_factory=list)
    expand_keywords: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0, ge=0, le=1)
