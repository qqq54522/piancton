from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal, get_db
from app.models.user import User, UserSession
from app.repositories.business_concept_repository import BusinessConceptRepository
from app.services.ai_knowledge_service import AiKnowledgeService
from app.services.ai_service import AiService
from app.services.api_center_service import ApiCenterService
from app.services.asset_agent_service import AssetAgentService
from app.services.asset_identity_admin_service import AssetIdentityAdminService
from app.services.asset_identity_service import AssetIdentityService
from app.services.asset_relation_service import AssetRelationService
from app.services.asset_service import AssetService
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.business_concept_service import BusinessConceptService
from app.services.embedding_index import EmbeddingIndexSync
from app.services.image_analysis_service import ImageAnalysisService
from app.services.image_lifecycle_service import ImageLifecycleService
from app.services.image_service import ImageService
from app.services.intent_catalog_service import IntentCatalogService
from app.services.search_cache import shared_search_caches
from app.services.search_index_sync import SearchIndexSync
from app.services.search_log_service import SearchLogService
from app.services.search_ops_service import SearchOpsService
from app.services.search_service import SearchService
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient
from app.services.storage_factory import build_storage
from app.services.tag_service import TagService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.user_service import UserService
from app.services.vikingdb_client import VikingDBClient
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter
from app.services.vikingdb_vector_index import VikingDBVectorIndexSync

settings = get_settings()


def _trace_session_factory(db: Session):
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    return factory


def _provider_attempt_count(provider) -> int:
    return max(1, int(getattr(provider, "attempt_count", 1)))


def _build_scheduled_provider(
    db: Session,
    *,
    request_id: str | None = None,
):
    api_center = ApiCenterService(
        db,
        trace_session_factory=_trace_session_factory(db),
    )
    api_center.initialize_runtime()
    return api_center.build_scheduled_provider(default_request_id=request_id)


def _build_vikingdb_knowledge_router(db: Session) -> VikingDBKnowledgeRouter | None:
    if not settings.vikingdb_knowledge_router_enabled:
        return None
    return VikingDBKnowledgeRouter(
        client=VikingDBClient(
            base_url=settings.vikingdb_base_url,
            api_key=settings.vikingdb_api_key,
            collection_name=settings.vikingdb_collection_name,
            upsert_path=settings.vikingdb_upsert_path,
            search_path=settings.vikingdb_search_path,
            timeout_seconds=settings.vikingdb_timeout_seconds,
        ),
        index_name=settings.vikingdb_index_name,
        runtime_catalog=IntentCatalogService(
            BusinessConceptRepository(db)
        ).runtime_catalog(),
        enabled=settings.vikingdb_knowledge_router_enabled,
        limit=settings.vikingdb_search_limit,
        min_score=settings.vikingdb_knowledge_min_score,
        multi_score_ratio=settings.vikingdb_knowledge_multi_score_ratio,
        multi_score_gap=settings.vikingdb_knowledge_multi_score_gap,
        max_matches=settings.vikingdb_knowledge_max_matches,
    )


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
        build_storage(settings),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
        embedding_index=EmbeddingIndexSync.from_settings(),
        vector_index=VikingDBVectorIndexSync.from_settings(),
    )


def get_asset_service(db: Session = Depends(get_db)) -> AssetService:
    return AssetService(
        db,
        build_storage(settings),
        settings.max_upload_bytes,
        settings.max_image_pixels,
        settings.thumbnail_max_size,
        vector_index=VikingDBVectorIndexSync.from_settings(),
    )


def get_asset_identity_service(db: Session = Depends(get_db)) -> AssetIdentityService:
    return AssetIdentityService(db)


def get_asset_identity_admin_service(
    db: Session = Depends(get_db),
) -> AssetIdentityAdminService:
    return AssetIdentityAdminService(db)


def get_asset_relation_service(db: Session = Depends(get_db)) -> AssetRelationService:
    return AssetRelationService(
        db,
        search_index=SearchIndexSync.from_settings(),
        embedding_index=EmbeddingIndexSync.from_settings(),
        vector_index=VikingDBVectorIndexSync.from_settings(),
    )


def get_business_concept_service(
    db: Session = Depends(get_db),
) -> BusinessConceptService:
    return BusinessConceptService(db)


def get_image_lifecycle_service(db: Session = Depends(get_db)) -> ImageLifecycleService:
    return ImageLifecycleService(
        db,
        build_storage(settings),
        vector_index=VikingDBVectorIndexSync.from_settings(),
    )


def get_image_analysis_service(db: Session = Depends(get_db)) -> ImageAnalysisService:
    return ImageAnalysisService(
        db,
        embedding_index=EmbeddingIndexSync.from_settings(),
        vector_index=VikingDBVectorIndexSync.from_settings(),
    )


def get_tag_service(db: Session = Depends(get_db)) -> TagService:
    return TagService(db)


def get_search_service(
    request: Request,
    db: Session = Depends(get_db),
) -> SearchService:
    pure_vikingdb_search = (
        settings.vikingdb_knowledge_router_enabled
        and not settings.vikingdb_skill_backup_enabled
    )
    search_ai_service = get_search_ai_service(
        db,
        request_id=request.state.request_id,
    )
    provider_attempts = (
        1
        if pure_vikingdb_search
        else _provider_attempt_count(search_ai_service.provider)
    )
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
        vikingdb_knowledge_router=_build_vikingdb_knowledge_router(db),
        vikingdb_skill_backup_enabled=settings.vikingdb_skill_backup_enabled,
    )


def get_search_log_service(db: Session = Depends(get_db)) -> SearchLogService:
    return SearchLogService(db)


def get_search_ops_service(db: Session = Depends(get_db)) -> SearchOpsService:
    return SearchOpsService(db)


def get_api_center_service(db: Session = Depends(get_db)) -> ApiCenterService:
    return ApiCenterService(db, trace_session_factory=_trace_session_factory(db))


def get_ai_service(
    request: Request,
    db: Session = Depends(get_db),
) -> AiService:
    return AiService(
        _build_scheduled_provider(db, request_id=request.state.request_id),
        knowledge=AiKnowledgeService(db).knowledge(),
    )


def get_asset_agent_service(
    request: Request,
    db: Session = Depends(get_db),
) -> AssetAgentService:
    return AssetAgentService(
        db,
        _build_scheduled_provider(db, request_id=request.state.request_id),
    )


def get_search_ai_service(
    db: Session = Depends(get_db),
    *,
    request_id: str | None = None,
) -> AiService:
    return AiService(
        _build_scheduled_provider(db, request_id=request_id),
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
