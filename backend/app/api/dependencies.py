from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal, get_db
from app.models.user import User, UserSession
from app.services.announcement_service import AnnouncementService
from app.services.asset_agent_service import AssetAgentService
from app.services.asset_agent_temporary_image_service import (
    AssetAgentTemporaryImageService,
)
from app.services.asset_collection_service import AssetCollectionService
from app.services.asset_identity_admin_service import AssetIdentityAdminService
from app.services.asset_identity_service import AssetIdentityService
from app.services.asset_relation_service import AssetRelationService
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.business_concept_service import BusinessConceptService
from app.services.channel_folder_service import ChannelFolderService
from app.services.home_recommendation_service import HomeRecommendationService
from app.services.image_lifecycle_service import ImageLifecycleService
from app.services.image_service import ImageService
from app.services.search_cache import shared_search_caches
from app.services.search_log_service import SearchLogService
from app.services.search_ops_service import SearchOpsService
from app.services.search_service import SearchService
from app.services.storage_factory import build_storage
from app.services.tag_service import TagService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.user_avatar_service import UserAvatarService
from app.services.user_service import UserService
from app.services.volc_ai_search_client import VolcAiSearchClient
from app.services.volc_ai_search_service import VolcAiSearchService
from app.services.volc_ai_search_sync import VolcAiSearchIndexSync

settings = get_settings()


def get_db_session_factory():
    return SessionLocal


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(
        db,
        settings.session_ttl_hours,
        settings.login_max_attempts,
        settings.login_window_minutes,
        settings.login_block_minutes,
    )


def _build_ai_search_client() -> VolcAiSearchClient:
    return VolcAiSearchClient(
        base_url=settings.ai_search_base_url,
        api_key=settings.ai_search_api_key,
        dataset_id=settings.ai_search_dataset_id,
        application_id=settings.ai_search_application_id,
        search_path=settings.ai_search_search_path,
        chat_search_path=settings.ai_search_chat_path,
        chat_dataset_ids=settings.ai_search_chat_dataset_ids,
        recommend_path=settings.ai_search_recommend_path,
        behavior_dataset_id=settings.ai_search_behavior_dataset_id,
        timeout_seconds=settings.ai_search_timeout_seconds,
    )


def _build_ai_search_image_client() -> VolcAiSearchClient:
    return VolcAiSearchClient(
        base_url=settings.ai_search_base_url,
        api_key=settings.ai_search_api_key,
        dataset_id=settings.ai_search_image_dataset_id,
        search_path=settings.ai_search_image_search_path,
        timeout_seconds=settings.ai_search_timeout_seconds,
    )


def _build_ai_search_chat_client() -> VolcAiSearchClient:
    return VolcAiSearchClient(
        base_url=settings.ai_search_base_url,
        api_key=settings.ai_search_api_key,
        dataset_id=settings.ai_search_dataset_id,
        application_id=settings.ai_search_application_id,
        search_path=settings.ai_search_search_path,
        chat_search_path=settings.ai_search_chat_path,
        chat_dataset_ids=settings.ai_search_chat_dataset_ids,
        recommend_path=settings.ai_search_recommend_path,
        behavior_dataset_id=settings.ai_search_behavior_dataset_id,
        timeout_seconds=settings.ai_search_chat_timeout_seconds,
    )


def _build_ai_search_recommend_client() -> VolcAiSearchClient:
    return VolcAiSearchClient(
        base_url=settings.ai_search_base_url,
        api_key=settings.ai_search_api_key,
        dataset_id=settings.ai_search_dataset_id,
        application_id=settings.ai_search_application_id,
        search_path=settings.ai_search_search_path,
        chat_search_path=settings.ai_search_chat_path,
        chat_dataset_ids=settings.ai_search_chat_dataset_ids,
        recommend_path=settings.ai_search_recommend_path,
        behavior_dataset_id=settings.ai_search_behavior_dataset_id,
        timeout_seconds=settings.ai_search_recommend_timeout_seconds,
    )


def _build_ai_search_home_recommend_client() -> VolcAiSearchClient:
    client = _build_ai_search_recommend_client()
    client.recommend_path = settings.ai_search_home_recommend_path.strip() or client.recommend_path
    return client


def _build_ai_search_index() -> VolcAiSearchIndexSync:
    public_base_url = (
        settings.ai_search_public_base_url or settings.public_base_url or _first_cors_origin()
    )
    return VolcAiSearchIndexSync(
        _build_ai_search_client(),
        enabled=settings.ai_search_enabled and settings.ai_search_sync_enabled,
        public_base_url=public_base_url,
        image_client=_build_ai_search_image_client(),
        image_enabled=(
            settings.ai_search_enabled and settings.ai_search_image_sync_enabled
        ),
        image_storage=build_storage(settings),
    )


def _first_cors_origin() -> str:
    for origin in settings.cors_origin_list:
        if origin.startswith("http://") or origin.startswith("https://"):
            return origin
    return ""


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    return ImageService(
        db,
        build_storage(settings),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.max_long_image_pixels,
        settings.long_image_min_aspect_ratio,
        settings.thumbnail_max_size,
        ai_search_index=_build_ai_search_index(),
        ai_search_client=_build_ai_search_recommend_client(),
        ai_search_recommend_enabled=(
            settings.ai_search_enabled and settings.ai_search_recommend_enabled
        ),
    )


def get_channel_folder_service(db: Session = Depends(get_db)) -> ChannelFolderService:
    return ChannelFolderService(db)


def get_home_recommendation_service(
    db: Session = Depends(get_db),
) -> HomeRecommendationService:
    return HomeRecommendationService(
        db,
        ai_search_client=_build_ai_search_home_recommend_client(),
        enabled=settings.ai_search_enabled and settings.ai_search_recommend_enabled,
    )


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(
        db,
        build_storage(settings),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.max_long_image_pixels,
        settings.long_image_min_aspect_ratio,
        settings.thumbnail_max_size,
        ai_search_index=_build_ai_search_index(),
    )


def get_user_avatar_service(db: Session = Depends(get_db)) -> UserAvatarService:
    return UserAvatarService(db, build_storage(settings, namespace="account-avatars"))


def get_asset_collection_service(
    db: Session = Depends(get_db),
) -> AssetCollectionService:
    return AssetCollectionService(db)


def get_asset_identity_service(db: Session = Depends(get_db)) -> AssetIdentityService:
    return AssetIdentityService(db)


def get_asset_identity_admin_service(
    db: Session = Depends(get_db),
) -> AssetIdentityAdminService:
    return AssetIdentityAdminService(db)


def get_asset_relation_service(db: Session = Depends(get_db)) -> AssetRelationService:
    return AssetRelationService(
        db,
        ai_search_index=_build_ai_search_index(),
    )


def get_business_concept_service(
    db: Session = Depends(get_db),
) -> BusinessConceptService:
    return BusinessConceptService(db)


def get_image_lifecycle_service(db: Session = Depends(get_db)) -> ImageLifecycleService:
    return ImageLifecycleService(
        db,
        build_storage(settings),
        ai_search_index=_build_ai_search_index(),
    )


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(
        db,
        search_backend=settings.search_backend,
        meilisearch_url=settings.meilisearch_url,
        meilisearch_api_key=settings.meilisearch_api_key,
        meilisearch_index=settings.meilisearch_index,
        search_timeout_seconds=settings.search_meilisearch_timeout_seconds,
        ai_service=None,
        embedding_client=None,
        embedding_top_n=settings.embedding_top_n,
        reranker=None,
        reranker_top_n=settings.reranker_top_n,
        total_timeout_seconds=settings.search_total_timeout_seconds,
        meilisearch_timeout_seconds=settings.search_meilisearch_timeout_seconds,
        embedding_timeout_seconds=settings.search_embedding_timeout_seconds,
        understanding_timeout_seconds=settings.search_understanding_timeout_seconds,
        system_routing_timeout_seconds=settings.search_system_routing_timeout_seconds,
        selling_point_timeout_seconds=settings.search_selling_point_timeout_seconds,
        proof_point_timeout_seconds=settings.search_proof_point_timeout_seconds,
        candidate_review_timeout_seconds=settings.search_candidate_review_timeout_seconds,
        candidate_review_limit=settings.search_candidate_review_limit,
        understanding_grace_seconds=settings.search_understanding_grace_seconds,
        understanding_retry_attempts=settings.search_understanding_retry_attempts,
        understanding_retry_backoff_seconds=(settings.search_understanding_retry_backoff_seconds),
        reranker_timeout_seconds=settings.search_reranker_timeout_seconds,
        result_recommendation_timeout_seconds=(
            settings.search_result_recommendation_timeout_seconds
        ),
        result_recommendation_limit=settings.search_result_recommendation_limit,
        candidate_limit=settings.search_candidate_limit,
        cache_ttl_seconds=settings.search_cache_ttl_seconds,
        cache_max_entries=settings.search_cache_max_entries,
        caches=shared_search_caches(
            settings.search_cache_ttl_seconds,
            settings.search_cache_max_entries,
        ),
        vikingdb_knowledge_router=None,
        vikingdb_skill_backup_enabled=False,
        ai_search=VolcAiSearchService(
            db,
            _build_ai_search_client(),
            enabled=settings.ai_search_enabled,
            page_size=settings.ai_search_page_size,
        ),
    )


def get_search_log_service(db: Session = Depends(get_db)) -> SearchLogService:
    return SearchLogService(db)


def get_search_ops_service(db: Session = Depends(get_db)) -> SearchOpsService:
    return SearchOpsService(db)


def get_asset_agent_service(db: Session = Depends(get_db)) -> AssetAgentService:
    return AssetAgentService(
        db,
        ai_search_chat=_build_ai_search_chat_client()
        if settings.ai_search_enabled and settings.ai_search_chat_enabled
        else None,
        ai_search_chat_page_size=settings.ai_search_page_size,
        ai_search_public_base_url=(
            settings.ai_search_public_base_url or settings.public_base_url or _first_cors_origin()
        ),
        temporary_images=get_asset_agent_temporary_image_service(),
        storage=build_storage(settings),
    )


def get_asset_agent_temporary_image_service() -> AssetAgentTemporaryImageService:
    return AssetAgentTemporaryImageService(
        settings.storage_dir / ".agent-temporary",
        public_base_url=(
            settings.ai_search_public_base_url or settings.public_base_url or _first_cors_origin()
        ),
        max_upload_bytes=settings.max_upload_bytes,
        max_image_pixels=settings.max_image_pixels,
        max_long_image_pixels=settings.max_long_image_pixels,
        long_image_min_aspect_ratio=settings.long_image_min_aspect_ratio,
    )


def get_reverse_image_search_service(db: Session = Depends(get_db)):
    from app.services.reverse_image_search_service import ReverseImageSearchService

    return ReverseImageSearchService(
        db,
        client=_build_ai_search_image_client(),
        temporary_images=get_asset_agent_temporary_image_service(),
        enabled=settings.ai_search_enabled,
        page_size=settings.ai_search_page_size,
    )


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


def get_announcement_service(
    db: Session = Depends(get_db),
) -> AnnouncementService:
    return AnnouncementService(db)


def get_usage_analytics_service(
    db: Session = Depends(get_db),
) -> UsageAnalyticsService:
    return UsageAnalyticsService(db)


def get_audit_service(db: Session = Depends(get_db)) -> AuditService:
    return AuditService(db)


def get_current_session(
    token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    service: AuthService = Depends(get_auth_service),
) -> UserSession:
    return service.authenticate(token)


def get_current_user(session: UserSession = Depends(get_current_session)) -> User:
    return session.user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


def require_csrf(
    request: Request,
    session: UserSession = Depends(get_current_session),
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    csrf_cookie: str | None = Cookie(default=None, alias=settings.csrf_cookie_name),
    service: AuthService = Depends(get_auth_service),
) -> User:
    origin = request.headers.get("origin")
    if origin and not _is_trusted_origin_for_request(request, origin):
        raise ForbiddenError("请求来源不受信任")
    if not csrf_header or csrf_header != csrf_cookie:
        raise ForbiddenError("安全令牌无效，请重新登录")
    service.verify_csrf(session, csrf_header)
    return session.user


def _is_trusted_origin_for_request(request: Request, origin: str) -> bool:
    configured = {_normalize_origin(item) for item in settings.cors_origin_list}
    normalized_origin = _normalize_origin(origin)
    if normalized_origin in configured:
        return True
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    request_host = forwarded_host or request.headers.get("host") or request.url.netloc
    request_scheme = forwarded_proto or request.url.scheme
    request_origin = _normalize_origin(f"{request_scheme}://{request_host}")
    return normalized_origin == request_origin


def _normalize_origin(origin: str) -> str:
    parsed = urlparse(origin.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return origin.strip().rstrip("/")
    port = parsed.port
    host = parsed.hostname.lower()
    default_port = (
        port is None
        or (parsed.scheme == "http" and port == 80)
        or (parsed.scheme == "https" and port == 443)
    )
    netloc = host if default_port else f"{host}:{port}"
    return f"{parsed.scheme.lower()}://{netloc}"


def require_write_role(user: User = Depends(require_csrf)) -> User:
    if user.role not in {"designer", "admin"}:
        raise ForbiddenError()
    return user


def require_admin(user: User = Depends(require_csrf)) -> User:
    if user.role != "admin":
        raise ForbiddenError()
    return user


def require_admin_role(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise ForbiddenError()
    return user
