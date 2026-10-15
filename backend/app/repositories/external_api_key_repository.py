from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.external_api_key import ExternalApiKey


class ExternalApiKeyRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[ExternalApiKey]:
        statement = select(ExternalApiKey).order_by(ExternalApiKey.created_at.desc())
        return list(self.db.scalars(statement).all())

    def get(self, key_id: str) -> ExternalApiKey | None:
        return self.db.get(ExternalApiKey, key_id)

    def get_by_hash(self, secret_hash: str) -> ExternalApiKey | None:
        return self.db.scalar(
            select(ExternalApiKey).where(ExternalApiKey.secret_hash == secret_hash)
        )

    def add(self, key: ExternalApiKey) -> ExternalApiKey:
        self.db.add(key)
        self.db.flush()
        return key

    def save(self, key: ExternalApiKey) -> ExternalApiKey:
        self.db.add(key)
        self.db.flush()
        return key


def is_key_active(key: ExternalApiKey, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    expires_at = key.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return key.status == "active" and (expires_at is None or expires_at > now)
