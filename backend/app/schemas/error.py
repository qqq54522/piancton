from __future__ import annotations

from typing import Any

from app.schemas.base import ApiModel


class ErrorResponse(ApiModel):
    code: str
    message: str
    details: Any | None = None
