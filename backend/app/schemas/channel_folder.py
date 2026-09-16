from pydantic import Field

from app.schemas.base import ApiModel


class FolderRead(ApiModel):
    id: str
    name: str
    parent_id: str | None = None


class ChannelRead(ApiModel):
    name: str
    folders: list[FolderRead]


class ChannelCreate(ApiModel):
    name: str = Field(min_length=1, max_length=100)


class FolderCreate(ApiModel):
    channel: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=80)
    parent_id: str | None = None


class FolderRename(ApiModel):
    name: str = Field(min_length=1, max_length=80)


class FolderTreeCopy(ApiModel):
    source_channel: str = Field(min_length=1, max_length=100)
    target_channel: str = Field(min_length=1, max_length=100)
    source_folder_id: str | None = None
    target_parent_id: str | None = None


class FolderTreeCopyResult(ApiModel):
    created: int
    skipped: int


class PlacementBatch(ApiModel):
    channel: str = Field(min_length=1, max_length=100)
    image_ids: list[str] = Field(min_length=1, max_length=100)
    folder_id: str | None = None


class PlacementResult(ApiModel):
    assigned: int
