import json
from typing import Optional

from app.models.user import AuditLog
from app.repositories.user_repository import AuditLogRepository
from app.schemas.audit import AuditLogRead
from app.services.unit_of_work import UnitOfWork


class AuditService:
    def __init__(self, db):
        self.logs = AuditLogRepository(db)
        self.uow = UnitOfWork(db)

    def record(
        self,
        *,
        actor_user_id: Optional[str],
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[dict] = None,
        request_id: Optional[str] = None,
    ) -> None:
        self.logs.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=target_id,
                details_json=json.dumps(details or {}, ensure_ascii=False),
                request_id=request_id,
            )
        )
        self.uow.commit()

    def list_recent(self, limit: int = 100) -> list[AuditLogRead]:
        return [
            AuditLogRead(
                id=entry.id,
                actor_user_id=entry.actor_user_id,
                action=entry.action,
                target_type=entry.target_type,
                target_id=entry.target_id,
                details=json.loads(entry.details_json),
                request_id=entry.request_id,
                created_at=entry.created_at,
            )
            for entry in self.logs.list_recent(limit)
        ]
