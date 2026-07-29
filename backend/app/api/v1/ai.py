from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import (
    get_ai_service,
    get_asset_phrase_suggestion_service,
    get_image_analysis_service,
    get_image_service,
    get_search_ai_service,
    require_roles,
    require_write_role,
)
from app.core.errors import AppError
from app.models.user import User
from app.schemas.ai import (
    AssetSearchPhraseSuggestion,
    ImageAnalysisResult,
    ProviderStatus,
    SearchIntentRequest,
    SearchUnderstanding,
    SellingPointMatchResult,
    SellingPointRequest,
)
from app.services.ai_service import AiService
from app.services.asset_phrase_suggestion_service import AssetPhraseSuggestionService
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
    service: AiService = Depends(get_search_ai_service),
):
    return service.understand_search(payload.keyword)


@router.post("/selling-points/match", response_model=SellingPointMatchResult)
def match_selling_points(
    payload: SellingPointRequest,
    _: User = Depends(require_write_role),
    service: AiService = Depends(get_search_ai_service),
):
    return service.match_selling_points(payload.copy_text)


@router.post(
    "/asset-search-phrases",
    response_model=AssetSearchPhraseSuggestion,
)
def generate_asset_search_phrases(
    file: UploadFile = File(...),
    count: int = Form(default=5, ge=2, le=5),
    title: str = Form(default="", max_length=200),
    concept_code: str = Form(default="", alias="conceptCode", max_length=100),
    _: User = Depends(require_write_role),
    service: AssetPhraseSuggestionService = Depends(
        get_asset_phrase_suggestion_service
    ),
):
    return service.generate(
        file.file,
        count=count,
        title=title.strip() or Path(file.filename or "image").stem,
        concept_code=concept_code,
    )


@router.post("/images/{image_id}/analyze", response_model=ImageAnalysisResult)
def analyze_image(
    image_id: str,
    _: User = Depends(require_write_role),
    service: AiService = Depends(get_ai_service),
    images: ImageService = Depends(get_image_service),
    analysis: ImageAnalysisService = Depends(get_image_analysis_service),
):
    path, image = images.content(image_id)
    if image.asset_role == "derivative":
        raise AppError(
            "derivative_analysis_not_required",
            "尺寸延展版本继承主图业务信息，无需重复 AI 分析",
        )
    result = service.analyze_image(path)
    analysis.save_ai_analysis(image_id, result)
    return result
