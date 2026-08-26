from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from app.api.dependencies import (
    get_ai_service,
    get_audit_service,
    get_current_user,
    get_db_session_factory,
    get_image_analysis_service,
    get_image_lifecycle_service,
    get_image_service,
    get_search_log_service,
    get_search_service,
    get_usage_analytics_service,
    require_roles,
    require_write_role,
)
from app.models.user import User
from app.schemas.image import (
    ImageDetailRead,
    ImageListResponse,
    ImageRead,
    ImageTitleResolution,
    ImageTitleUpdate,
    SearchRequest,
    SearchResponse,
)
from app.services.ai_service import AiService
from app.services.analysis_tasks import run_image_analysis_task
from app.services.audit_service import AuditService
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_lifecycle_service import ImageLifecycleService
from app.services.image_service import ImageService
from app.services.search_log_service import SearchLogService
from app.services.search_service import SearchService
from app.services.usage_analytics_service import UsageAnalyticsService

router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=ImageListResponse)
def list_images(
    keyword: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = Query(default=12, ge=1, le=50),
    sort_by: str = Query(
        default="createdAt",
        alias="sortBy",
        pattern="^(createdAt|downloadCount)$",
    ),
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    return service.list_images(keyword, cursor, limit, sort_by)


@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    payload: SearchRequest,
    request: Request,
    user: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
    analytics: SearchLogService = Depends(get_search_log_service),
):
    identity_handled, identity_response = service.identity_search.search(
        payload.keyword,
        payload.limit,
    )
    if identity_handled:
        assert identity_response is not None
        identity_response.search_log_id = analytics.record_search(
            actor_user_id=user.id,
            keyword=payload.keyword,
            response=identity_response,
            request_id=request.state.request_id,
        )
        return identity_response
    response = await service.search_async(
        payload.keyword,
        payload.limit,
        payload.system_code,
        payload.concept_code,
        payload.proof_point_code,
        payload.evidence_point_code,
    )
    response.search_log_id = analytics.record_search(
        actor_user_id=user.id,
        keyword=payload.keyword,
        response=response,
        request_id=request.state.request_id,
    )
    return response


@router.post("/upload", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
def upload_image(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    expected_search_words: str = Form(default="", alias="expectedSearchWords"),
    channel: Optional[str] = Form(default=None, max_length=100),
    style_label: Optional[str] = Form(default=None, alias="styleLabel", max_length=100),
    is_scene_image: Optional[bool] = Form(default=None, alias="isSceneImage"),
    auto_analyze: bool = Form(default=True, alias="autoAnalyze"),
    user: User = Depends(require_write_role),
    service: ImageService = Depends(get_image_service),
    analysis: ImageAnalysisService = Depends(get_image_analysis_service),
    ai: AiService = Depends(get_ai_service),
    audit: AuditService = Depends(get_audit_service),
    session_factory=Depends(get_db_session_factory),
):
    original_name = file.filename or "image"
    image = service.upload(
        file.file,
        original_name,
        title or original_name.rsplit(".", 1)[0],
        user.username,
        [item for item in expected_search_words.split("\n") if item.strip()],
        _required_channel(channel),
        style_label,
        is_scene_image,
    )
    audit.record(
        actor_user_id=user.id,
        action="image.upload",
        target_type="image",
        target_id=image.id,
        details={
            "fileName": image.file_name,
            "sizeBytes": image.size_bytes,
            "channel": image.channel,
            "styleLabel": image.style_label,
            "isSceneImage": image.is_scene_image,
        },
        request_id=request.state.request_id,
    )
    provider = getattr(ai, "provider", None)
    if auto_analyze and provider is not None and provider.configured:
        analysis_run = analysis.create_analysis_run(image.id)
        background_tasks.add_task(
            run_image_analysis_task,
            image.id,
            analysis_run.id,
            provider,
            session_factory,
        )
    return image


def _required_channel(value: Optional[str]) -> str:
    channel = (value or "").strip()
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "channel_required", "message": "请先选择使用渠道"},
        )
    return channel


@router.get("/trash", response_model=list[ImageRead])
def list_deleted_images(
    _: User = Depends(require_roles("designer", "admin")),
    service: ImageLifecycleService = Depends(get_image_lifecycle_service),
):
    return service.list_deleted()


@router.get("/title-resolution", response_model=ImageTitleResolution)
def resolve_image_title(
    title: str = Query(min_length=1, max_length=255),
    _: User = Depends(require_roles("designer", "admin")),
    service: ImageService = Depends(get_image_service),
):
    """Preview the title the backend will reserve when the image is published."""
    return service.resolve_title(title)


@router.post("/{image_id}/restore", response_model=ImageRead)
def restore_image(
    image_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageLifecycleService = Depends(get_image_lifecycle_service),
    audit: AuditService = Depends(get_audit_service),
):
    image = service.restore(image_id)
    audit.record(
        actor_user_id=user.id,
        action="image.restore",
        target_type="image",
        target_id=image_id,
        request_id=request.state.request_id,
    )
    return image


@router.delete("/{image_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
def purge_image(
    image_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageLifecycleService = Depends(get_image_lifecycle_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.purge(image_id)
    audit.record(
        actor_user_id=user.id,
        action="image.purge",
        target_type="image",
        target_id=image_id,
        request_id=request.state.request_id,
    )


@router.get("/{image_id}/thumbnail")
def get_image_thumbnail(
    image_id: str,
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    path, image = service.thumbnail(image_id)
    media_type = "image/jpeg" if image.thumbnail_storage_key else image.media_type
    return FileResponse(path, media_type=media_type, content_disposition_type="inline")


@router.get("/{image_id}/content")
def get_image_content(
    image_id: str,
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    path, image = service.content(image_id)
    return FileResponse(path, media_type=image.media_type, content_disposition_type="inline")


@router.get("/{image_id}/download")
def download_image(
    image_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
    usage: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    path, image = service.download(image_id)
    background_tasks.add_task(service.increment_download, image_id)
    background_tasks.add_task(
        usage.record_download,
        user_id=user.id,
        image_id=image_id,
        request_id=request.state.request_id,
    )
    return FileResponse(
        path,
        filename=image.file_name,
        media_type=image.media_type,
        background=background_tasks,
    )


@router.get("/{image_id}", response_model=ImageDetailRead)
def get_image_detail(
    image_id: str,
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    return service.get_detail(image_id)


@router.patch("/{image_id}/title", response_model=ImageRead)
def update_image_title(
    image_id: str,
    payload: ImageTitleUpdate,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageService = Depends(get_image_service),
    audit: AuditService = Depends(get_audit_service),
):
    image = service.update_title(image_id, payload.title)
    audit.record(
        actor_user_id=user.id,
        action="image.update_title",
        target_type="image",
        target_id=image_id,
        request_id=request.state.request_id,
    )
    return image


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageLifecycleService = Depends(get_image_lifecycle_service),
    audit: AuditService = Depends(get_audit_service),
):
    service.delete(image_id)
    audit.record(
        actor_user_id=user.id,
        action="image.trash",
        target_type="image",
        target_id=image_id,
        request_id=request.state.request_id,
    )
