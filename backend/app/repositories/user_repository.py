from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.models.user import AuditLog, LoginThrottle, User, UserSession


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.created_at)).all())

    def get(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class SessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, session: UserSession) -> UserSession:
        self.db.add(session)
        self.db.flush()
        return session

    def get_valid(self, token_hash: str) -> UserSession | None:
        now = datetime.now(timezone.utc)
        return self.db.scalar(
            select(UserSession)
            .where(
                UserSession.token_hash == token_hash,
                UserSession.expires_at > now,
            )
            .options(selectinload(UserSession.user))
        )

    def delete_by_token(self, token_hash: str) -> None:
        self.db.execute(delete(UserSession).where(UserSession.token_hash == token_hash))

    def delete_for_user(self, user_id: str) -> None:
        self.db.execute(delete(UserSession).where(UserSession.user_id == user_id))

    def delete_expired(self) -> None:
        self.db.execute(
            delete(UserSession).where(UserSession.expires_at <= datetime.now(timezone.utc))
        )


class LoginThrottleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, key: str) -> LoginThrottle | None:
        return self.db.get(LoginThrottle, key)

    def save(self, throttle: LoginThrottle) -> None:
        self.db.add(throttle)
        self.db.flush()

    def delete(self, throttle: LoginThrottle) -> None:
        self.db.delete(throttle)
        self.db.flush()


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, entry: AuditLog) -> None:
        self.db.add(entry)
        self.db.flush()

    def list_recent(self, limit: int = 100) -> list[AuditLog]:
        return list(
            self.db.scalars(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
            ).all()
        )
