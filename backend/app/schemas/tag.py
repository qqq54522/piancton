from typing import Optional

from app.schemas.base import ApiModel


class TagRead(ApiModel):
    id: str
    code: Optional[str] = None
    name: str
    color: str
    parent_id: Optional[str] = None
    parent_name: Optional[str] = None
    is_secondary: bool = False
    node_type: str = "custom"
    assignable: bool = True
    status: str = "active"
    taxonomy_version: Optional[str] = None
    sort_order: int = 0
    image_count: int = 0
