from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_ai_service,
    get_search_ai_service,
    require_roles,
    require_write_role,
)
from app.core.errors import AppError
from app.models.user import User
from app.schemas.ai import (
    ProviderStatus,
    SearchIntentRequest,
    SearchUnderstanding,
    SellingPointRequest,
)
from app.services.ai_service import AiService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/provider", response_model=ProviderStatus)
def provider_status(
    _: User = Depends(require_roles("designer", "admin")),
    service: AiService = Depends(get_ai_service),
):
    return service.provider_status()


@router.post("/search-intent", response_model=SearchUnderstanding)
def understand_search(
    payload: SearchIntentRequest,
    _: User = Depends(require_write_role),
    service: AiService = Depends(get_search_ai_service),
):
    return service.understand_search(payload.keyword).value


@router.post("/selling-points/match")
def match_selling_points(
    payload: SellingPointRequest,
    _: User = Depends(require_write_role),
):
    _ = payload
    raise AppError(
        "copy_selling_point_matching_retired",
        "文案卖点匹配接口已退役；当前搜索以火山向量命中卖点为准。",
        status_code=410,
    )


@router.post("/images/{image_id}/analyze")
def analyze_image(
    image_id: str,
    _: User = Depends(require_write_role),
):
    _ = image_id
    raise AppError(
        "image_content_analysis_retired",
        "图片语义分析已退役；当前请以人工选择的卖点、渠道和场景/功能属性为准。",
        status_code=410,
    )
