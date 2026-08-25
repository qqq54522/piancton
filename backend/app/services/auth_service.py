from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.errors import AppError, UnauthorizedError
from app.core.security import hash_secret, new_secret, verify_password
from app.models.user import LoginThrottle, User, UserSession
from app.repositories.user_repository import (
    LoginThrottleRepository,
    SessionRepository,
    UserRepository,
)
from app.services.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class AuthResult:
    user: User
    session_token: str
    csrf_token: str
    expires_at: datetime


class AuthService:
    def __init__(
        self,
        db,
        session_ttl_hours: int,
        login_max_attempts: int,
        login_window_minutes: int,
        login_block_minutes: int,
    ):
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.throttles = LoginThrottleRepository(db)
        self.uow = UnitOfWork(db)
        self.session_ttl_hours = session_ttl_hours
        self.login_max_attempts = login_max_attempts
        self.login_window = timedelta(minutes=login_window_minutes)
        self.login_block = timedelta(minutes=login_block_minutes)

    def login(self, username: str, password: str, client_ip: str) -> AuthResult:
        normalized_username = username.strip().lower()
        throttle_key = hash_secret(f"{normalized_username}|{client_ip}")
        now = datetime.now(timezone.utc)
        throttle = self.throttles.get(throttle_key)
        blocked_until = self._as_utc(throttle.blocked_until) if throttle else None
        if blocked_until and blocked_until > now:
            raise AppError(
                "login_rate_limited",
                "登录失败次数过多，请稍后重试",
                status_code=429,
            )
        user = self.users.get_by_username(username.strip())
        if not user or not user.is_active or not verify_password(user.password_hash, password):
            self._record_failure(throttle_key, throttle, now)
            raise UnauthorizedError("账号或密码错误")
        if throttle:
            self.throttles.delete(throttle)
        self.sessions.delete_expired()
        session_token = new_secret()
        csrf_token = new_secret()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.session_ttl_hours)
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

    def _record_failure(
        self,
        key: str,
        throttle: LoginThrottle | None,
        now: datetime,
    ) -> None:
        window_started = self._as_utc(throttle.window_started_at) if throttle else None
        if not throttle:
            throttle = LoginThrottle(key=key, attempts=0, window_started_at=now)
        elif not window_started or now - window_started > self.login_window:
            throttle.attempts = 0
            throttle.window_started_at = now
            throttle.blocked_until = None
        throttle.attempts += 1
        if throttle.attempts >= self.login_max_attempts:
            throttle.blocked_until = now + self.login_block
        self.throttles.save(throttle)
        self.uow.commit()

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def logout(self, session_token: str | None) -> None:
        if session_token:
            self.sessions.delete_by_token(hash_secret(session_token))
            self.uow.commit()

    def authenticate(self, session_token: str | None) -> UserSession:
        if not session_token:
            raise UnauthorizedError()
        session = self.sessions.get_valid(hash_secret(session_token))
        if not session or not session.user.is_active:
            raise UnauthorizedError("登录状态已失效")
        return session

    def verify_csrf(self, session: UserSession, csrf_token: str | None) -> None:
        if not csrf_token or hash_secret(csrf_token) != session.csrf_hash:
            raise UnauthorizedError("安全令牌无效，请重新登录")
