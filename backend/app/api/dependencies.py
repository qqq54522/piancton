from __future__ import annotations

from collections.abc import Callable
from math import ceil

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.ai import get_model_provider
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal, get_db
from app.models.user import User, UserSession
from app.services.ai_knowledge_service import AiKnowledgeService
from app.services.ai_service import AiService
from app.services.asset_phrase_suggestion_service import AssetPhraseSuggestionService
from app.services.asset_relation_service import AssetRelationService
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.business_concept_service import BusinessConceptService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_lifecycle_service import ImageLifecycleService
from app.services.image_service import ImageService
from app.services.search_cache import shared_search_caches
from app.services.search_index_sync import SearchIndexSync
from app.services.search_log_service import SearchLogService
from app.services.search_ops_service import SearchOpsService
from app.services.search_service import SearchService
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient
from app.services.storage_service import LocalStorageProvider
from app.services.tag_service import TagService
from app.services.user_service import UserService

settings = get_settings()


def _provider_attempt_count(provider) -> int:
    return max(1, int(getattr(provider, "attempt_count", 1)))


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


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    return ImageService(
        db,
        LocalStorageProvider(settings.storage_dir),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
        embedding_index=EmbeddingIndexSync.from_settings(),
    )


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(
        db,
        LocalStorageProvider(settings.storage_dir),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
    )


def get_asset_relation_service(db: Session = Depends(get_db)) -> AssetRelationService:
    return AssetRelationService(
        db,
        search_index=SearchIndexSync.from_settings(),
        embedding_index=EmbeddingIndexSync.from_settings(),
    )


def get_business_concept_service(
    db: Session = Depends(get_db),
) -> BusinessConceptService:
    return BusinessConceptService(db)


def get_image_lifecycle_service(db: Session = Depends(get_db)) -> ImageLifecycleService:
    return ImageLifecycleService(db, LocalStorageProvider(settings.storage_dir))


def get_image_analysis_service(db: Session = Depends(get_db)) -> ImageAnalysisService:
    return ImageAnalysisService(db, embedding_index=EmbeddingIndexSync.from_settings())


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    search_ai_service = get_search_ai_service(db)
    provider_attempts = _provider_attempt_count(search_ai_service.provider)
    return SearchService(
        db,
        search_backend=settings.search_backend,
        meilisearch_url=settings.meilisearch_url,
        meilisearch_api_key=settings.meilisearch_api_key,
        meilisearch_index=settings.meilisearch_index,
        search_timeout_seconds=settings.search_meilisearch_timeout_seconds,
        ai_service=search_ai_service,
        embedding_client=EmbeddingClient(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model_name=settings.embedding_model_name,
            timeout_seconds=min(
                settings.embedding_timeout_seconds,
                settings.search_embedding_timeout_seconds,
            ),
        ),
        embedding_top_n=settings.embedding_top_n,
        reranker=RerankerClient(
            base_url=settings.reranker_base_url,
            api_key=settings.reranker_api_key,
            model_name=settings.reranker_model_name,
            timeout_seconds=min(
                settings.reranker_timeout_seconds,
                settings.search_reranker_timeout_seconds,
            ),
        ),
        reranker_top_n=settings.reranker_top_n,
        total_timeout_seconds=settings.search_total_timeout_seconds,
        meilisearch_timeout_seconds=settings.search_meilisearch_timeout_seconds,
        embedding_timeout_seconds=settings.search_embedding_timeout_seconds,
        understanding_timeout_seconds=(
            settings.search_understanding_timeout_seconds * provider_attempts
        ),
        system_routing_timeout_seconds=(
            settings.search_system_routing_timeout_seconds * provider_attempts
        ),
        selling_point_timeout_seconds=(
            settings.search_selling_point_timeout_seconds * provider_attempts
        ),
        proof_point_timeout_seconds=(
            settings.search_proof_point_timeout_seconds * provider_attempts
        ),
        candidate_review_timeout_seconds=(
            settings.search_candidate_review_timeout_seconds * provider_attempts
            + settings.search_understanding_grace_seconds * provider_attempts
        ),
        candidate_review_limit=settings.search_candidate_review_limit,
        understanding_grace_seconds=settings.search_understanding_grace_seconds,
        understanding_retry_attempts=settings.search_understanding_retry_attempts,
        understanding_retry_backoff_seconds=(
            settings.search_understanding_retry_backoff_seconds
        ),
        reranker_timeout_seconds=settings.search_reranker_timeout_seconds,
        candidate_limit=settings.search_candidate_limit,
        cache_ttl_seconds=settings.search_cache_ttl_seconds,
        cache_max_entries=settings.search_cache_max_entries,
        caches=shared_search_caches(
            settings.search_cache_ttl_seconds,
            settings.search_cache_max_entries,
        ),
    )


def get_search_log_service(db: Session = Depends(get_db)) -> SearchLogService:
    return SearchLogService(db)


def get_search_ops_service(db: Session = Depends(get_db)) -> SearchOpsService:
    return SearchOpsService(db)


def get_ai_service(db: Session = Depends(get_db)) -> AiService:
    return AiService(
        get_model_provider(purpose="image_analysis"),
        knowledge=AiKnowledgeService(db).knowledge(),
    )


def get_asset_phrase_ai_service(db: Session = Depends(get_db)) -> AiService:
    return AiService(
        get_model_provider(purpose="asset_phrase"),
        knowledge=AiKnowledgeService(db).knowledge(),
    )


def get_asset_phrase_suggestion_service(
    ai: AiService = Depends(get_asset_phrase_ai_service),
) -> AssetPhraseSuggestionService:
    return AssetPhraseSuggestionService(
        ai,
        LocalStorageProvider(settings.storage_dir),
        max_upload_bytes=settings.max_upload_bytes,
        max_image_pixels=settings.max_image_pixels,
        thumbnail_max_size=settings.thumbnail_max_size,
    )


def get_search_ai_service(db: Session = Depends(get_db)) -> AiService:
    provider_timeout = max(
        settings.search_understanding_timeout_seconds,
        settings.search_system_routing_timeout_seconds,
        settings.search_selling_point_timeout_seconds,
        settings.search_proof_point_timeout_seconds,
    )
    return AiService(
        get_model_provider(
            timeout_seconds=max(1, ceil(provider_timeout)),
            purpose="search",
        ),
        knowledge=AiKnowledgeService(db).knowledge(),
        system_routing_timeout_seconds=(settings.search_system_routing_timeout_seconds),
        selling_point_timeout_seconds=(settings.search_selling_point_timeout_seconds),
        proof_point_timeout_seconds=(settings.search_proof_point_timeout_seconds),
        candidate_review_timeout_seconds=(
            settings.search_candidate_review_timeout_seconds
        ),
    )


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)


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
    if origin and origin not in settings.cors_origin_list:
        raise ForbiddenError("请求来源不受信任")
    if not csrf_header or csrf_header != csrf_cookie:
        raise ForbiddenError("安全令牌无效，请重新登录")
    service.verify_csrf(session, csrf_header)
    return session.user


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
