from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import (
    get_api_center_service,
    get_audit_service,
    get_search_service,
    require_roles,
)
from app.models.user import User
from app.schemas.api_center import (
    ApiCallTraceListResponse,
    ApiCenterMaintenanceRunResult,
    ApiCenterSummary,
    ApiCredentialCreate,
    ApiCredentialRead,
    ApiCredentialUpdate,
    ApiExternalConnectionTestRequest,
    ApiExternalConnectionTestResult,
    ApiExternalKnowledgeServiceConfig,
    ApiExternalKnowledgeServiceUpdate,
    ApiExternalVectorDatabaseConfig,
    ApiExternalVectorDatabaseUpdate,
    ApiHealthCheckCreate,
    ApiHealthCheckRead,
    ApiHealthCheckRunRequest,
    ApiHealthCheckRunResult,
    ApiProviderGroupRead,
    ApiSearchChainDiagnosticRequest,
    ApiSearchChainDiagnosticResult,
    ApiSearchChainDiagnosticStep,
    ApiTemperatureProbeRequest,
    ApiTemperatureTuneRequest,
    ApiTemperatureTuneResult,
    RoutingSlotRead,
    RoutingSlotUpdate,
)
from app.services.api_center_service import ApiCenterService
from app.services.audit_service import AuditService
from app.services.search_service import SearchService

router = APIRouter(prefix="/admin/api-center", tags=["admin"])


@router.get("/summary", response_model=ApiCenterSummary)
def api_center_summary(
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    service.initialize_runtime()
    return service.summary()


@router.get("/call-traces", response_model=ApiCallTraceListResponse)
def list_api_call_traces(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    task: str | None = Query(None, max_length=80),
    status: str | None = Query(None, max_length=24),
    provider: str | None = Query(None, max_length=120),
    credential_id: str | None = Query(None, max_length=36),
    request_id: str | None = Query(None, max_length=64),
    keyword: str | None = Query(None, max_length=120),
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    service.initialize_runtime()
    return service.list_call_traces(
        limit=limit,
        offset=offset,
        task=task,
        status=status,
        provider=provider,
        credential_id=credential_id,
        request_id=request_id,
        keyword=keyword,
    )


@router.post("/credentials", response_model=ApiCredentialRead)
def create_api_credential(
    payload: ApiCredentialCreate,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    credential = service.create_credential(
        payload,
        actor_user_id=user.id,
        require_probe=True,
    )
    audit.record(
        actor_user_id=user.id,
        action="api_center.credential.create",
        target_type="model_api_credential",
        target_id=credential.id,
        details=service.credential_create_audit_details(credential),
        request_id=request.state.request_id,
    )
    return credential


@router.post("/credentials/temperature-probe", response_model=ApiTemperatureTuneResult)
def probe_api_credential_temperature(
    payload: ApiTemperatureProbeRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.probe_credential_temperature(payload)


@router.patch("/credentials/{credential_id}", response_model=ApiCredentialRead)
def update_api_credential(
    credential_id: str,
    payload: ApiCredentialUpdate,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    before = service.credential_audit_snapshot(credential_id)
    credential = service.update_credential(
        credential_id,
        payload,
        require_probe=True,
    )
    audit.record(
        actor_user_id=user.id,
        action="api_center.credential.update",
        target_type="model_api_credential",
        target_id=credential.id,
        details=service.credential_update_audit_details(
            before,
            credential,
            api_key_changed=bool(payload.api_key and payload.api_key.strip()),
        ),
        request_id=request.state.request_id,
    )
    return credential


@router.delete("/credentials/{credential_id}", status_code=204)
def delete_api_credential(
    credential_id: str,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    before = service.credential_audit_snapshot(credential_id)
    service.delete_credential(credential_id)
    audit.record(
        actor_user_id=user.id,
        action="api_center.credential.delete",
        target_type="model_api_credential",
        target_id=credential_id,
        details=before or {},
        request_id=request.state.request_id,
    )


@router.post("/provider-groups/{provider_group}/disable", response_model=ApiProviderGroupRead)
def disable_api_provider_group(
    provider_group: str,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    before = service.provider_group_audit_snapshot(provider_group)
    group = service.disable_provider_group(provider_group, actor_user_id=user.id)
    audit.record(
        actor_user_id=user.id,
        action="api_center.provider_group.disable",
        target_type="api_provider_group",
        target_id=provider_group,
        details={
            "providerGroup": provider_group,
            "affectedCredentialIds": [credential["id"] for credential in before],
            "affectedCredentialLabels": [credential["label"] for credential in before],
            "activeCredentialCountBefore": sum(
                1 for credential in before if credential["status"] == "active"
            ),
            "activeCredentialCountAfter": group.active_credential_count,
        },
        request_id=request.state.request_id,
    )
    return group


@router.post("/credentials/{credential_id}/test", response_model=ApiHealthCheckRead)
def test_api_credential(
    credential_id: str,
    payload: ApiHealthCheckCreate,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.test_credential(credential_id, payload)


@router.post(
    "/credentials/{credential_id}/temperature-tune",
    response_model=ApiTemperatureTuneResult,
)
def tune_api_credential_temperature(
    credential_id: str,
    payload: ApiTemperatureTuneRequest,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    before = service.credential_audit_snapshot(credential_id)
    result = service.tune_credential_temperature(credential_id, payload)
    after = service.repo.get_credential(credential_id)
    if payload.persist and result.status == "ok" and after is not None:
        audit.record(
            actor_user_id=user.id,
            action="api_center.credential.temperature_tune",
            target_type="model_api_credential",
            target_id=credential_id,
            details={
                "changedFields": ["temperature", "temperatureEnabled"],
                "before": {
                    "temperature": before.get("temperature") if before else None,
                    "temperatureEnabled": before.get("temperatureEnabled") if before else None,
                },
                "after": {
                    "temperature": after.temperature,
                    "temperatureEnabled": after.temperature_enabled,
                },
            },
            request_id=request.state.request_id,
        )
    return result


@router.post("/health-checks/run-all", response_model=ApiHealthCheckRunResult)
def run_api_health_checks(
    payload: ApiHealthCheckRunRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.run_health_checks(payload)


@router.post("/maintenance/run", response_model=ApiCenterMaintenanceRunResult)
def run_api_center_maintenance(
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.run_maintenance_cycle(only_due=False)


@router.patch("/routing-slots/{task}", response_model=RoutingSlotRead)
def update_routing_slot(
    task: str,
    payload: RoutingSlotUpdate,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.update_slot(task, payload, actor_user_id=user.id)


@router.patch(
    "/external-connections/knowledge-service",
    response_model=ApiExternalKnowledgeServiceConfig,
)
def update_external_knowledge_service(
    payload: ApiExternalKnowledgeServiceUpdate,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    config = service.update_external_knowledge_service(payload)
    changed_fields = [
        field
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None and field != "api_key"
    ]
    if payload.api_key and payload.api_key.strip():
        changed_fields.append("api_key")
    audit.record(
        actor_user_id=user.id,
        action="api_center.external.knowledge_service.update",
        target_type="api_external_connection",
        target_id="knowledge-service",
        details={
            "changedFields": changed_fields,
            "apiKeyChanged": bool(payload.api_key and payload.api_key.strip()),
        },
        request_id=request.state.request_id,
    )
    return config


@router.patch(
    "/external-connections/vector-database",
    response_model=ApiExternalVectorDatabaseConfig,
)
def update_external_vector_database(
    payload: ApiExternalVectorDatabaseUpdate,
    request: Request,
    user: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    audit: AuditService = Depends(get_audit_service),
):
    config = service.update_external_vector_database(payload)
    changed_fields = [
        field
        for field, value in payload.model_dump(exclude_unset=True).items()
        if value is not None and field != "api_key"
    ]
    if payload.api_key and payload.api_key.strip():
        changed_fields.append("api_key")
    audit.record(
        actor_user_id=user.id,
        action="api_center.external.vector_database.update",
        target_type="api_external_connection",
        target_id="vector-database",
        details={
            "changedFields": changed_fields,
            "apiKeyChanged": bool(payload.api_key and payload.api_key.strip()),
        },
        request_id=request.state.request_id,
    )
    return config


@router.post(
    "/external-connections/knowledge-service/test",
    response_model=ApiExternalConnectionTestResult,
)
def test_external_knowledge_service(
    payload: ApiExternalConnectionTestRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.test_external_knowledge_service(payload)


@router.post(
    "/external-connections/vector-database/test",
    response_model=ApiExternalConnectionTestResult,
)
def test_external_vector_database(
    payload: ApiExternalConnectionTestRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
):
    return service.test_external_vector_database(payload)


@router.post(
    "/external-connections/search-chain/diagnose",
    response_model=ApiSearchChainDiagnosticResult,
)
async def diagnose_external_search_chain(
    payload: ApiSearchChainDiagnosticRequest,
    _: User = Depends(require_roles("admin")),
    service: ApiCenterService = Depends(get_api_center_service),
    search_service: SearchService = Depends(get_search_service),
):
    query = payload.query.strip() or "洋葱拍题精学习"
    started = time.monotonic()
    steps: list[ApiSearchChainDiagnosticStep] = []

    external = service.external_connections()
    knowledge_ready = (
        external.knowledge_service.enabled
        and external.knowledge_service.api_key_configured
        and bool(external.knowledge_service.base_url.strip())
        and bool(external.knowledge_service.service_resource_id.strip())
    )
    vector_ready = (
        external.vector_database.enabled
        and external.vector_database.fallback_enabled
        and external.vector_database.api_key_configured
        and bool(external.vector_database.base_url.strip())
        and bool(external.vector_database.collection_name.strip())
        and bool(external.vector_database.index_name.strip())
    )
    config_ok = knowledge_ready and vector_ready
    steps.append(
        ApiSearchChainDiagnosticStep(
            name="配置读取",
            status="ok" if config_ok else "failed",
            message=(
                "API 中心已配置知识库主判断与 VikingDB fallback"
                if config_ok
                else "API 中心外部连接配置不完整"
            ),
            preview={
                "knowledgeEnabled": external.knowledge_service.enabled,
                "knowledgeApiKeyConfigured": external.knowledge_service.api_key_configured,
                "knowledgeServiceResourceId": external.knowledge_service.service_resource_id,
                "vectorEnabled": external.vector_database.enabled,
                "vectorFallbackEnabled": external.vector_database.fallback_enabled,
                "vectorApiKeyConfigured": external.vector_database.api_key_configured,
                "vectorCollectionName": external.vector_database.collection_name,
                "vectorIndexName": external.vector_database.index_name,
                "vectorFallbackMinScore": external.vector_database.fallback_min_score,
                "vectorFallbackMaxMatches": external.vector_database.fallback_max_matches,
            },
        )
    )

    knowledge_result = service.test_external_knowledge_service(
        ApiExternalConnectionTestRequest(query=query)
    )
    steps.append(
        ApiSearchChainDiagnosticStep(
            name="知识库服务",
            status=knowledge_result.status,
            duration_ms=knowledge_result.duration_ms,
            message=knowledge_result.message,
            preview=knowledge_result.preview,
        )
    )

    vector_result = service.test_external_vector_database(
        ApiExternalConnectionTestRequest(query=query)
    )
    steps.append(
        ApiSearchChainDiagnosticStep(
            name="VikingDB 向量库",
            status=vector_result.status,
            duration_ms=vector_result.duration_ms,
            message=vector_result.message,
            preview=vector_result.preview,
        )
    )

    search_step_started = time.monotonic()
    try:
        search_response = await search_service.search_async(query, 12)
    except Exception as exc:
        steps.append(
            ApiSearchChainDiagnosticStep(
                name="完整搜索链路",
                status="failed",
                duration_ms=_elapsed_ms(search_step_started),
                message=str(exc)[:160] or exc.__class__.__name__,
            )
        )
        return ApiSearchChainDiagnosticResult(
            status="failed",
            query=query,
            duration_ms=_elapsed_ms(started),
            steps=steps,
        )

    matched_concepts = (
        [
            item.concept
            for item in search_response.search_understanding.matched_business_concepts
        ]
        if search_response.search_understanding
        else []
    )
    search_ok = bool(matched_concepts)
    steps.append(
        ApiSearchChainDiagnosticStep(
            name="完整搜索链路",
            status="ok" if search_ok else "failed",
            duration_ms=_elapsed_ms(search_step_started),
            message=(
                "搜索已产出卖点并回本地图库取素材"
                if search_ok
                else "搜索未产出可靠卖点"
            ),
            preview={
                "matchedConcepts": matched_concepts,
                "resultCount": len(search_response.results),
                "fallback": search_response.fallback,
                "fallbackReason": search_response.fallback_reason,
                "matchSummary": search_response.match_summary,
                "branches": [
                    {
                        "source": branch.source,
                        "status": branch.status,
                        "durationMs": branch.duration_ms,
                        "resultCount": branch.result_count,
                        "detail": branch.detail,
                    }
                    for branch in (
                        search_response.search_diagnostics.branches
                        if search_response.search_diagnostics
                        else []
                    )
                ],
            },
        )
    )
    overall_status = "ok" if search_ok and all(
        step.status == "ok" for step in steps
    ) else "degraded" if search_ok else "failed"
    return ApiSearchChainDiagnosticResult(
        status=overall_status,
        query=query,
        duration_ms=_elapsed_ms(started),
        steps=steps,
        matched_concepts=matched_concepts,
        result_count=len(search_response.results),
        fallback=search_response.fallback,
        fallback_reason=search_response.fallback_reason,
    )


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
