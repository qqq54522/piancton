from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.image import SearchResponse


class ExternalApiKeyCreate(ApiModel):
    name: str = Field(min_length=1, max_length=120)
    rate_limit_per_minute: int = Field(default=60, ge=1, le=10000)
    expires_at: Optional[datetime] = None


class ExternalApiKeyRead(ApiModel):
    id: str
    name: str
    key_prefix: str
    secret_preview: str
    status: str
    rate_limit_per_minute: int
    expires_at: Optional[datetime] = None
    created_by: Optional[str] = None
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime


class ExternalApiKeyCreated(ExternalApiKeyRead):
    """The raw secret is returned only by the create operation."""

    secret: str


class ExternalApiSearchRequest(ApiModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=12, ge=1, le=50)
    system_code: Optional[str] = Field(default=None, max_length=100)
    concept_code: Optional[str] = Field(default=None, max_length=100)
    proof_point_code: Optional[str] = Field(default=None, max_length=120)
    evidence_point_code: Optional[str] = Field(default=None, max_length=140)
    channel: Optional[str] = Field(default=None, max_length=100)
    scene: str = Field(default="all", pattern="^(all|scene|nonScene)$")


class ExternalApiSearchResponse(ApiModel):
    data: SearchResponse
    request_id: Optional[str] = None
