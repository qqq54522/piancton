from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from urllib.parse import urlencode

import httpx

from app.core.errors import AppError
from app.core.security import hash_password, hash_secret, new_secret
from app.models.user import User, UserSession
from app.repositories.user_repository import SessionRepository, UserRepository
from app.services.auth_service import AuthResult
from app.services.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeishuIdentity:
    open_id: str
    union_id: str | None
    user_id: str | None
    tenant_key: str | None
    display_name: str
    department_names: str | None


class FeishuAuthService:
    """Exchange an in-client Feishu auth code and bind it to a local session."""

    def __init__(
        self,
        db,
        *,
        enabled: bool,
        app_id: str,
        app_secret: str,
        allowed_tenant_key: str,
        base_url: str,
        timeout_seconds: float,
        http_client_factory: Callable[..., Any] = httpx.Client,
        session_ttl_hours: int = 168,
    ):
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.uow = UnitOfWork(db)
        self.enabled = enabled
        self.app_id = app_id.strip()
        self.app_secret = app_secret.strip()
        self.allowed_tenant_key = allowed_tenant_key.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.http_client_factory = http_client_factory
        self.session_ttl_hours = session_ttl_hours

    def login(self, code: str) -> AuthResult:
        identity = self._exchange_code(code)
        user = self.users.get_by_feishu_identity(
            open_id=identity.open_id,
            user_id=identity.user_id,
            union_id=identity.union_id,
        )
        if user is None:
            user = self._create_user(identity)
        else:
            self._update_identity(user, identity)

        now = datetime.now(timezone.utc)
        user.last_feishu_login_at = now
        self.users.save(user)
        self.sessions.delete_expired()
        session_token = new_secret()
        csrf_token = new_secret()
        expires_at = now + timedelta(hours=self.session_ttl_hours)
        self.sessions.add(
            UserSession(
                token_hash=hash_secret(session_token),
                csrf_hash=hash_secret(csrf_token),
                user_id=user.id,
                expires_at=expires_at,
            )
        )
        self.uow.commit()
        return AuthResult(user, session_token, csrf_token, expires_at)

    def authorization_url(self, *, redirect_uri: str, state: str) -> str:
        if not self.enabled or not self.app_id or not self.app_secret:
            raise AppError("feishu_not_configured", "飞书登录尚未配置", status_code=503)
        if not redirect_uri:
            raise AppError(
                "feishu_redirect_not_configured", "飞书登录回调地址尚未配置", status_code=503
            )
        query = urlencode(
            {
                "client_id": self.app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "state": state,
            }
        )
        return f"{self.base_url}/open-apis/authen/v1/authorize?{query}"

    def _exchange_code(self, code: str) -> FeishuIdentity:
        if not self.enabled or not self.app_id or not self.app_secret:
            raise AppError("feishu_not_configured", "飞书登录尚未配置", status_code=503)
        try:
            with self.http_client_factory(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            ) as client:
                token_payload = self._post(
                    client,
                    "/open-apis/authen/v1/access_token",
                    {
                        "grant_type": "authorization_code",
                        "code": code,
                        "app_id": self.app_id,
                        "app_secret": self.app_secret,
                    },
                )
                token_data = self._data(token_payload)
                user_access_token = str(token_data.get("access_token") or "")
                if not user_access_token:
                    raise AppError(
                        "feishu_auth_failed", "飞书没有返回用户访问凭证", status_code=401
                    )
                user_payload = self._get(
                    client,
                    "/open-apis/authen/v1/user_info",
                    headers={"Authorization": f"Bearer {user_access_token}"},
                )
                user_data = self._data(user_payload)
                user_data = (
                    user_data.get("user")
                    if isinstance(user_data.get("user"), dict)
                    else user_data
                )
                open_id = str(user_data.get("open_id") or token_data.get("open_id") or "")
                user_id = self._optional_string(
                    user_data.get("user_id") or token_data.get("user_id")
                )
                union_id = self._optional_string(
                    user_data.get("union_id") or token_data.get("union_id")
                )
                tenant_key = self._optional_string(user_data.get("tenant_key"))
                if not open_id:
                    raise AppError("feishu_auth_failed", "飞书用户身份信息不完整", status_code=401)
                if self.allowed_tenant_key and tenant_key != self.allowed_tenant_key:
                    raise AppError(
                        "feishu_tenant_forbidden", "该飞书用户不属于当前企业", status_code=403
                    )
                department_names = self._department_names(client, user_id)
                display_name = str(
                    user_data.get("name")
                    or user_data.get("display_name")
                    or user_data.get("en_name")
                    or open_id
                ).strip()
                return FeishuIdentity(
                    open_id=open_id,
                    union_id=union_id,
                    user_id=user_id,
                    tenant_key=tenant_key,
                    display_name=display_name,
                    department_names=department_names,
                )
        except AppError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning("Feishu login exchange failed: %s", exc.__class__.__name__)
            raise AppError(
                "feishu_auth_unavailable", "暂时无法连接飞书，请稍后重试", status_code=502
            ) from exc

    def _department_names(self, client: Any, user_id: str | None) -> str | None:
        if not user_id:
            return None
        try:
            tenant_payload = self._post(
                client,
                "/open-apis/auth/v3/tenant_access_token/internal",
                {"app_id": self.app_id, "app_secret": self.app_secret},
            )
            tenant_token = str(self._data(tenant_payload).get("tenant_access_token") or "")
            if not tenant_token:
                return None
            user_payload = self._get(
                client,
                f"/open-apis/contact/v3/users/{user_id}",
                headers={"Authorization": f"Bearer {tenant_token}"},
                params={"user_id_type": "user_id"},
            )
            contact_user = self._data(user_payload).get("user", {})
            department_ids = contact_user.get("department_ids") or []
            if not department_ids:
                return None
            names: list[str] = []
            for department_id in department_ids[:20]:
                try:
                    department_payload = self._get(
                        client,
                        f"/open-apis/contact/v3/departments/{department_id}",
                        headers={"Authorization": f"Bearer {tenant_token}"},
                        params={"department_id_type": "open_department_id"},
                    )
                    department = self._data(department_payload).get("department", {})
                    name = str(department.get("name") or "").strip()
                    if name and name not in names:
                        names.append(name)
                except AppError:
                    continue
            return "、".join(names) if names else None
        except (AppError, httpx.HTTPError, ValueError, TypeError) as exc:
            # Missing department scope must not prevent a user from logging in.
            logger.info("Feishu department lookup unavailable: %s", exc.__class__.__name__)
            return None

    def _create_user(self, identity: FeishuIdentity) -> User:
        base = f"feishu_{identity.user_id or identity.open_id}"[:92]
        username = base
        suffix = 2
        while self.users.get_by_username(username):
            username = f"{base[:90]}_{suffix}"
            suffix += 1
        user = User(
            username=username,
            password_hash=hash_password(new_secret()),
            role="business",
        )
        self._update_identity(user, identity)
        self.users.add(user)
        return user

    @staticmethod
    def _update_identity(user: User, identity: FeishuIdentity) -> None:
        user.feishu_open_id = identity.open_id
        user.feishu_union_id = identity.union_id
        user.feishu_user_id = identity.user_id
        user.feishu_tenant_key = identity.tenant_key
        user.feishu_display_name = identity.display_name
        user.feishu_department_names = identity.department_names

    def _post(self, client: Any, path: str, payload: dict[str, str]) -> dict[str, Any]:
        response = client.post(path, json=payload)
        return self._validate_response(response)

    def _get(
        self,
        client: Any,
        path: str,
        *,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        response = client.get(path, headers=headers, params=params)
        return self._validate_response(response)

    @staticmethod
    def _validate_response(response: Any) -> dict[str, Any]:
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("code", 0) not in (0, "0", None):
            raise AppError("feishu_auth_failed", "飞书身份校验失败", status_code=401)
        return payload

    @staticmethod
    def _data(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        value = str(value or "").strip()
        return value or None
