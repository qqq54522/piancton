from typing import Literal, Optional
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Request,
    Response,
    UploadFile,
    status,
)

from app.api.dependencies import (
    get_ai_service,
    get_asset_relation_service,
    get_asset_service,
    get_audit_service,
    get_current_user,
    get_db_session_factory,
    get_image_analysis_service,
    require_write_role,
)
from app.models.user import User
from app.schemas.asset import (
    AssetBusinessClassificationUpdate,
    AssetConceptBatchReview,
    AssetConceptConfirmation,
    AssetConceptReview,
    AssetGroupBundleExportRequest,
    AssetGroupRead,
    AssetSearchPhraseCreate,
    AssetSearchPhraseReview,
    AssetSourceLinkCreate,
    AssetSourceLinkUpdate,
)
from app.services.ai_service import AiService
from app.services.analysis_tasks import run_image_analysis_task
from app.services.asset_relation_service import AssetRelationService
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.services.image_analysis_service import ImageAnalysisService

router = APIRouter(prefix="/asset-groups", tags=["asset-groups"])


@router.get("", response_model=list[AssetGroupRead])
def list_asset_groups(
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
):
    groups = service.list()
    if user.role in {"designer", "admin"}:
        return [service.get(group.id, include_source_links=True) for group in groups]
    return groups


@router.get("/{group_id}", response_model=AssetGroupRead)
def get_asset_group(
    group_id: str,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
):
    return service.get(group_id, include_source_links=user.role in {"designer", "admin"})


@router.get("/{group_id}/export")
def export_asset_group(
    group_id: str,
    _: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
):
    filename, payload = service.export_bundle(group_id)
    fallback = "asset-bundle.zip"
    encoded = quote(filename)
    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'
            )
        },
    )


@router.post("/export")
def export_asset_groups(
    payload: AssetGroupBundleExportRequest,
    user: User = Depends(get_current_user),
    service: AssetService = Depends(get_asset_service),
):
    filename, payload_bytes = service.export_bundles(
        payload.group_ids,
        include_source_links=user.role in {"designer", "admin"},
    )
    encoded = quote(filename)
    return Response(
        content=payload_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded}'
            )
        },
    )


@router.post(
    "/{group_id}/images",
    response_model=AssetGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def add_asset_variant(
    group_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    asset_role: Literal["derivative", "alternative", "revision"] = Form(alias="assetRole"),
    channel: Optional[str] = Form(default=None),
    auto_analyze: bool = Form(default=True, alias="autoAnalyze"),
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    analysis: ImageAnalysisService = Depends(get_image_analysis_service),
    ai: AiService = Depends(get_ai_service),
    session_factory=Depends(get_db_session_factory),
):
    original_name = file.filename or "image"
    group = service.add_variant(
        group_id,
        file.file,
        original_name,
        title or original_name.rsplit(".", 1)[0],
        asset_role,
        channel,
        user.username,
    )
    image_id = max(group.images, key=lambda item: item.version_no).id
    # A derivative is only a size/channel adaptation of the same visual. It
    # inherits group semantics and must never create a competing AI analysis.
    if asset_role != "derivative":
        _queue_analysis(
            image_id,
            auto_analyze=auto_analyze,
            background_tasks=background_tasks,
            analysis=analysis,
            ai=ai,
            session_factory=session_factory,
        )
    return group


@router.post(
    "/{group_id}/primary-image",
    response_model=AssetGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def replace_asset_primary(
    group_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    channel: Optional[str] = Form(default=None),
    auto_analyze: bool = Form(default=True, alias="autoAnalyze"),
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    analysis: ImageAnalysisService = Depends(get_image_analysis_service),
    ai: AiService = Depends(get_ai_service),
    session_factory=Depends(get_db_session_factory),
):
    original_name = file.filename or "image"
    group = service.replace_primary(
        group_id,
        file.file,
        original_name,
        title or original_name.rsplit(".", 1)[0],
        channel,
        user.username,
    )
    if group.primary_image_id:
        _queue_analysis(
            group.primary_image_id,
            auto_analyze=auto_analyze,
            background_tasks=background_tasks,
            analysis=analysis,
            ai=ai,
            session_factory=session_factory,
        )
    return group

@router.delete("/{group_id}/images/{image_id}", response_model=AssetGroupRead)
def delete_asset_variant(
    group_id: str,
    image_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    audit: AuditService = Depends(get_audit_service),
):
    group = service.delete_variant(group_id, image_id)
    audit.record(
        actor_user_id=user.id,
        action="asset.variant.trash",
        target_type="image",
        target_id=image_id,
        details={"assetGroupId": group_id},
        request_id=request.state.request_id,
    )
    return group


@router.post("/{group_id}/concept-links", response_model=AssetGroupRead)
def confirm_asset_concept(
    group_id: str,
    payload: AssetConceptConfirmation,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.confirm(group_id, payload)


@router.patch("/{group_id}/business-classification", response_model=AssetGroupRead)
def update_asset_business_classification(
    group_id: str,
    payload: AssetBusinessClassificationUpdate,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.update_business_classification(group_id, payload)


@router.patch("/{group_id}/concept-links/{link_id}", response_model=AssetGroupRead)
def review_asset_concept_suggestion(
    group_id: str,
    link_id: str,
    payload: AssetConceptReview,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.review_suggestion(group_id, link_id, payload)


@router.post("/{group_id}/concept-links/review-batch", response_model=AssetGroupRead)
def review_asset_concept_suggestions(
    group_id: str,
    payload: AssetConceptBatchReview,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.review_suggestions(group_id, payload)


@router.post("/{group_id}/search-phrases", response_model=AssetGroupRead)
def add_asset_search_phrase(
    group_id: str,
    payload: AssetSearchPhraseCreate,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.add_phrase(group_id, payload)


@router.patch("/{group_id}/search-phrases/{phrase_id}", response_model=AssetGroupRead)
def review_asset_search_phrase(
    group_id: str,
    phrase_id: str,
    payload: AssetSearchPhraseReview,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.review_phrase(group_id, phrase_id, payload)


@router.delete("/{group_id}/search-phrases/{phrase_id}", response_model=AssetGroupRead)
def remove_asset_search_phrase(
    group_id: str,
    phrase_id: str,
    _: User = Depends(require_write_role),
    service: AssetRelationService = Depends(get_asset_relation_service),
):
    return service.remove_phrase(group_id, phrase_id)


@router.post("/{group_id}/source-links", response_model=AssetGroupRead)
def add_asset_source_link(
    group_id: str,
    payload: AssetSourceLinkCreate,
    request: Request,
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    audit: AuditService = Depends(get_audit_service),
):
    group = service.add_source_link(group_id, payload, user.username)
    created = group.source_links[-1] if group.source_links else None
    audit.record(
        actor_user_id=user.id,
        action="asset.source_link.create",
        target_type="asset_group",
        target_id=group_id,
        details={
            "linkId": created.id if created else None,
            "linkType": payload.link_type,
            "label": payload.label,
        },
        request_id=request.state.request_id,
    )
    return group


@router.patch("/{group_id}/source-links/{link_id}", response_model=AssetGroupRead)
def update_asset_source_link(
    group_id: str,
    link_id: str,
    payload: AssetSourceLinkUpdate,
    request: Request,
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    audit: AuditService = Depends(get_audit_service),
):
    group = service.update_source_link(group_id, link_id, payload)
    audit.record(
        actor_user_id=user.id,
        action="asset.source_link.update",
        target_type="asset_source_link",
        target_id=link_id,
        details={"assetGroupId": group_id},
        request_id=request.state.request_id,
    )
    return group


@router.delete("/{group_id}/source-links/{link_id}", response_model=AssetGroupRead)
def delete_asset_source_link(
    group_id: str,
    link_id: str,
    request: Request,
    user: User = Depends(require_write_role),
    service: AssetService = Depends(get_asset_service),
    audit: AuditService = Depends(get_audit_service),
):
    group = service.delete_source_link(group_id, link_id)
    audit.record(
        actor_user_id=user.id,
        action="asset.source_link.delete",
        target_type="asset_source_link",
        target_id=link_id,
        details={"assetGroupId": group_id},
        request_id=request.state.request_id,
    )
    return group


def _queue_analysis(
    image_id: str,
    *,
    auto_analyze: bool,
    background_tasks: BackgroundTasks,
    analysis: ImageAnalysisService,
    ai: AiService,
    session_factory,
) -> None:
    provider = getattr(ai, "provider", None)
    if not auto_analyze or provider is None or not provider.configured:
        return
    analysis_run = analysis.create_analysis_run(image_id)
    background_tasks.add_task(
        run_image_analysis_task,
        image_id,
        analysis_run.id,
        provider,
        session_factory,
    )
