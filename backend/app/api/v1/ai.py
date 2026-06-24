from fastapi import APIRouter, Depends

from app.api.dependencies import (
    get_ai_service,
    get_image_analysis_service,
    get_image_service,
    require_roles,
    require_write_role,
)
from app.models.user import User
from app.schemas.ai import (
    ImageAnalysisResult,
    ProviderStatus,
    SearchIntentRequest,
    SearchUnderstanding,
    SellingPointMatchResult,
    SellingPointRequest,
)
from app.services.ai_service import AiService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_service import ImageService

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
    service: AiService = Depends(get_ai_service),
):
    return service.understand_search(payload.keyword)


@router.post("/selling-points/match", response_model=SellingPointMatchResult)
def match_selling_points(
    payload: SellingPointRequest,
    _: User = Depends(require_write_role),
    service: AiService = Depends(get_ai_service),
):
    return service.match_selling_points(payload.copy_text)


@router.post("/images/{image_id}/analyze", response_model=ImageAnalysisResult)
def analyze_image(
    image_id: str,
    _: User = Depends(require_write_role),
    service: AiService = Depends(get_ai_service),
    images: ImageService = Depends(get_image_service),
    analysis: ImageAnalysisService = Depends(get_image_analysis_service),
):
    path, _image = images.content(image_id)
    result = service.analyze_image(path)
    analysis.save_ai_analysis(image_id, result)
    return result
