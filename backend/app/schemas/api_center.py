from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from app.schemas.base import ApiModel

ModelTaskName = Literal[
    "image_content_analysis",
    "search_system_routing",
    "search_intent_understanding",
    "search_proof_point_understanding",
    "search_candidate_review",
    "search_result_recommendation_reason",
    "copy_selling_point_matching",
    "asset_agent_chat",
]


class ApiCredentialCreate(ApiModel):
    label: str
    provider_type: str = "openai_compatible"
    base_url: str
    model_name: str
    api_key: str
    task_scope: list[ModelTaskName] = []
    status: Literal["active", "disabled"] = "active"
    priority: int = 100
    timeout_seconds: float = 20.0
    temperature: float = 0.2
    temperature_enabled: bool = True
    max_concurrency: int = 1
    auto_assign_enabled: bool = True


class ApiCredentialUpdate(ApiModel):
    label: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    task_scope: Optional[list[ModelTaskName]] = None
    status: Optional[Literal["active", "disabled"]] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[float] = None
    temperature: Optional[float] = None
    temperature_enabled: Optional[bool] = None
    max_concurrency: Optional[int] = None
    auto_assign_enabled: Optional[bool] = None


class ApiCredentialCapabilityRead(ApiModel):
    capability: str
    label: str
    status: Literal["ok", "failed", "unknown"] = "unknown"
    last_task: Optional[str] = None
    duration_ms: Optional[int] = None
    error_summary: Optional[str] = None
    checked_at: Optional[datetime] = None


class ApiCredentialRead(ApiModel):
    id: str
    label: str
    provider_type: str
    base_url: str
    model_name: str
    api_key_preview: str
    task_scope: list[str]
    status: str
    priority: int
    timeout_seconds: float
    temperature: float
    temperature_enabled: bool
    max_concurrency: int
    auto_assign_enabled: bool
    capability_profile: list[ApiCredentialCapabilityRead] = []
    current_concurrency: int = 0
    available_concurrency: int = 0
    capacity_status: str = "idle"
    recent_call_count: int = 0
    recent_failure_rate: float = 0.0
    recent_average_latency_ms: int = 0
    last_status: Optional[str] = None
    last_latency_ms: Optional[int] = None
    last_error: Optional[str] = None
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ApiProviderGroupRead(ApiModel):
    provider_group: str
    credential_count: int
    active_credential_count: int
    auto_assign_credential_count: int
    current_concurrency: int
    recent_call_count: int
    recent_failure_rate: float
    recent_timeout_count: int
    status: Literal["ok", "watch", "degraded"] = "ok"
    recommendation: Optional[str] = None


class RoutingSlotUpdate(ApiModel):
    label: Optional[str] = None
    primary_credential_id: Optional[str] = None
    backup_credential_ids: Optional[list[str]] = None
    excluded_credential_ids: Optional[list[str]] = None
    timeout_seconds: Optional[float] = None
    hedging_delay_ms: Optional[int] = None
    max_parallel: Optional[int] = None
    auto_select_enabled: Optional[bool] = None
    notes: Optional[str] = None


class RoutingSlotRead(ApiModel):
    id: str
    task: str
    label: str
    primary_credential_id: Optional[str] = None
    primary_credential_label: Optional[str] = None
    backup_credential_ids: list[str]
    backup_credential_labels: list[str]
    excluded_credential_ids: list[str]
    excluded_credential_labels: list[str]
    timeout_seconds: float
    hedging_delay_ms: int
    max_parallel: int
    auto_select_enabled: bool
    notes: Optional[str] = None
    updated_at: datetime


class ApiHealthCheckCreate(ApiModel):
    task: ModelTaskName = "search_result_recommendation_reason"
    timeout_seconds: Optional[float] = None


class ApiHealthCheckRead(ApiModel):
    id: str
    credential_id: str
    credential_label: Optional[str] = None
    task: str
    status: str
    duration_ms: int
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    error_severity: Optional[str] = None
    error_retryable: Optional[bool] = None
    error_operator_action: Optional[str] = None
    error_system_action: Optional[str] = None
    error_summary: Optional[str] = None
    checked_at: datetime


class ApiHealthCheckRunRequest(ApiModel):
    task: Optional[ModelTaskName] = None
    include_disabled: bool = False
    timeout_seconds: Optional[float] = None


class ApiHealthCheckRunResult(ApiModel):
    checked_count: int
    ok_count: int
    failed_count: int
    checks: list[ApiHealthCheckRead]


class ApiTemperatureProbeRead(ApiModel):
    temperature: Optional[float] = None
    temperature_enabled: bool = True
    status: str
    duration_ms: int
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    error_severity: Optional[str] = None
    error_retryable: Optional[bool] = None
    error_operator_action: Optional[str] = None
    error_system_action: Optional[str] = None
    error_summary: Optional[str] = None
    checked_at: datetime


class ApiTemperatureTuneRequest(ApiModel):
    task: Optional[ModelTaskName] = None
    candidate_temperatures: Optional[list[float]] = None
    timeout_seconds: Optional[float] = None
    persist: bool = True


class ApiTemperatureProbeRequest(ApiModel):
    base_url: str
    model_name: str
    api_key: str
    task: ModelTaskName = "search_result_recommendation_reason"
    temperature: float = 0.2
    candidate_temperatures: Optional[list[float]] = None
    timeout_seconds: Optional[float] = None


class ApiTemperatureTuneResult(ApiModel):
    credential_id: str
    credential_label: Optional[str] = None
    status: str
    previous_temperature: float
    previous_temperature_enabled: bool = True
    selected_temperature: Optional[float] = None
    selected_temperature_enabled: Optional[bool] = None
    probes: list[ApiTemperatureProbeRead]


class ApiCallTraceRead(ApiModel):
    id: str
    search_log_id: Optional[str] = None
    request_id: Optional[str] = None
    search_keyword: Optional[str] = None
    search_result_count: Optional[int] = None
    search_timed_out: Optional[bool] = None
    task: str
    layer_name: str
    credential_id: Optional[str] = None
    credential_label: Optional[str] = None
    provider: str
    model: str
    status: str
    duration_ms: int
    fallback_index: Optional[int] = None
    error_code: Optional[str] = None
    error_category: Optional[str] = None
    error_severity: Optional[str] = None
    error_retryable: Optional[bool] = None
    error_operator_action: Optional[str] = None
    error_system_action: Optional[str] = None
    error_summary: Optional[str] = None
    response_valid: Optional[bool] = None
    output_summary: dict
    created_at: datetime


class ApiCallTraceListResponse(ApiModel):
    items: list[ApiCallTraceRead]
    total: int
    limit: int
    offset: int
    has_more: bool


class ApiExternalKnowledgeServiceConfig(ApiModel):
    enabled: bool
    base_url: str
    service_resource_id: str
    api_key_configured: bool
    timeout_seconds: float
    result_limit: int
    max_matches: int


class ApiExternalVectorDatabaseConfig(ApiModel):
    enabled: bool
    fallback_enabled: bool
    base_url: str
    collection_name: str
    index_name: str
    api_key_configured: bool
    timeout_seconds: float
    search_limit: int
    primary_min_score: float
    primary_max_matches: int
    fallback_min_score: float
    fallback_max_matches: int


class ApiExternalConnectionsRead(ApiModel):
    knowledge_service: ApiExternalKnowledgeServiceConfig
    vector_database: ApiExternalVectorDatabaseConfig


class ApiExternalKnowledgeServiceUpdate(ApiModel):
    enabled: Optional[bool] = None
    base_url: Optional[str] = None
    service_resource_id: Optional[str] = None
    api_key: Optional[str] = None
    timeout_seconds: Optional[float] = None
    result_limit: Optional[int] = None
    max_matches: Optional[int] = None


class ApiExternalVectorDatabaseUpdate(ApiModel):
    enabled: Optional[bool] = None
    fallback_enabled: Optional[bool] = None
    base_url: Optional[str] = None
    collection_name: Optional[str] = None
    index_name: Optional[str] = None
    api_key: Optional[str] = None
    timeout_seconds: Optional[float] = None
    search_limit: Optional[int] = None
    primary_min_score: Optional[float] = None
    primary_max_matches: Optional[int] = None
    fallback_min_score: Optional[float] = None
    fallback_max_matches: Optional[int] = None


class ApiExternalConnectionTestRequest(ApiModel):
    query: str = "学有余力进一步提升"


class ApiExternalConnectionTestResult(ApiModel):
    status: Literal["ok", "failed", "skipped"]
    duration_ms: int
    message: str
    preview: dict = {}


class ApiCenterOverview(ApiModel):
    credential_count: int
    active_credential_count: int
    healthy_credential_count: int
    degraded_credential_count: int
    configured_slot_count: int
    recent_call_count: int
    recent_failure_count: int
    p95_latency_ms: int


class ApiCenterMaintenanceRead(ApiModel):
    enabled: bool
    interval_minutes: int
    startup_delay_seconds: int
    max_credentials_per_cycle: int
    call_trace_retention_days: int
    health_check_retention_days: int
    last_started_at: Optional[datetime] = None
    last_finished_at: Optional[datetime] = None
    last_status: str = "idle"
    last_error: Optional[str] = None
    last_checked_count: int = 0
    last_ok_count: int = 0
    last_failed_count: int = 0
    last_deleted_call_trace_count: int = 0
    last_deleted_health_check_count: int = 0
    next_run_at: Optional[datetime] = None


class ApiCenterMaintenanceRunResult(ApiModel):
    status: str
    started_at: datetime
    finished_at: datetime
    checked_count: int
    ok_count: int
    failed_count: int
    deleted_call_trace_count: int
    deleted_health_check_count: int


class ApiCenterSummary(ApiModel):
    overview: ApiCenterOverview
    maintenance: ApiCenterMaintenanceRead
    external_connections: ApiExternalConnectionsRead
    credentials: list[ApiCredentialRead]
    provider_groups: list[ApiProviderGroupRead] = []
    routing_slots: list[RoutingSlotRead]
    recent_call_traces: list[ApiCallTraceRead]
