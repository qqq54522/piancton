from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from fastapi import Cookie, Depends, Header, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.errors import ForbiddenError
from app.db.session import SessionLocal, get_db
from app.models.user import User, UserSession
from app.repositories.api_center_repository import ApiCenterRepository
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
from app.services.search_knowledge_fallback_router import SearchKnowledgeFallbackRouter
from app.services.search_log_service import SearchLogService
from app.services.search_ops_service import SearchOpsService
from app.services.search_service import SearchService
from app.services.semantic_search_clients import EmbeddingClient, RerankerClient
from app.services.storage_factory import build_storage
from app.services.tag_service import TagService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.user_service import UserService
from app.services.viking_knowledge_service_client import VikingKnowledgeServiceClient
from app.services.viking_knowledge_service_router import VikingKnowledgeServiceRouter
from app.services.vikingdb_client import VikingDBClient
from app.services.vikingdb_knowledge_router import VikingDBKnowledgeRouter
from app.services.vikingdb_vector_index import VikingDBVectorIndexSync
from app.services.volc_ai_search_client import VolcAiSearchClient
from app.services.volc_ai_search_service import VolcAiSearchService
from app.services.volc_ai_search_sync import VolcAiSearchIndexSync

settings = get_settings()


def _api_center_setting(db: Session, key: str, default: object) -> str:
    row = ApiCenterRepository(db).get_setting(key)
    if row is not None and row.value != "":
        return row.value
    return str(default or "")


def _api_center_bool(db: Session, key: str, default: bool) -> bool:
    raw = _api_center_setting(db, key, default).strip().lower()
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _api_center_float(
    db: Session,
    key: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    try:
        value = float(_api_center_setting(db, key, default).strip())
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _api_center_int(
    db: Session,
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    try:
        value = int(float(_api_center_setting(db, key, default).strip()))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


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


def _build_vikingdb_knowledge_router(
    db: Session,
) -> (
    VikingDBKnowledgeRouter
    | VikingKnowledgeServiceRouter
    | SearchKnowledgeFallbackRouter
    | None
):
    runtime_catalog = IntentCatalogService(
        BusinessConceptRepository(db)
    ).runtime_catalog()
    vector_enabled = _api_center_bool(
        db,
        "vikingdb_knowledge_router_enabled",
        settings.vikingdb_knowledge_router_enabled,
    )
    vector_base_url = _api_center_setting(db, "vikingdb_base_url", settings.vikingdb_base_url)
    vector_api_key = _api_center_setting(db, "vikingdb_api_key", settings.vikingdb_api_key)
    vector_collection_name = _api_center_setting(
        db,
        "vikingdb_collection_name",
        settings.vikingdb_collection_name,
    )
    vector_index_name = _api_center_setting(
        db,
        "vikingdb_index_name",
        settings.vikingdb_index_name,
    )
    vector_timeout_seconds = _api_center_float(
        db,
        "vikingdb_timeout_seconds",
        settings.vikingdb_timeout_seconds,
        minimum=0.5,
        maximum=120.0,
    )
    vector_search_limit = _api_center_int(
        db,
        "vikingdb_search_limit",
        settings.vikingdb_search_limit,
        minimum=1,
        maximum=100,
    )
    knowledge_service_enabled = _api_center_bool(
        db,
        "viking_knowledge_service_enabled",
        settings.viking_knowledge_service_enabled,
    )
    fallback_enabled = _api_center_bool(
        db,
        "vikingdb_knowledge_fallback_enabled",
        settings.vikingdb_knowledge_fallback_enabled,
    )
    vector_router = None
    if vector_enabled:
        vector_router = VikingDBKnowledgeRouter(
            client=VikingDBClient(
                base_url=vector_base_url,
                api_key=vector_api_key,
                collection_name=vector_collection_name,
                upsert_path=settings.vikingdb_upsert_path,
                search_path=settings.vikingdb_search_path,
                timeout_seconds=vector_timeout_seconds,
            ),
            index_name=vector_index_name,
            runtime_catalog=runtime_catalog,
            enabled=vector_enabled,
            limit=vector_search_limit,
            min_score=_api_center_float(
                db,
                "vikingdb_knowledge_min_score",
                settings.vikingdb_knowledge_min_score,
                minimum=0.0,
                maximum=1.0,
            ),
            multi_score_ratio=settings.vikingdb_knowledge_multi_score_ratio,
            multi_score_gap=settings.vikingdb_knowledge_multi_score_gap,
            max_matches=_api_center_int(
                db,
                "vikingdb_knowledge_max_matches",
                settings.vikingdb_knowledge_max_matches,
                minimum=1,
                maximum=6,
            ),
        )
    if knowledge_service_enabled:
        service_router = VikingKnowledgeServiceRouter(
            client=VikingKnowledgeServiceClient(
                base_url=_api_center_setting(
                    db,
                    "viking_knowledge_service_base_url",
                    settings.viking_knowledge_service_base_url,
                ),
                api_key=_api_center_setting(
                    db,
                    "viking_knowledge_service_api_key",
                    settings.viking_knowledge_service_api_key,
                ),
                service_resource_id=_api_center_setting(
                    db,
                    "viking_knowledge_service_resource_id",
                    settings.viking_knowledge_service_resource_id,
                ),
                chat_path=settings.viking_knowledge_service_path,
                timeout_seconds=_api_center_float(
                    db,
                    "viking_knowledge_service_timeout_seconds",
                    settings.viking_knowledge_service_timeout_seconds,
                    minimum=0.5,
                    maximum=60.0,
                ),
                result_limit=_api_center_int(
                    db,
                    "viking_knowledge_service_result_limit",
                    settings.viking_knowledge_service_result_limit,
                    minimum=1,
                    maximum=20,
                ),
            ),
            runtime_catalog=runtime_catalog,
            enabled=knowledge_service_enabled,
            max_matches=_api_center_int(
                db,
                "viking_knowledge_service_max_matches",
                settings.viking_knowledge_service_max_matches,
                minimum=1,
                maximum=6,
            ),
        )
        if fallback_enabled:
            fallback_router = VikingDBKnowledgeRouter(
                client=VikingDBClient(
                    base_url=vector_base_url,
                    api_key=vector_api_key,
                    collection_name=vector_collection_name,
                    upsert_path=settings.vikingdb_upsert_path,
                    search_path=settings.vikingdb_search_path,
                    timeout_seconds=vector_timeout_seconds,
                ),
                index_name=vector_index_name,
                runtime_catalog=runtime_catalog,
                enabled=vector_enabled,
                limit=max(1, vector_search_limit),
                min_score=_api_center_float(
                    db,
                    "vikingdb_knowledge_fallback_min_score",
                    settings.vikingdb_knowledge_fallback_min_score,
                    minimum=0.0,
                    maximum=1.0,
                ),
                multi_score_ratio=1.0,
                multi_score_gap=0.0,
                max_matches=_api_center_int(
                    db,
                    "vikingdb_knowledge_fallback_max_matches",
                    settings.vikingdb_knowledge_fallback_max_matches,
                    minimum=1,
                    maximum=6,
                ),
            )
            return SearchKnowledgeFallbackRouter(
                primary=service_router,
                fallback=fallback_router,
            )
        return service_router
    return vector_router


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
        search_path=settings.ai_search_search_path,
        timeout_seconds=settings.ai_search_timeout_seconds,
    )


def _build_ai_search_index() -> VolcAiSearchIndexSync:
    public_base_url = (
        settings.ai_search_public_base_url
        or settings.public_base_url
        or _first_cors_origin()
    )
    return VolcAiSearchIndexSync(
        _build_ai_search_client(),
        enabled=settings.ai_search_enabled and settings.ai_search_sync_enabled,
        public_base_url=public_base_url,
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
        embedding_index=EmbeddingIndexSync.from_settings(),
        vector_index=VikingDBVectorIndexSync.from_settings(),
        ai_search_index=_build_ai_search_index(),
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
        vector_index=VikingDBVectorIndexSync.from_settings(),
        ai_search_index=_build_ai_search_index(),
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
        (
            _api_center_bool(
                db,
                "viking_knowledge_service_enabled",
                settings.viking_knowledge_service_enabled,
            )
            or _api_center_bool(
                db,
                "vikingdb_knowledge_router_enabled",
                settings.vikingdb_knowledge_router_enabled,
            )
        )
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
        knowledge_router=_build_vikingdb_knowledge_router(db),
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
