from __future__ import annotations

import secrets
import threading
from collections import deque
from datetime import datetime, timezone

from app.core.errors import AppError, NotFoundError
from app.core.security import hash_secret
from app.models.external_api_key import ExternalApiKey
from app.repositories.external_api_key_repository import ExternalApiKeyRepository, is_key_active
from app.schemas.external_api import (
    ExternalApiKeyCreate,
    ExternalApiKeyCreated,
    ExternalApiKeyRead,
)
from app.services.unit_of_work import UnitOfWork


class ExternalApiKeyService:
    _rate_lock = threading.Lock()
    _rate_windows: dict[str, deque[float]] = {}

    def __init__(self, db):
        self.keys = ExternalApiKeyRepository(db)
        self.uow = UnitOfWork(db)

    def create(self, payload: ExternalApiKeyCreate, *, created_by: str) -> ExternalApiKeyCreated:
        raw_secret = f"pk_live_{secrets.token_urlsafe(32)}"
        key = self.keys.add(
            ExternalApiKey(
                name=payload.name.strip(),
                key_prefix=raw_secret[:16],
                secret_hash=hash_secret(raw_secret),
                secret_preview=f"{raw_secret[:8]}...{raw_secret[-4:]}",
                rate_limit_per_minute=payload.rate_limit_per_minute,
                expires_at=payload.expires_at,
                created_by=created_by,
            )
        )
        self.uow.commit()
        return ExternalApiKeyCreated(
            **self._read(key).model_dump(),
            secret=raw_secret,
        )

    def list(self) -> list[ExternalApiKeyRead]:
        return [self._read(key) for key in self.keys.list()]

    def revoke(self, key_id: str) -> ExternalApiKeyRead:
        key = self.keys.get(key_id)
        if key is None:
            raise NotFoundError("external_api_key_not_found", "API Key 不存在")
        key.status = "revoked"
        key.revoked_at = datetime.now(timezone.utc)
        self.keys.save(key)
        self.uow.commit()
        return self._read(key)

    def authenticate(self, raw_secret: str) -> ExternalApiKey:
        key = self.keys.get_by_hash(hash_secret(raw_secret))
        if key is None or not is_key_active(key):
            raise AppError("invalid_api_key", "API Key 无效或已失效", status_code=401)
        self._check_rate_limit(key)
        key.last_used_at = datetime.now(timezone.utc)
        self.keys.save(key)
        return key

    @classmethod
    def _check_rate_limit(cls, key: ExternalApiKey) -> None:
        now = datetime.now(timezone.utc).timestamp()
        with cls._rate_lock:
            window = cls._rate_windows.setdefault(key.id, deque())
            while window and window[0] <= now - 60:
                window.popleft()
            if len(window) >= key.rate_limit_per_minute:
                raise AppError(
                    "api_rate_limit_exceeded",
                    "API Key 请求过于频繁，请稍后再试",
                    status_code=429,
                )
            window.append(now)

    @staticmethod
    def _read(key: ExternalApiKey) -> ExternalApiKeyRead:
        result = ExternalApiKeyRead.model_validate(key, from_attributes=True)
        expires_at = key.expires_at
        normalized_expiry = (
            expires_at.replace(tzinfo=timezone.utc)
            if expires_at is not None and expires_at.tzinfo is None
            else expires_at
        )
        if (
            result.status == "active"
            and normalized_expiry is not None
            and normalized_expiry <= datetime.now(timezone.utc)
        ):
            result.status = "expired"
        return result
