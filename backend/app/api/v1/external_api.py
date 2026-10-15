from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_audit_service,
    get_external_api_key_service,
    get_image_service,
    get_search_log_service,
    get_search_service,
    require_admin,
    require_admin_role,
    require_external_api_key,
)
from app.api.storage_response import StorageFileResponse
from app.core.config import get_settings
from app.models.external_api_key import ExternalApiKey
from app.models.user import User
from app.schemas.external_api import (
    ExternalApiKeyCreate,
    ExternalApiKeyCreated,
    ExternalApiKeyRead,
    ExternalApiSearchRequest,
)
from app.schemas.image import SearchResponse
from app.services.audit_service import AuditService
from app.services.external_api_key_service import ExternalApiKeyService
from app.services.image_service import ImageService
from app.services.search_log_service import SearchLogService
from app.services.search_service import SearchService

admin_router = APIRouter(prefix="/admin/api-keys", tags=["external-api-keys"])
public_router = APIRouter(prefix="/public", tags=["external-api"])


@admin_router.get("", response_model=list[ExternalApiKeyRead])
def list_api_keys(
    _: User = Depends(require_admin_role),
    service: ExternalApiKeyService = Depends(get_external_api_key_service),
):
    return service.list()


@admin_router.post("", response_model=ExternalApiKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ExternalApiKeyCreate,
    request: Request,
    actor: User = Depends(require_admin),
    service: ExternalApiKeyService = Depends(get_external_api_key_service),
    audit: AuditService = Depends(get_audit_service),
):
    created = service.create(payload, created_by=actor.id)
    audit.record(
        actor_user_id=actor.id,
        action="external_api_key.create",
        target_type="external_api_key",
        target_id=created.id,
        details={
            "name": created.name,
            "keyPrefix": created.key_prefix,
            "rateLimitPerMinute": created.rate_limit_per_minute,
            "expiresAt": created.expires_at.isoformat() if created.expires_at else None,
        },
        request_id=request.state.request_id,
    )
    return created


@admin_router.post("/{key_id}/revoke", response_model=ExternalApiKeyRead)
def revoke_api_key(
    key_id: str,
    request: Request,
    actor: User = Depends(require_admin),
    service: ExternalApiKeyService = Depends(get_external_api_key_service),
    audit: AuditService = Depends(get_audit_service),
):
    revoked = service.revoke(key_id)
    audit.record(
        actor_user_id=actor.id,
        action="external_api_key.revoke",
        target_type="external_api_key",
        target_id=key_id,
        request_id=request.state.request_id,
    )
    return revoked


@public_router.post("/image-search", response_model=SearchResponse)
async def public_image_search(
    payload: ExternalApiSearchRequest,
    request: Request,
    _: ExternalApiKey = Depends(require_external_api_key),
    service: SearchService = Depends(get_search_service),
    analytics: SearchLogService = Depends(get_search_log_service),
):
    response = await service.search_async(
        payload.query,
        payload.limit,
        payload.system_code,
        payload.concept_code,
        payload.proof_point_code,
        payload.evidence_point_code,
        user_id="",
    )
    if payload.channel or payload.scene != "all":
        response.results = [
            item
            for item in response.results
            if (not payload.channel or item.image.channel == payload.channel)
            and (
                payload.scene == "all"
                or (payload.scene == "scene" and item.image.is_scene_image is True)
                or (payload.scene == "nonScene" and item.image.is_scene_image is False)
            )
        ][: payload.limit]
        response.has_more = False
    response.search_log_id = analytics.record_search(
        actor_user_id=None,
        keyword=payload.query,
        response=response,
        request_id=request.state.request_id,
    )
    response.results = [
        item.model_copy(
            update={
                "image": item.image.model_copy(
                    update={
                        "thumbnail_url": _public_media_url(request, item.image.id, "thumbnail"),
                        "content_url": _public_media_url(request, item.image.id, "content"),
                        "download_url": _public_media_url(request, item.image.id, "download"),
                    }
                )
            }
        )
        for item in response.results
    ]
    return response


@public_router.get("/images/{image_id}/thumbnail")
def public_image_thumbnail(
    image_id: str,
    background_tasks: BackgroundTasks,
    _: ExternalApiKey = Depends(require_external_api_key),
    service: ImageService = Depends(get_image_service),
):
    path, image, media_type = service.thumbnail(image_id)
    _require_published(image, release=lambda: service.storage.release(path))
    return StorageFileResponse(
        path,
        release=service.storage.release,
        media_type=media_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=300"},
        background=background_tasks,
    )


@public_router.get("/images/{image_id}/content")
def public_image_content(
    image_id: str,
    background_tasks: BackgroundTasks,
    _: ExternalApiKey = Depends(require_external_api_key),
    service: ImageService = Depends(get_image_service),
):
    path, image = service.content(image_id)
    _require_published(image, release=lambda: service.storage.release(path))
    return StorageFileResponse(
        path,
        release=service.storage.release,
        media_type=image.media_type,
        content_disposition_type="inline",
        headers={"Cache-Control": "public, max-age=300"},
        background=background_tasks,
    )


@public_router.get("/images/{image_id}/download")
def public_image_download(
    image_id: str,
    background_tasks: BackgroundTasks,
    _: ExternalApiKey = Depends(require_external_api_key),
    service: ImageService = Depends(get_image_service),
):
    path, image = service.download(image_id)
    _require_published(image, release=lambda: service.storage.release(path))
    background_tasks.add_task(service.increment_download, image_id)
    return StorageFileResponse(
        path,
        release=service.storage.release,
        filename=image.file_name,
        media_type=image.media_type,
        background=background_tasks,
    )


def _require_published(image, *, release) -> None:
    if (
        image.deleted_at is not None
        or not image.is_current
        or (image.asset_group is not None and image.asset_group.publish_status != "published")
    ):
        release()
        raise HTTPException(status_code=404, detail="图片不存在")


def _public_media_url(request: Request, image_id: str, kind: str) -> str:
    api_prefix = get_settings().api_prefix.rstrip("/")
    return f"{str(request.base_url).rstrip('/')}{api_prefix}/public/images/{image_id}/{kind}"
