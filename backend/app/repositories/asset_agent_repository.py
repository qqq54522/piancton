from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.asset_agent import AssetAgentMessage, AssetAgentSession

SESSION_LOAD_OPTIONS = (selectinload(AssetAgentSession.messages),)


class AssetAgentSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: str) -> list[AssetAgentSession]:
        return list(
            self.db.scalars(
                select(AssetAgentSession)
                .where(AssetAgentSession.user_id == user_id)
                .options(*SESSION_LOAD_OPTIONS)
                .order_by(AssetAgentSession.updated_at.desc(), AssetAgentSession.id.desc())
            ).all()
        )

    def get_for_user(self, user_id: str, session_id: str) -> AssetAgentSession | None:
        return self.db.scalar(
            select(AssetAgentSession)
            .where(
                AssetAgentSession.id == session_id,
                AssetAgentSession.user_id == user_id,
            )
            .options(*SESSION_LOAD_OPTIONS)
        )

    def get(self, session_id: str) -> AssetAgentSession | None:
        return self.db.scalar(
            select(AssetAgentSession)
            .where(AssetAgentSession.id == session_id)
            .options(*SESSION_LOAD_OPTIONS)
        )

    def add(self, session: AssetAgentSession) -> AssetAgentSession:
        self.db.add(session)
        self.db.flush()
        return session

    def save(self, session: AssetAgentSession) -> None:
        self.db.add(session)
        self.db.flush()

    def delete(self, session: AssetAgentSession) -> None:
        self.db.delete(session)
        self.db.flush()

class AssetAgentMessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, message: AssetAgentMessage) -> AssetAgentMessage:
        self.db.add(message)
        self.db.flush()
        return message
