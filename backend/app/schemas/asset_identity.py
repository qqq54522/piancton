from datetime import datetime
from typing import List, Literal, Optional

from app.schemas.base import ApiModel

IdentityCodeType = Literal["asset", "version"]
IdentityCodeStatus = Literal["active", "deleted", "retired"]


class AssetIdentityCodeRead(ApiModel):
    code: str
    code_type: IdentityCodeType
    asset_group_id: Optional[str] = None
    primary_image_id: Optional[str] = None
    image_id: Optional[str] = None
    asset_title: Optional[str] = None
    image_title: Optional[str] = None
    file_name: Optional[str] = None
    asset_role: Optional[str] = None
    version_no: Optional[int] = None
    is_current: Optional[bool] = None
    deleted_at: Optional[datetime] = None
    created_at: datetime
    retired_at: Optional[datetime] = None
    status: IdentityCodeStatus
    detail_path: Optional[str] = None


class AssetIdentityCodeSummary(ApiModel):
    asset_total: int
    version_total: int
    active_total: int
    deleted_total: int
    retired_total: int


class AssetIdentityCodeListResponse(ApiModel):
    items: List[AssetIdentityCodeRead]
    total: int
    page: int
    page_size: int
    summary: AssetIdentityCodeSummary
