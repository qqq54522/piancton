from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_asset_identity_admin_service, require_roles
from app.models.user import User
from app.schemas.asset_identity import (
    AssetIdentityCodeListResponse,
)
from app.services.asset_identity_admin_service import AssetIdentityAdminService

router = APIRouter(prefix="/admin/identity-codes", tags=["admin"])


@router.get("", response_model=AssetIdentityCodeListResponse)
def list_identity_codes(
    q: Optional[str] = Query(default=None, max_length=200),
    code_type: str = Query(default="all", alias="codeType", pattern="^(all|asset|version)$"),
    status: str = Query(default="all", pattern="^(all|active|deleted|retired)$"),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=100),
    _: User = Depends(require_roles("admin")),
    service: AssetIdentityAdminService = Depends(get_asset_identity_admin_service),
):
    return service.list(
        keyword=q,
        code_type=code_type,
        status=status,
        page=page,
        page_size=page_size,
    )
