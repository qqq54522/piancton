from __future__ import annotations

from collections.abc import Callable

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session

from app.ai import get_model_provider
from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal, get_db
from app.models.user import User, UserSession
from app.services.ai_service import AiService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_lifecycle_service import ImageLifecycleService
from app.services.image_service import ImageService
from app.services.image_tagging_service import ImageTaggingService
from app.services.search_service import SearchService
from app.services.semantic_search_clients import RerankerClient
from app.services.storage_service import LocalStorageProvider
from app.services.tag_service import TagService
from app.services.user_service import UserService

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


def get_image_service(db: Session = Depends(get_db)) -> ImageService:
    return ImageService(
        db,
        LocalStorageProvider(settings.storage_dir),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
        embedding_index=EmbeddingIndexSync.from_settings(),
    )


def get_image_lifecycle_service(db: Session = Depends(get_db)) -> ImageLifecycleService:
    return ImageLifecycleService(db, LocalStorageProvider(settings.storage_dir))


def get_image_tagging_service(db: Session = Depends(get_db)) -> ImageTaggingService:
    return ImageTaggingService(db, embedding_index=EmbeddingIndexSync.from_settings())


def get_image_analysis_service(db: Session = Depends(get_db)) -> ImageAnalysisService:
    return ImageAnalysisService(db, embedding_index=EmbeddingIndexSync.from_settings())


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


def get_search_service(db: Session = Depends(get_db)) -> SearchService:
    return SearchService(
        db,
        search_backend=settings.search_backend,
        meilisearch_url=settings.meilisearch_url,
        meilisearch_api_key=settings.meilisearch_api_key,
        meilisearch_index=settings.meilisearch_index,
        search_timeout_seconds=settings.search_timeout_seconds,
        ai_service=get_ai_service(),
        embedding_client=EmbeddingIndexSync.from_settings().client,
        embedding_top_n=settings.embedding_top_n,
        reranker=RerankerClient(
            base_url=settings.reranker_base_url,
            api_key=settings.reranker_api_key,
            model_name=settings.reranker_model_name,
            timeout_seconds=settings.reranker_timeout_seconds,
        ),
        reranker_top_n=settings.reranker_top_n,
    )


def get_ai_service() -> AiService:
    return AiService(get_model_provider())


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
