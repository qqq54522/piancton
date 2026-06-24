from typing import Optional

from pydantic import Field

from app.schemas.base import ApiModel


class TagCreate(ApiModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = "#6B7280"
    parent_id: Optional[str] = None
    is_secondary: bool = False
    assignable: bool = True


class TagUpdate(ApiModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_secondary: Optional[bool] = None
    assignable: Optional[bool] = None
    status: Optional[str] = Field(default=None, pattern="^(active|inactive)$")


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


class TagDeleteImpact(ApiModel):
    tag_id: str
    tag_name: str
    subtree_tag_count: int
    direct_child_count: int
    affected_image_count: int
