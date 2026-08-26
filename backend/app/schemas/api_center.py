from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from app.schemas.base import ApiModel

ModelTaskName = Literal[
    "image_content_analysis",
    "asset_search_phrase_generation",
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
    status: Literal["active", "disabled", "cooling", "invalid"] = "active"
    priority: int = 100
    timeout_seconds: float = 20.0
    temperature: float = 0.2
    max_concurrency: int = 1
    auto_assign_enabled: bool = True


class ApiCredentialUpdate(ApiModel):
    label: Optional[str] = None
    provider_type: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    task_scope: Optional[list[ModelTaskName]] = None
    status: Optional[Literal["active", "disabled", "cooling", "invalid"]] = None
    priority: Optional[int] = None
    timeout_seconds: Optional[float] = None
    temperature: Optional[float] = None
    max_concurrency: Optional[int] = None
    auto_assign_enabled: Optional[bool] = None


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
    max_concurrency: int
    auto_assign_enabled: bool
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


class RoutingSlotUpdate(ApiModel):
    label: Optional[str] = None
    primary_credential_id: Optional[str] = None
    backup_credential_ids: Optional[list[str]] = None
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
    timeout_seconds: float
    hedging_delay_ms: int
    max_parallel: int
    auto_select_enabled: bool
    notes: Optional[str] = None
    updated_at: datetime


class ApiHealthCheckCreate(ApiModel):
    task: ModelTaskName = "search_system_routing"
    timeout_seconds: Optional[float] = None


class ApiHealthCheckRead(ApiModel):
    id: str
    credential_id: str
    credential_label: Optional[str] = None
    task: str
    status: str
    duration_ms: int
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


class ApiCallTraceRead(ApiModel):
    id: str
    search_log_id: Optional[str] = None
    request_id: Optional[str] = None
    task: str
    layer_name: str
    credential_id: Optional[str] = None
    credential_label: Optional[str] = None
    provider: str
    model: str
    status: str
    duration_ms: int
    fallback_index: Optional[int] = None
    error_summary: Optional[str] = None
    response_valid: Optional[bool] = None
    output_summary: dict
    created_at: datetime


class ApiCenterOverview(ApiModel):
    credential_count: int
    active_credential_count: int
    healthy_credential_count: int
    degraded_credential_count: int
    configured_slot_count: int
    recent_call_count: int
    recent_failure_count: int
    p95_latency_ms: int


class ApiCenterSummary(ApiModel):
    overview: ApiCenterOverview
    credentials: list[ApiCredentialRead]
    routing_slots: list[RoutingSlotRead]
    recent_call_traces: list[ApiCallTraceRead]
