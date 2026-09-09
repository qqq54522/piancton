from datetime import datetime
from typing import List, Optional

from app.schemas.base import ApiModel


class ImageIdentityCodeRead(ApiModel):
    code: str
    image_id: str
    image_title: str
    file_name: str
    channel: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime
    detail_path: str


class ImageIdentityCodeSummary(ApiModel):
    image_total: int


class ImageIdentityCodeListResponse(ApiModel):
    items: List[ImageIdentityCodeRead]
    total: int
    page: int
    page_size: int
    summary: ImageIdentityCodeSummary
