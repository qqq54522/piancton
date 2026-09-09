from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.image import SearchResponse
from app.services.asset_identity_service import (
    AssetIdentityService,
    extract_identity_code,
    looks_like_identity_query,
)
from app.services.search_models import SearchHit
from app.services.search_response_builder import SearchResponseBuilder
from app.services.search_scorer import SearchScorer


class IdentitySearchService:
    """Deterministic code/link lookup kept outside semantic search orchestration."""

    def __init__(self, db: Session):
        self.identities = AssetIdentityService(db)
        self.response_builder = SearchResponseBuilder(SearchScorer())

    def search(self, keyword: str, limit: int) -> tuple[bool, SearchResponse | None]:
        if not looks_like_identity_query(keyword):
            return False, None

        code = extract_identity_code(keyword)
        if not code:
            return True, SearchResponse(
                results=[],
                has_more=False,
                search_mode="fuzzy",
                fallback=False,
                match_summary="身份码格式不正确，请检查后重试",
            )

        image = self.identities.find_image(code)
        if not image:
            return True, SearchResponse(
                results=[],
                has_more=False,
                search_mode="fuzzy",
                fallback=False,
                identity_code=code,
                exact_match=True,
                match_summary=f"没有找到身份码“{code}”对应的已发布素材",
            )

        response = self.response_builder.build_response(
            keyword=keyword,
            hits=[
                SearchHit(
                    image=image,
                    score=1.0,
                    reasons=("身份码精确匹配",),
                )
            ],
            search_mode="fuzzy",
            fallback=False,
        )
        response.identity_code = code
        response.exact_match = True
        return True, response
