from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
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
    get_image_tagging_service,
    get_search_service,
    require_roles,
    require_write_role,
)
from app.models.user import User
from app.schemas.image import (
    BusinessLabelReviewUpdate,
    ImageDetailRead,
    ImageListResponse,
    ImageRead,
    ImageTagsUpdate,
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
from app.services.image_tagging_service import ImageTaggingService
from app.services.search_service import SearchService

router = APIRouter(prefix="/images", tags=["images"])


@router.get("", response_model=ImageListResponse)
def list_images(
    keyword: Optional[str] = None,
    tag_ids: Optional[str] = Query(default=None, alias="tagIds"),
    cursor: Optional[str] = None,
    limit: int = Query(default=12, ge=1, le=50),
    sort_by: str = Query(
        default="createdAt",
        alias="sortBy",
        pattern="^(createdAt|downloadCount)$",
    ),
    category: Optional[str] = None,
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    return service.list_images(
        keyword, tag_ids.split(",") if tag_ids else [], cursor, limit, sort_by, category
    )


@router.post("/search", response_model=SearchResponse)
def semantic_search(
    payload: SearchRequest,
    _: User = Depends(get_current_user),
    service: SearchService = Depends(get_search_service),
):
    return service.search(payload.keyword, payload.limit, payload.search_mode)


@router.post("/upload", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
def upload_image(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    tag_ids: str = Form(default="", alias="tagIds"),
    primary_tag_id: str = Form(default="", alias="primaryTagId"),
    categories: str = Form(default=""),
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
        [item for item in tag_ids.split(",") if item],
        primary_tag_id or None,
        [item for item in categories.split(",") if item],
        user.username,
    )
    audit.record(
        actor_user_id=user.id,
        action="image.upload",
        target_type="image",
        target_id=image.id,
        details={"fileName": image.file_name, "sizeBytes": image.size_bytes},
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


@router.get("/trash", response_model=list[ImageRead])
def list_deleted_images(
    _: User = Depends(require_roles("designer", "admin")),
    service: ImageLifecycleService = Depends(get_image_lifecycle_service),
):
    return service.list_deleted()


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
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_user),
    service: ImageService = Depends(get_image_service),
):
    path, image = service.download(image_id)
    background_tasks.add_task(service.increment_download, image_id)
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


@router.patch("/{image_id}/tags", response_model=ImageRead)
def update_image_tags(
    image_id: str,
    payload: ImageTagsUpdate,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageTaggingService = Depends(get_image_tagging_service),
    audit: AuditService = Depends(get_audit_service),
):
    image = service.update_tags(image_id, payload.tag_ids, payload.primary_tag_id)
    audit.record(
        actor_user_id=user.id,
        action="image.update_tags",
        target_type="image",
        target_id=image_id,
        details={"tagIds": payload.tag_ids},
        request_id=request.state.request_id,
    )
    return image


@router.patch(
    "/{image_id}/business-labels/{label_id}",
    response_model=ImageDetailRead,
)
def review_business_label(
    image_id: str,
    label_id: str,
    payload: BusinessLabelReviewUpdate,
    request: Request,
    user: User = Depends(require_write_role),
    service: ImageTaggingService = Depends(get_image_tagging_service),
    audit: AuditService = Depends(get_audit_service),
):
    image = service.review_business_label(
        image_id,
        label_id,
        payload.review_status,
    )
    audit.record(
        actor_user_id=user.id,
        action="image.review_business_label",
        target_type="image",
        target_id=image_id,
        details={"labelId": label_id, "reviewStatus": payload.review_status},
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
