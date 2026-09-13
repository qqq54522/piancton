from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.image import ImageRead


class AssetSaveContext(ApiModel):
    image_id: Optional[str] = Field(default=None, max_length=36)
    source: str = Field(default="library_browse", min_length=1, max_length=80)
    position: Optional[int] = Field(default=None, ge=0, le=10000)
    search_log_id: Optional[str] = Field(default=None, max_length=36)
    keyword: str = Field(default="", max_length=200)


class SavedAssetRead(ApiModel):
    asset_group_id: str
    title: str
    saved_at: datetime
    image: ImageRead


class SavedAssetListResponse(ApiModel):
    items: list[SavedAssetRead] = Field(default_factory=list)
    next_cursor: Optional[str] = None
    has_more: bool = False


class AssetCollectionBoardCreate(ApiModel):
    name: str = Field(min_length=1, max_length=80)


class AssetCollectionBoardUpdate(ApiModel):
    name: str = Field(min_length=1, max_length=80)


class AssetCollectionBoardRead(ApiModel):
    id: str
    name: str
    item_count: int
    created_at: datetime
    updated_at: datetime


class AssetCollectionBoardListResponse(ApiModel):
    items: list[AssetCollectionBoardRead] = Field(default_factory=list)


class AssetCollectionSummary(ApiModel):
    liked_asset_group_ids: list[str] = Field(default_factory=list)
    liked_count: int = 0
    boards: list[AssetCollectionBoardRead] = Field(default_factory=list)


class AssetCollectionMembership(ApiModel):
    asset_group_id: str
    liked: bool
    board_ids: list[str] = Field(default_factory=list)
