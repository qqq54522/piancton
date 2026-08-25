from typing import List, Literal, Optional

from pydantic import Field, model_validator

from app.schemas.base import ApiModel

# D051：查询状态收口为封闭枚举，覆盖“单卖点/多卖点/探索型/待消歧/纯画面/无可靠卖点”。
SearchQueryType = Literal[
    "business_intent_search",
    "multi_business_intent_search",
    "exploratory_business_intent_search",
    "ambiguous_business_intent_search",
    "visual_scene_search",
    "no_reliable_intent_search",
]

SEARCH_QUERY_TYPES: frozenset[str] = frozenset(
    (
        "business_intent_search",
        "multi_business_intent_search",
        "exploratory_business_intent_search",
        "ambiguous_business_intent_search",
        "visual_scene_search",
        "no_reliable_intent_search",
    )
)

SearchSystemRouteType = Literal[
    "single_system",
    "multi_system",
    "ambiguous_system",
    "visual_scene",
    "no_reliable_system",
]


class SearchSystemCandidate(ApiModel):
    code: Literal[
        "sync_school",
        "sync_exam",
        "sync_cultivation",
        "sync_planning",
        "sync_self_study",
        "sync_companion",
    ]
    relation: Literal["primary", "related"]
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchSystemRouting(ApiModel):
    original_query: str
    route_type: SearchSystemRouteType
    candidate_systems: List[SearchSystemCandidate] = Field(default_factory=list)
    excluded_systems: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_route_shape(self):
        candidates = self.candidate_systems
        if self.route_type in {"visual_scene", "no_reliable_system"}:
            if candidates:
                raise ValueError("纯画面或无可靠体系时不得返回体系候选")
            return self
        if not candidates:
            raise ValueError("业务体系路由必须至少返回一个候选体系")
        primary_count = sum(item.relation == "primary" for item in candidates)
        if primary_count != 1:
            raise ValueError("体系候选必须且只能包含一个 primary")
        if self.route_type == "single_system" and len(candidates) != 1:
            raise ValueError("单体系路由只能返回一个候选")
        limit = 3 if self.route_type == "multi_system" else 2
        if len(candidates) > limit:
            raise ValueError("体系候选数量超出渐进式加载上限")
        return self


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


class AssetSearchPhraseSuggestion(ApiModel):
    phrases: List[str] = Field(min_length=2, max_length=5)


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


class SearchProofPointMatch(ApiModel):
    code: str
    concept_code: str
    name: str
    reason: str
    weight: float = Field(ge=0, le=1)
    evidence_terms: List[str] = Field(default_factory=list, max_length=3)


class SearchEvidencePointMatch(ApiModel):
    code: str
    proof_point_code: str
    concept_code: str
    name: str
    reason: str
    weight: float = Field(ge=0, le=1)


class SearchUnderstanding(ApiModel):
    original_query: str
    normalized_query: str
    search_intent: str
    query_type: SearchQueryType
    expanded_terms: List[ExpandedSearchTerm] = Field(default_factory=list)
    matched_business_concepts: List[SearchConceptMatch] = Field(default_factory=list)
    matched_proof_points: List[SearchProofPointMatch] = Field(default_factory=list)
    matched_evidence_points: List[SearchEvidencePointMatch] = Field(default_factory=list)
    excluded_concepts: List[str] = Field(default_factory=list)
    search_strategy: str = ""


class SearchProofPointUnderstanding(ApiModel):
    original_query: str
    matched_proof_points: List[SearchProofPointMatch] = Field(default_factory=list)
    matched_evidence_points: List[SearchEvidencePointMatch] = Field(default_factory=list)
    search_strategy: str = ""


class SearchCandidateReviewDecision(ApiModel):
    image_id: str
    decision: Literal["keep", "demote", "exclude"]
    confidence: float = Field(ge=0, le=1)
    reason: str


class SearchCandidateReviewResult(ApiModel):
    decisions: List[SearchCandidateReviewDecision] = Field(default_factory=list)
    review_strategy: str = ""


class SearchResultRecommendationReason(ApiModel):
    image_id: str = Field(min_length=1, max_length=36)
    reason: str = Field(min_length=1, max_length=500)


class SearchResultRecommendationReasonResult(ApiModel):
    reasons: List[SearchResultRecommendationReason] = Field(default_factory=list)
    generation_strategy: str = ""


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
