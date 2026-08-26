from fastapi import APIRouter, Depends

from app.api.dependencies import get_api_center_service, require_roles
from app.models.user import User
from app.schemas.api_center import (
    ApiCenterSummary,
    ApiCredentialCreate,
    ApiCredentialRead,
    ApiCredentialUpdate,
    ApiHealthCheckCreate,
    ApiHealthCheckRead,
    ApiHealthCheckRunRequest,
    ApiHealthCheckRunResult,
    RoutingSlotRead,
    RoutingSlotUpdate,
)
from app.services.api_center_service import ApiCenterService

router = APIRouter(prefix="/admin/api-center", tags=["admin"])


@router.get("/summary", response_model=ApiCenterSummary)
def api_center_summary(
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    service.initialize_runtime()
    return service.summary()


@router.post("/credentials", response_model=ApiCredentialRead)
def create_api_credential(
    payload: ApiCredentialCreate,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.create_credential(payload, actor_user_id=user.id)


@router.patch("/credentials/{credential_id}", response_model=ApiCredentialRead)
def update_api_credential(
    credential_id: str,
    payload: ApiCredentialUpdate,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.update_credential(credential_id, payload)


@router.delete("/credentials/{credential_id}", status_code=204)
def delete_api_credential(
    credential_id: str,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    service.delete_credential(credential_id)


@router.post("/credentials/{credential_id}/test", response_model=ApiHealthCheckRead)
def test_api_credential(
    credential_id: str,
    payload: ApiHealthCheckCreate,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.test_credential(credential_id, payload)


@router.post("/health-checks/run-all", response_model=ApiHealthCheckRunResult)
def run_api_health_checks(
    payload: ApiHealthCheckRunRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.run_health_checks(payload)


@router.patch("/routing-slots/{task}", response_model=RoutingSlotRead)
def update_routing_slot(
    task: str,
    payload: RoutingSlotUpdate,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.update_slot(task, payload, actor_user_id=user.id)
