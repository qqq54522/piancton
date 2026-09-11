from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiModel

AssetAgentMessageRole = Literal["user", "assistant", "system"]


class AssetAgentChatRequest(ApiModel):
    message: str = Field(min_length=1, max_length=4000)
    image_ids: list[str] = Field(default_factory=list, max_length=10)
    asset_group_ids: list[str] = Field(default_factory=list, max_length=10)
    conversation_id: str | None = Field(default=None, max_length=80)


class AssetAgentImageContext(ApiModel):
    image_id: str
    asset_group_id: str | None = None
    title: str = Field(min_length=1, max_length=255)
    image_url: str | None = Field(default=None, max_length=1000)


class AssetAgentMessageRead(ApiModel):
    id: str
    role: AssetAgentMessageRole
    content: str
    used_model: bool | None = None
    created_at: datetime


class AssetAgentSessionRead(ApiModel):
    id: str
    title: str
    messages: list[AssetAgentMessageRead] = Field(default_factory=list)
    context_images: list[AssetAgentImageContext] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class AssetAgentSessionListResponse(ApiModel):
    sessions: list[AssetAgentSessionRead] = Field(default_factory=list)


class AssetAgentSessionCreateRequest(ApiModel):
    title: str | None = Field(default=None, max_length=120)
    context_images: list[AssetAgentImageContext] = Field(default_factory=list, max_length=8)


class AssetAgentSessionContextUpdateRequest(ApiModel):
    context_images: list[AssetAgentImageContext] = Field(default_factory=list, max_length=8)


class AssetAgentContextCard(ApiModel):
    kind: Literal["image", "asset_group", "concept"]
    id: str
    title: str
    subtitle: str | None = None
    facts: list[str] = Field(default_factory=list)


class AssetAgentChatResponse(ApiModel):
    answer: str
    conversation_id: str | None = None
    session: AssetAgentSessionRead | None = None
    suggested_questions: list[str] = Field(default_factory=list)
    context_cards: list[AssetAgentContextCard] = Field(default_factory=list)
    used_model: bool = False
    provider_attempts: list[dict] = Field(default_factory=list)


class AssetAgentModelResponse(ApiModel):
    answer: str = Field(min_length=1, max_length=8000)
    suggested_questions: list[str] = Field(default_factory=list, max_length=6)
