from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from app.schemas.base import ApiModel


class ConceptSystemLinkInput(ApiModel):
    system_tag_id: str
    role: Literal["core", "support", "evidence", "related"] = "core"
    weight: float = Field(default=1.0, ge=0, le=2)
    reason: Optional[str] = Field(default=None, max_length=1000)


class ConceptSystemLinkRead(ConceptSystemLinkInput):
    system_name: str
    status: str


class ConceptSearchPhraseCreate(ApiModel):
    phrase: str = Field(min_length=1, max_length=300)
    phrase_type: Literal[
        "official", "alias", "pain", "outcome", "scenario", "colloquial", "typo"
    ] = "alias"
    origin: Literal["source_document", "manual", "ai", "search_feedback", "migrated"] = "manual"
    review_status: Literal["pending", "accepted", "rejected"] = "accepted"
    weight: float = Field(default=1.0, ge=0, le=2)
    source_ref: Optional[str] = Field(default=None, max_length=300)


class ConceptSearchPhraseRead(ConceptSearchPhraseCreate):
    id: str
    created_at: datetime


class ConceptSearchPhraseUpdate(ApiModel):
    phrase: Optional[str] = Field(default=None, min_length=1, max_length=300)
    phrase_type: Optional[
        Literal["official", "alias", "pain", "outcome", "scenario", "colloquial", "typo"]
    ] = None
    review_status: Optional[Literal["pending", "accepted", "rejected"]] = None
    weight: Optional[float] = Field(default=None, ge=0, le=2)
    source_ref: Optional[str] = Field(default=None, max_length=300)


class BusinessConceptCreate(ApiModel):
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=150)
    concept_type: str = Field(default="business_term", min_length=1, max_length=50)
    definition: Optional[str] = Field(default=None, max_length=5000)
    recommendation_text: Optional[str] = Field(default=None, max_length=5000)
    system_links: List[ConceptSystemLinkInput] = Field(default_factory=list)


class BusinessConceptUpdate(ApiModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    concept_type: Optional[str] = Field(default=None, min_length=1, max_length=50)
    definition: Optional[str] = Field(default=None, max_length=5000)
    recommendation_text: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[Literal["draft", "active", "deprecated", "merged"]] = None
    replaced_by_concept_id: Optional[str] = None
    system_links: Optional[List[ConceptSystemLinkInput]] = None


class BusinessConceptRead(ApiModel):
    id: str
    code: str
    name: str
    concept_type: str
    definition: Optional[str] = None
    recommendation_text: Optional[str] = None
    status: str
    version: int
    replaced_by_concept_id: Optional[str] = None
    system_links: List[ConceptSystemLinkRead] = Field(default_factory=list)
    search_phrases: List[ConceptSearchPhraseRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ConceptRelationCreate(ApiModel):
    target_concept_id: str
    relation_type: Literal[
        "broader_than", "narrower_than", "supports", "similar_to",
        "distinguishes_from", "conflicts_with",
    ]
    reason: Optional[str] = Field(default=None, max_length=2000)


class ConceptRelationRead(ConceptRelationCreate):
    id: str
    source_concept_id: str
    status: str
