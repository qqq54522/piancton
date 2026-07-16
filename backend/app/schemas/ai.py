from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.base import ApiModel


class ProviderStatus(ApiModel):
    provider: str
    configured: bool
    model_name: str = ""


class ConceptSuggestion(ApiModel):
    concept_code: Optional[str] = None
    system_name: str
    concept_name: str
    confidence: float = Field(ge=0, le=1)
    evidence_level: Literal["A", "B", "C"]
    relation_role: Literal["expresses", "supports"]
    reason: str


class ImageSemanticProfile(ApiModel):
    schema_version: Literal[3] = 3
    visual_facts: List[str] = Field(default_factory=list)
    scenes: List[str] = Field(default_factory=list)
    asset_search_phrases: List[str] = Field(default_factory=list)

class ImageAnalysisResult(ApiModel):
    image_summary: str
    semantic_profile: ImageSemanticProfile = Field(default_factory=ImageSemanticProfile)
    concept_suggestions: List[ConceptSuggestion] = Field(default_factory=list)


class SearchIntentRequest(ApiModel):
    keyword: str = Field(min_length=1, max_length=200)


class ExpandedSearchTerm(ApiModel):
    term: str
    relation: Literal["exact", "strong", "medium", "weak"]
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchConceptMatch(ApiModel):
    concept: str
    relation: Literal["direct", "related", "fallback"]
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchUnderstanding(ApiModel):
    original_query: str
    normalized_query: str
    search_intent: str
    query_type: str
    expanded_terms: List[ExpandedSearchTerm] = Field(default_factory=list)
    matched_business_concepts: List[SearchConceptMatch] = Field(default_factory=list)
    excluded_concepts: List[str] = Field(default_factory=list)
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
