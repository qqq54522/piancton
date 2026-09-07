from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.api.dependencies import (
    get_audit_service,
    get_auth_service,
    get_current_user,
    get_usage_analytics_service,
    get_user_service,
    require_csrf,
)
from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserRead
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.usage_analytics_service import UsageAnalyticsService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=UserRead, status_code=201)
def register(
    payload: RegisterRequest,
    request: Request,
    service: UserService = Depends(get_user_service),
    audit: AuditService = Depends(get_audit_service),
):
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
    max_age = settings.session_ttl_hours * 3600
    response.set_cookie(
        settings.session_cookie_name,
        result.session_token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        result.csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
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
