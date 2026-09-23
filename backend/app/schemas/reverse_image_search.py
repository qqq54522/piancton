from typing import List, Literal

from pydantic import Field

from app.schemas.base import ApiModel


class ReverseImageMatchRead(ApiModel):
    image_id: str
    title: str
    thumbnail_url: str
    detail_url: str
    score: float = Field(ge=0, le=1)
    match_type: Literal["same_or_transformed", "visually_similar"]


class ReverseImageSearchResponse(ApiModel):
    matches: List[ReverseImageMatchRead] = Field(default_factory=list)
    searched: bool = True
    message: str = ""
