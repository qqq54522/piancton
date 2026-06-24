from datetime import datetime
from typing import Any, Optional

from app.schemas.base import ApiModel


class AuditLogRead(ApiModel):
    id: str
    actor_user_id: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[str] = None
    details: dict[str, Any]
    request_id: Optional[str] = None
    created_at: datetime
