from __future__ import annotations

import hmac
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Cookie, Depends, File, Query, Request, Response, UploadFile
from fastapi.responses import RedirectResponse

from app.api.dependencies import (
    get_audit_service,
    get_auth_service,
    get_current_user,
    get_feishu_auth_service,
    get_usage_analytics_service,
    get_user_avatar_service,
    get_user_service,
    require_csrf,
)
from app.api.storage_response import StorageFileResponse
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.user import User
from app.schemas.auth import (
    AvatarPresetRequest,
    FeishuLoginRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    UserRead,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.feishu_auth_service import FeishuAuthService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.user_avatar_service import UserAvatarService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
FEISHU_STATE_COOKIE = "piancton_feishu_oauth_state"


def _set_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )


def _feishu_redirect_uri() -> str:
    if settings.feishu_redirect_uri:
        return settings.feishu_redirect_uri.strip()
    public_base_url = settings.public_base_url.strip().rstrip("/")
    if not public_base_url:
        raise AppError(
            "feishu_redirect_not_configured", "飞书登录回调地址尚未配置", status_code=503
        )
    return f"{public_base_url}/api/auth/feishu/callback"


@router.get("/feishu/start")
def start_feishu_login(
    service: FeishuAuthService = Depends(get_feishu_auth_service),
):
    state = secrets.token_urlsafe(32)
    redirect = RedirectResponse(
        service.authorization_url(redirect_uri=_feishu_redirect_uri(), state=state),
        status_code=303,
    )
    redirect.set_cookie(
        FEISHU_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/api/auth/feishu",
    )
    return redirect


@router.get("/feishu/callback")
def feishu_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    service: FeishuAuthService = Depends(get_feishu_auth_service),
    audit: AuditService = Depends(get_audit_service),
    usage: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    expected_state = request.cookies.get(FEISHU_STATE_COOKIE)
    invalid_state = (
        error
        or not code
        or not state
        or not expected_state
        or not hmac.compare_digest(state, expected_state)
    )
    if invalid_state:
        redirect = RedirectResponse(
            f"/login?feishu_error={quote(error or '授权校验失败')}", status_code=303
        )
        redirect.delete_cookie(FEISHU_STATE_COOKIE, path="/api/auth/feishu")
        return redirect
    try:
        result = service.login(code)
    except AppError as exc:
        redirect = RedirectResponse(f"/login?feishu_error={quote(exc.code)}", status_code=303)
        redirect.delete_cookie(FEISHU_STATE_COOKIE, path="/api/auth/feishu")
        return redirect
    redirect = RedirectResponse("/", status_code=303)
    _set_session_cookies(redirect, result.session_token, result.csrf_token)
    redirect.delete_cookie(FEISHU_STATE_COOKIE, path="/api/auth/feishu")
    audit.record(
        actor_user_id=result.user.id,
        action="auth.feishu_login",
        target_type="session",
        details={
            "feishuLinked": True,
            "feishuDisplayName": result.user.feishu_display_name,
            "feishuDepartment": result.user.feishu_department_names,
        },
        request_id=request.state.request_id,
    )
    usage.record_login(
        result.user,
        client_ip=request.client.host if request.client else "unknown",
        request_id=request.state.request_id,
    )
    return redirect


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    audit: AuditService = Depends(get_audit_service),
):
    if not settings.self_registration_enabled:
        raise AppError(
            "registration_disabled", "当前不开放自助注册，请联系管理员分配账号", status_code=403
        )
    user = service.register(payload)
    audit.record(
        actor_user_id=user.id,
        action="auth.register",
        target_type="user",
        target_id=user.id,
        request_id=request.state.request_id,
    )
    return user


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    audit: AuditService = Depends(get_audit_service),
    usage: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    client_ip = request.client.host if request.client else "unknown"
    result = service.login(payload.username, payload.password, client_ip)
    audit.record(
        actor_user_id=result.user.id,
        action="auth.login",
        target_type="session",
        details={"clientIp": client_ip},
        request_id=request.state.request_id,
    )
    usage.record_login(
        result.user,
        client_ip=client_ip,
        request_id=request.state.request_id,
    )
    _set_session_cookies(response, result.session_token, result.csrf_token)
    return LoginResponse(
        user=UserRead.model_validate(result.user),
        csrf_token=result.csrf_token,
    )


@router.post("/feishu", response_model=LoginResponse)
def feishu_login(
    payload: FeishuLoginRequest,
    request: Request,
    response: Response,
    service: FeishuAuthService = Depends(get_feishu_auth_service),
    audit: AuditService = Depends(get_audit_service),
    usage: UsageAnalyticsService = Depends(get_usage_analytics_service),
):
    result = service.login(payload.code)
    _set_session_cookies(response, result.session_token, result.csrf_token)
    audit.record(
        actor_user_id=result.user.id,
        action="auth.feishu_login",
        target_type="session",
        details={
            "feishuLinked": True,
            "feishuDisplayName": result.user.feishu_display_name,
            "feishuDepartment": result.user.feishu_department_names,
        },
        request_id=request.state.request_id,
    )
    usage.record_login(
        result.user,
        client_ip=request.client.host if request.client else "unknown",
        request_id=request.state.request_id,
    )
    return LoginResponse(
        user=UserRead.model_validate(result.user),
        csrf_token=result.csrf_token,
    )


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    _: User = Depends(require_csrf),
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    service: AuthService = Depends(get_auth_service),
):
    service.logout(session_token)
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return UserRead.model_validate(user)


@router.post("/onboarding/complete", response_model=UserRead)
def complete_onboarding(
    user: User = Depends(require_csrf),
    service: UserService = Depends(get_user_service),
):
    return service.complete_onboarding(user.id)


@router.post("/avatar", response_model=UserRead)
def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(require_csrf),
    service: UserAvatarService = Depends(get_user_avatar_service),
):
    return service.upload(user, file.file)


@router.post("/avatar/preset", response_model=UserRead)
def select_avatar_preset(
    payload: AvatarPresetRequest,
    user: User = Depends(require_csrf),
    service: UserAvatarService = Depends(get_user_avatar_service),
):
    return service.select_preset(user, payload.preset_id)


@router.get("/avatar")
def get_avatar(
    user: User = Depends(get_current_user),
    service: UserAvatarService = Depends(get_user_avatar_service),
):
    return StorageFileResponse(
        service.thumbnail(user),
        release=service.storage.release,
        media_type="image/jpeg",
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=86400"},
    )
