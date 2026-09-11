import json
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from typing import Optional

import pytest

from app.ai.contracts import (
    CancellationSignal,
    ModelCallResult,
    ModelProviderCancelled,
    ModelProviderError,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.models import (
    ModelApiCredential,
    ModelApiHealthCheck,
    ModelCallTrace,
    ModelRoutingSlot,
)
from app.models.search_log import SearchLog
from app.schemas.api_center import (
    ApiCredentialCreate,
    ApiCredentialUpdate,
    ApiTemperatureProbeRequest,
    ApiTemperatureTuneRequest,
    RoutingSlotUpdate,
)
from app.schemas.image import SearchResponse
from app.services import api_center_service
from app.services.api_center_service import ApiCenterService
from app.services.search_log_service import SearchLogService
from tests.conftest import login


def _empty_provider_settings():
    return SimpleNamespace(
        model_base_url="",
        model_name="",
        model_api_key="",
        model_temperature=0.2,
        search_fallback_base_url="",
        search_fallback_model_name="",
        search_fallback_api_key="",
        search_fallback_temperature=0.2,
        image_analysis_base_url="",
        image_analysis_model_name="",
        image_analysis_api_key="",
        image_analysis_temperature=0.2,
        asset_phrase_base_url="",
        asset_phrase_model_name="",
        asset_phrase_api_key="",
        asset_phrase_temperature=0.2,
        api_center_maintenance_enabled=False,
        api_center_maintenance_interval_minutes=360,
        api_center_maintenance_startup_delay_seconds=300,
        api_center_maintenance_max_credentials_per_cycle=20,
        api_center_call_trace_retention_days=30,
        api_center_health_check_retention_days=90,
    )


@pytest.fixture(autouse=True)
def no_environment_provider_import(monkeypatch):
    api_center_service._CAPACITY_TRACKER.reset_for_tests()
    api_center_service._SCHEDULE_METRICS_CACHE.reset_for_tests()
    monkeypatch.setattr(api_center_service, "get_settings", _empty_provider_settings)

    def fake_generate_json(self, request):
        return ModelCallResult(
            {"ok": True},
            (
                {
                    "provider": self.base_url.rstrip("/").split("//")[-1].split("/")[0],
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 10,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )
    yield
    api_center_service._CAPACITY_TRACKER.reset_for_tests()
    api_center_service._SCHEDULE_METRICS_CACHE.reset_for_tests()


def admin_headers(client) -> dict[str, str]:
    csrf = login(client, "admin", "admin-password")
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def test_admin_api_center_summary_initializes_default_slots(client):
    headers = admin_headers(client)

    response = client.get("/api/admin/api-center/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    tasks = {item["task"] for item in payload["routingSlots"]}
    assert tasks == {
        "search_result_recommendation_reason",
        "asset_agent_chat",
    }
    assert payload["overview"]["credentialCount"] == 0


def test_api_center_is_admin_only(client):
    csrf = login(client, "designer", "designer-password")

    response = client.get(
        "/api/admin/api-center/summary",
        headers={"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"},
    )

    assert response.status_code == 403


def test_create_credential_masks_key_and_can_be_disabled(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "老张-搜索A",
            "providerType": "openai_compatible",
            "baseUrl": "https://api.example.com/v1",
            "modelName": "gpt-test",
            "apiKey": "sk-secret-value-1234",
            "taskScope": ["search_result_recommendation_reason"],
            "maxConcurrency": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "老张-搜索A"
    assert payload["apiKeyPreview"] == "sk-****1234"
    assert payload["maxConcurrency"] == 3
    assert payload["currentConcurrency"] == 0
    assert payload["availableConcurrency"] == 3
    capability_status = {
        item["capability"]: item["status"]
        for item in payload["capabilityProfile"]
    }
    assert capability_status == {
        "text_json": "ok",
        "vision_json": "unknown",
    }
    assert "apiKey" not in payload

    disable = client.patch(
        f"/api/admin/api-center/credentials/{payload['id']}",
        headers=headers,
        json={"status": "disabled"},
    )
    assert disable.status_code == 200
    assert disable.json()["status"] == "disabled"


def test_duplicate_credential_is_rejected_without_blocking_allowed_variants(client):
    headers = admin_headers(client)

    first = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "重复防护 A",
            "providerType": "openai_compatible",
            "baseUrl": "https://duplicate.example.test/v1/chat/completions",
            "modelName": "gpt-dup",
            "apiKey": "sk-duplicate-secret-1234",
        },
    )
    duplicate = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "重复防护 B",
            "providerType": "openai_compatible",
            "baseUrl": "https://duplicate.example.test/v1/",
            "modelName": "gpt-dup",
            "apiKey": "sk-duplicate-secret-1234",
        },
    )
    same_key_different_model = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "同 Key 不同模型",
            "providerType": "openai_compatible",
            "baseUrl": "https://duplicate.example.test/v1",
            "modelName": "gpt-other",
            "apiKey": "sk-duplicate-secret-1234",
        },
    )
    same_model_different_key = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "同模型不同 Key",
            "providerType": "openai_compatible",
            "baseUrl": "https://duplicate.example.test/v1",
            "modelName": "gpt-dup",
            "apiKey": "sk-another-secret-1234",
        },
    )

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert "api_credential_duplicate" in duplicate.text
    assert same_key_different_model.status_code == 200
    assert same_model_different_key.status_code == 200


def test_update_credential_rejects_duplicate_inventory_identity(client):
    headers = admin_headers(client)
    first = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "目标库存",
            "baseUrl": "https://update-duplicate.example.test/v1",
            "modelName": "gpt-target",
            "apiKey": "sk-target-secret-1234",
        },
    ).json()
    second = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "待修改库存",
            "baseUrl": "https://update-duplicate.example.test/v1",
            "modelName": "gpt-other",
            "apiKey": "sk-other-secret-1234",
        },
    ).json()

    response = client.patch(
        f"/api/admin/api-center/credentials/{second['id']}",
        headers=headers,
        json={
            "modelName": "gpt-target",
            "apiKey": "sk-target-secret-1234",
        },
    )
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    persisted_second = next(
        item for item in summary["credentials"] if item["id"] == second["id"]
    )

    assert first["id"] != second["id"]
    assert response.status_code == 409
    assert "api_credential_duplicate" in response.text
    assert persisted_second["modelName"] == "gpt-other"


def test_api_credential_lifecycle_writes_safe_audit_logs(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "审计 API",
            "baseUrl": "https://audit.example.test/v1",
            "modelName": "gpt-audit",
            "apiKey": "sk-audit-secret-1234",
        },
    ).json()
    client.patch(
        f"/api/admin/api-center/credentials/{created['id']}",
        headers=headers,
        json={"status": "disabled", "autoAssignEnabled": False},
    )
    client.delete(
        f"/api/admin/api-center/credentials/{created['id']}",
        headers=headers,
    )

    logs = client.get("/api/admin/users/audit-logs", headers=headers).json()
    api_logs = [
        item
        for item in logs
        if item["action"].startswith("api_center.credential.")
        and item["targetId"] == created["id"]
    ]
    actions = {item["action"] for item in api_logs}
    serialized_details = json.dumps(
        [item["details"] for item in api_logs],
        ensure_ascii=False,
    )

    assert {
        "api_center.credential.create",
        "api_center.credential.update",
        "api_center.credential.delete",
    }.issubset(actions)
    assert "sk-audit-secret-1234" not in serialized_details
    assert "apiKeyPreview" not in serialized_details
    update_log = next(
        item for item in api_logs
        if item["action"] == "api_center.credential.update"
    )
    assert set(update_log["details"]["changedFields"]) >= {
        "status",
        "autoAssignEnabled",
    }


def test_current_search_explanation_probe_uses_text_json_only(client, monkeypatch):
    headers = admin_headers(client)
    seen_tasks = []

    def fake_generate_json(self, request):
        seen_tasks.append(request.task)
        assert request.image_path is None
        assert request.image_media_type is None
        return ModelCallResult(
            {"ok": True},
            (
                {
                    "provider": "api.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 10,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "命中解释模型",
            "providerType": "openai_compatible",
            "baseUrl": "https://api.example.test/v1",
            "modelName": "text-json",
            "apiKey": "sk-text-value-1234",
            "taskScope": ["search_result_recommendation_reason"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert seen_tasks == ["search_result_recommendation_reason"]
    capability_status = {
        item["capability"]: item["status"]
        for item in payload["capabilityProfile"]
    }
    assert capability_status["text_json"] == "ok"
    assert capability_status["vision_json"] == "unknown"


def test_current_tasks_do_not_require_vision_capability(client, monkeypatch):
    headers = admin_headers(client)

    def fake_generate_json(self, request):
        if request.image_path is not None:
            raise ModelProviderError(
                "该模型不支持当前任务需要的图片输入",
                code="task_capability_unsupported",
            )
        return ModelCallResult(
            {"ok": True},
            (
                {
                    "provider": "api.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 10,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    create = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "文本模型",
            "providerType": "openai_compatible",
            "baseUrl": "https://api.example.test/v1",
            "modelName": "text-only",
            "apiKey": "sk-text-value-1234",
            "taskScope": ["search_result_recommendation_reason"],
        },
    )
    assert create.status_code == 200

    test = client.post(
        f"/api/admin/api-center/credentials/{create.json()['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason"},
    )

    assert test.status_code == 200
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    credential = summary["credentials"][0]
    capability_status = {
        item["capability"]: item["status"]
        for item in credential["capabilityProfile"]
    }
    assert test.json()["status"] == "ok"
    assert capability_status["text_json"] == "ok"
    assert capability_status["vision_json"] == "unknown"


def test_create_credential_rejects_api_that_fails_backend_probe(client, monkeypatch):
    headers = admin_headers(client)

    def fake_generate_json(self, request):
        raise ModelProviderError(
            "API 密钥无效或无权访问该模型",
            code="authentication_failed",
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "错误 Key",
            "providerType": "openai_compatible",
            "baseUrl": "https://api.invalid-key.test/v1",
            "modelName": "gpt-test",
            "apiKey": "sk-invalid-value-1234",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "authentication_failed"
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    assert summary["credentials"] == []


def test_create_credential_normalizes_chat_completions_url(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "完整端点 Key",
            "providerType": "openai_compatible",
            "baseUrl": "https://api.endpoint.test/v1/chat/completions",
            "modelName": "gpt-test",
            "apiKey": "sk-endpoint-value-1234",
        },
    )

    assert response.status_code == 200
    assert response.json()["baseUrl"] == "https://api.endpoint.test/v1"


def test_create_credential_rejects_unsupported_provider_type(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "未知协议 Key",
            "providerType": "unknown_provider",
            "baseUrl": "https://api.unknown.test/v1",
            "modelName": "gpt-test",
            "apiKey": "sk-unknown-value-1234",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_provider_type"


def test_update_credential_rejects_failed_probe_and_keeps_previous_values(
    client,
    monkeypatch,
):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "原始 Key",
            "baseUrl": "https://api.original.test/v1",
            "modelName": "gpt-original",
            "apiKey": "sk-original-value-1234",
        },
    ).json()

    def fake_generate_json(self, request):
        raise ModelProviderError("模型不存在或无权调用", code="model_not_found")

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.patch(
        f"/api/admin/api-center/credentials/{created['id']}",
        headers=headers,
        json={
            "baseUrl": "https://api.changed.test/v1",
            "modelName": "missing-model",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "model_not_found"
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    persisted = summary["credentials"][0]
    assert persisted["baseUrl"] == "https://api.original.test/v1"
    assert persisted["modelName"] == "gpt-original"


def test_delete_credential_removes_routing_references(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "删除测试 Key",
            "baseUrl": "https://api.delete.test/v1",
            "modelName": "gpt-delete",
            "apiKey": "sk-delete-value-1234",
            "taskScope": ["search_result_recommendation_reason"],
        },
    ).json()
    slot = client.patch(
        "/api/admin/api-center/routing-slots/search_result_recommendation_reason",
        headers=headers,
        json={
            "primaryCredentialId": created["id"],
            "backupCredentialIds": [created["id"]],
            "autoSelectEnabled": False,
        },
    )
    assert slot.status_code == 200

    response = client.delete(
        f"/api/admin/api-center/credentials/{created['id']}",
        headers=headers,
    )

    assert response.status_code == 204
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    assert summary["credentials"] == []
    routing = next(
        item
        for item in summary["routingSlots"]
        if item["task"] == "search_result_recommendation_reason"
    )
    assert routing["primaryCredentialId"] is None
    assert routing["backupCredentialIds"] == []


def test_routing_slot_rejects_credential_outside_task_scope(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Agent Only",
            "baseUrl": "https://api.agent-only.test/v1",
            "modelName": "gpt-agent",
            "apiKey": "sk-agent-only-1234",
            "taskScope": ["asset_agent_chat"],
        },
    ).json()

    response = client.patch(
        "/api/admin/api-center/routing-slots/search_result_recommendation_reason",
        headers=headers,
        json={
            "primaryCredentialId": created["id"],
            "autoSelectEnabled": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "credential_task_scope_mismatch"


def test_auto_routing_filters_credentials_outside_task_scope(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        included = service.create_credential(
            ApiCredentialCreate(
                label="命中解释专用",
                base_url="https://search-explain.example.test/v1",
                model_name="gpt-search-explain",
                api_key="sk-search-explain-1234",
                task_scope=["search_result_recommendation_reason"],
            ),
            actor_user_id="admin",
        )
        service.create_credential(
            ApiCredentialCreate(
                label="Agent 专用",
                base_url="https://agent-only.example.test/v1",
                model_name="gpt-agent-only",
                api_key="sk-agent-only-1234",
                task_scope=["asset_agent_chat"],
            ),
            actor_user_id="admin",
        )
        _, selected = service.select_credentials_for_task(
            "search_result_recommendation_reason",
        )

    assert [item.id for item in selected] == [included.id]


def test_routing_slot_rejects_disabled_manual_credential(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Disabled Manual API",
            "baseUrl": "https://api.disabled.test/v1",
            "modelName": "gpt-disabled",
            "apiKey": "sk-disabled-1234",
            "status": "disabled",
        },
    ).json()

    response = client.patch(
        "/api/admin/api-center/routing-slots/asset_agent_chat",
        headers=headers,
        json={
            "primaryCredentialId": created["id"],
            "autoSelectEnabled": False,
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "credential_not_active"


def test_health_check_updates_credential_status(client, monkeypatch):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "OpenAI-健康测试",
            "baseUrl": "https://api.openai.test/v1",
            "modelName": "gpt-test",
            "apiKey": "sk-health-value-5678",
        },
    ).json()

    def fake_generate_json(self, request):
        attempts = (
            {
                "provider": "api.openai.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 12,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        f"/api/admin/api-center/credentials/{created['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    assert summary["credentials"][0]["lastStatus"] == "ok"
    assert "recentHealthChecks" not in summary
    health_traces = [
        item
        for item in summary["recentCallTraces"]
        if item["outputSummary"].get("kind") == "health_check"
    ]
    assert len(health_traces) == 1
    assert health_traces[0]["task"] == "search_result_recommendation_reason"
    assert health_traces[0]["layerName"] == "健康检查"
    assert health_traces[0]["credentialLabel"] == "OpenAI-健康测试"


def test_health_check_rejects_credential_outside_task_scope(client):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "旧图片分析 Key",
            "baseUrl": "https://api.legacy-image.test/v1",
            "modelName": "gpt-legacy-image",
            "apiKey": "sk-legacy-image-1234",
            "taskScope": ["asset_agent_chat"],
        },
    ).json()

    response = client.post(
        f"/api/admin/api-center/credentials/{created['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "credential_task_scope_mismatch"


def test_create_credential_rejects_retired_task_scope(client):
    headers = admin_headers(client)

    response = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "旧图片分析 Key",
            "baseUrl": "https://api.legacy-image.test/v1",
            "modelName": "gpt-legacy-image",
            "apiKey": "sk-legacy-image-1234",
            "taskScope": ["image_content_analysis"],
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "model_task_retired"


def test_health_check_uses_system_window_and_auto_expands_runtime_limit(
    client,
    monkeypatch,
):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "慢速但可用 API",
            "baseUrl": "https://api.slow.test/v1",
            "modelName": "gpt-slow",
            "apiKey": "sk-slow-health-1234",
            "timeoutSeconds": 20,
        },
    ).json()
    seen_provider_timeouts: list[int] = []
    seen_request_timeouts: list[Optional[float]] = []

    def fake_generate_json(self, request):
        seen_provider_timeouts.append(self.timeout_seconds)
        seen_request_timeouts.append(request.timeout_seconds)
        return ModelCallResult({"ok": True}, ())

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )
    monkeypatch.setattr(api_center_service, "_elapsed_ms", lambda _started: 22_000)

    response = client.post(
        f"/api/admin/api-center/credentials/{created['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason", "timeoutSeconds": 1},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert seen_provider_timeouts == [60]
    assert seen_request_timeouts == [60.0]
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    assert summary["credentials"][0]["timeoutSeconds"] == 54


def test_health_check_timeout_message_requires_no_manual_tuning(client, monkeypatch):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "等待自动复测 API",
            "baseUrl": "https://api.retry.test/v1",
            "modelName": "gpt-retry",
            "apiKey": "sk-retry-health-1234",
        },
    ).json()

    def fake_generate_json(self, request):
        raise ModelProviderError(
            "模型响应未在本次调用等待时间内完成",
            code="response_timeout",
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        f"/api/admin/api-center/credentials/{created['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "timed_out"
    assert response.json()["errorCode"] == "response_timeout"
    assert response.json()["errorCategory"] == "timeout"
    assert response.json()["errorSeverity"] == "warning"
    assert response.json()["errorRetryable"] is True
    assert "健康探测有限重试" in response.json()["errorSystemAction"]
    assert "自动任务" in response.json()["errorOperatorAction"]
    assert response.json()["errorSummary"] == (
        "健康探测自动重试后仍未收到完整响应，后续巡检会自动重试"
    )


def test_health_check_retries_transient_connection_failure(client, monkeypatch):
    headers = admin_headers(client)
    created = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "瞬时连接恢复 API",
            "baseUrl": "https://api.transient.test/v1",
            "modelName": "gpt-transient",
            "apiKey": "sk-transient-health-1234",
        },
    ).json()
    calls = 0

    def fake_generate_json(self, request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ModelProviderError(
                "无法连接模型服务，请检查 API 地址、DNS 或本机网络",
                code="connection_failed",
            )
        return ModelCallResult({"ok": True}, ())

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        f"/api/admin/api-center/credentials/{created['id']}/test",
        headers=headers,
        json={"task": "search_result_recommendation_reason"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls == 2


def test_run_all_health_checks_checks_non_disabled_keys(client, monkeypatch):
    headers = admin_headers(client)
    active = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Active Key",
            "baseUrl": "https://api.openai.test/v1",
            "modelName": "gpt-active",
            "apiKey": "sk-active-value-1111",
            "taskScope": ["search_result_recommendation_reason"],
        },
    ).json()
    client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Disabled Key",
            "baseUrl": "https://api.openai.test/v1",
            "modelName": "gpt-disabled",
            "apiKey": "sk-disabled-value-2222",
            "status": "disabled",
            "taskScope": ["search_result_recommendation_reason"],
        },
    )

    def fake_generate_json(self, request):
        attempts = (
            {
                "provider": "api.openai.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 10,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    response = client.post(
        "/api/admin/api-center/health-checks/run-all",
        headers=headers,
        json={},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["checkedCount"] == 1
    assert payload["okCount"] == 1
    assert payload["failedCount"] == 0
    assert payload["checks"][0]["credentialId"] == active["id"]


def test_admin_can_run_api_center_maintenance(client):
    headers = admin_headers(client)
    client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "维护抽检 API",
            "baseUrl": "https://maintenance.example.test/v1",
            "modelName": "gpt-maintenance",
            "apiKey": "sk-maintenance-value-1234",
            "taskScope": ["search_result_recommendation_reason"],
        },
    )

    response = client.post(
        "/api/admin/api-center/maintenance/run",
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["checkedCount"] == 1
    assert payload["okCount"] == 1
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    assert summary["maintenance"]["lastStatus"] == "ok"
    assert summary["maintenance"]["lastCheckedCount"] == 1


def test_api_center_maintenance_skips_retired_scope_credentials(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        current = service.create_credential(
            ApiCredentialCreate(
                label="当前任务 Key",
                base_url="https://maintenance-current.example.test/v1",
                model_name="gpt-current",
                api_key="sk-current-value-1234",
                task_scope=["search_result_recommendation_reason"],
            ),
            actor_user_id="admin",
        )
        service.repo.add_credential(
            ModelApiCredential(
                label="退役范围 Key",
                provider_type="openai_compatible",
                base_url="https://maintenance-retired.example.test/v1",
                model_name="gpt-retired",
                api_key_secret="sk-retired-value-1234",
                api_key_preview="sk-****1234",
                task_scope_json=json.dumps(["image_content_analysis"]),
                status="active",
                priority=100,
                timeout_seconds=20,
                temperature=0.2,
                auto_assign_enabled=True,
            )
        )
        db.commit()

        result = service.run_maintenance_cycle(
            only_due=False,
            max_credentials_per_cycle=20,
            call_trace_retention_days=30,
            health_check_retention_days=90,
        )

    assert result.checked_count == 1
    with db_factory() as db:
        checks = db.query(ModelApiHealthCheck).all()

    assert len(checks) == 1
    assert checks[0].credential_id == current.id


def test_maintenance_cycle_probes_due_credentials_and_prunes_old_logs(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        created = service.create_credential(
            ApiCredentialCreate(
                label="自动维护 API",
                base_url="https://maintenance-prune.example.test/v1",
                model_name="gpt-maintenance",
                api_key="sk-maintenance-prune-1234",
                task_scope=["search_result_recommendation_reason"],
            ),
            actor_user_id="admin",
        )
        now = datetime.now(timezone.utc)
        credential = service.repo.get_credential(created.id)
        assert credential is not None
        credential.last_checked_at = now - timedelta(days=1)
        db.add(
            ModelCallTrace(
                task="search_result_recommendation_reason",
                layer_name="旧调用链路",
                credential_id=created.id,
                credential_label="自动维护 API",
                provider="maintenance-prune.example.test",
                model="gpt-maintenance",
                status="ok",
                duration_ms=10,
                output_summary_json="{}",
                created_at=now - timedelta(days=40),
            )
        )
        db.add(
            ModelApiHealthCheck(
                credential_id=created.id,
                task="search_result_recommendation_reason",
                status="ok",
                duration_ms=10,
                checked_at=now - timedelta(days=100),
            )
        )
        db.commit()

        result = service.run_maintenance_cycle(
            interval_minutes=1,
            max_credentials_per_cycle=1,
            call_trace_retention_days=30,
            health_check_retention_days=90,
        )
        status = service.maintenance_status()

        assert result.status == "ok"
        assert result.checked_count == 1
        assert result.ok_count == 1
        assert result.deleted_call_trace_count == 1
        assert result.deleted_health_check_count == 1
        assert status.last_status == "ok"
        assert status.last_checked_count == 1
        assert db.query(ModelCallTrace).count() == 1
        assert db.query(ModelApiHealthCheck).count() == 1


def test_temperature_probe_for_unsaved_credential_does_not_persist_key(
    db_factory,
    monkeypatch,
):
    seen_temperatures: list[float] = []
    seen_timeouts: list[Optional[float]] = []

    def fake_generate_json(self, request):
        seen_temperatures.append(self.temperature)
        seen_timeouts.append(request.timeout_seconds)
        if self.temperature != 1.0:
            attempts = (
                {
                    "provider": "api.preview.test",
                    "model": self.model_name,
                    "status": "failed",
                    "duration_ms": 12,
                    "error": "Unsupported value: temperature",
                },
            )
            raise ModelProviderError("Unsupported value: temperature", attempts=attempts)
        return ModelCallResult(
            {"ok": True},
            (
                {
                    "provider": "api.preview.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 18,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        result = service.probe_credential_temperature(
            ApiTemperatureProbeRequest(
                base_url="https://api.preview.test/v1",
                model_name="gpt-preview",
                api_key="sk-preview-value-1234",
                task="search_result_recommendation_reason",
                temperature=0.2,
            )
        )
        summary = service.summary()

    assert seen_temperatures == [0.2, 1.0]
    assert seen_timeouts == [20.0, 20.0]
    assert result.status == "ok"
    assert result.selected_temperature == 1.0
    assert summary.credentials == []
    assert summary.recent_call_traces == []


def test_temperature_probe_stops_immediately_for_non_temperature_failure(
    db_factory,
    monkeypatch,
):
    calls = 0

    def fake_generate_json(self, request):
        nonlocal calls
        calls += 1
        raise ModelProviderError(
            "API 密钥无效或无权访问该模型",
            code="authentication_failed",
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        result = ApiCenterService(db).probe_credential_temperature(
            ApiTemperatureProbeRequest(
                base_url="https://api.auth.test/v1",
                model_name="gpt-auth",
                api_key="sk-invalid-value-1234",
            )
        )

    assert calls == 1
    assert result.status == "failed"
    assert result.probes[0].error_code == "authentication_failed"
    assert result.probes[0].error_summary == "API 密钥无效或无权访问该模型"


def test_temperature_probe_can_disable_unsupported_parameter(db_factory, monkeypatch):
    seen_temperatures: list[Optional[float]] = []

    def fake_generate_json(self, request):
        seen_temperatures.append(self.temperature)
        if self.temperature is not None:
            raise ModelProviderError(
                "该模型不接受 temperature 参数",
                code="temperature_not_supported",
            )
        return ModelCallResult({"ok": True}, ())

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        result = ApiCenterService(db).probe_credential_temperature(
            ApiTemperatureProbeRequest(
                base_url="https://api.no-temperature.test/v1",
                model_name="reasoning-model",
                api_key="sk-no-temperature-1234",
            )
        )

    assert seen_temperatures == [0.2, None]
    assert result.status == "ok"
    assert result.selected_temperature is None
    assert result.selected_temperature_enabled is False
    assert [probe.error_code for probe in result.probes] == [
        "temperature_not_supported",
        None,
    ]


def test_temperature_probe_rejects_invalid_base_url(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        with pytest.raises(api_center_service.AppError) as exc_info:
            service.probe_credential_temperature(
                ApiTemperatureProbeRequest(
                    base_url="api.preview.test/v1",
                    model_name="gpt-preview",
                    api_key="sk-preview-value-1234",
                    task="search_result_recommendation_reason",
                    temperature=0.2,
                )
            )

    assert exc_info.value.code == "invalid_base_url"


def test_temperature_tune_persists_first_working_temperature(db_factory, monkeypatch):
    seen_temperatures: list[float] = []

    def fake_generate_json(self, request):
        seen_temperatures.append(self.temperature)
        if self.temperature != 1.0:
            attempts = (
                {
                    "provider": "api.temperature.test",
                    "model": self.model_name,
                    "status": "failed",
                    "duration_ms": 12,
                    "error": "Unsupported value: temperature",
                },
            )
            raise ModelProviderError("Unsupported value: temperature", attempts=attempts)
        attempts = (
            {
                "provider": "api.temperature.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 18,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="温度探测 Key",
                base_url="https://api.temperature.test/v1",
                model_name="gpt-temperature",
                api_key="sk-temperature-value-1234",
                task_scope=["search_result_recommendation_reason"],
                temperature=0.2,
            ),
            actor_user_id="admin",
        )
        result = service.tune_credential_temperature(
            credential.id,
            ApiTemperatureTuneRequest(task="search_result_recommendation_reason"),
        )
        persisted = service.repo.get_credential(credential.id)
        traces = [
            item
            for item in service.summary().recent_call_traces
            if item.output_summary.get("kind") == "temperature_probe"
        ]

    assert seen_temperatures == [0.2, 1.0]
    assert result.status == "ok"
    assert result.previous_temperature == 0.2
    assert result.selected_temperature == 1.0
    assert persisted is not None
    assert persisted.temperature == 1.0
    assert persisted.status == "active"
    assert [probe.status for probe in result.probes] == ["failed", "ok"]
    assert {trace.layer_name for trace in traces} == {"温度探测"}


def test_model_call_attempts_are_recorded_as_traces(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="Trace Key",
                base_url="https://trace.example.com/v1",
                model_name="gpt-trace",
                api_key="sk-trace-value-9999",
            ),
            actor_user_id="admin",
        )
        service.record_call_traces_from_attempts(
            search_log_id=None,
            request_id="req-1",
            branches=[
                {
                    "source": "query_understanding",
                    "status": "ok",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "provider": "trace.example.com",
                            "model": "gpt-trace",
                            "status": "ok",
                            "durationMs": 234,
                            "fallbackIndex": 0,
                        }
                    ],
                }
            ],
        )
        service.uow.commit()
        summary = service.summary()

    assert summary.recent_call_traces[0].credential_id == credential.id
    assert summary.recent_call_traces[0].credential_label == "Trace Key"
    assert summary.recent_call_traces[0].duration_ms == 234


def test_model_call_trace_persists_error_code(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        service.record_call_traces_from_attempts(
            search_log_id=None,
            request_id="req-error-code",
            branches=[
                {
                    "source": "query_understanding",
                    "status": "failed",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "provider": "error-code.example.test",
                            "model": "gpt-test",
                            "status": "failed",
                            "durationMs": 345,
                            "errorCode": "upstream_unavailable",
                            "error": "模型服务调用失败",
                        }
                    ],
                }
            ],
        )
        service.uow.commit()
        trace = service.summary().recent_call_traces[0]

    assert trace.error_code == "upstream_unavailable"
    assert trace.error_category == "upstream"
    assert trace.error_retryable is True
    assert trace.error_system_action == "健康探测有限重试；运行时切换候选。"
    assert trace.error_summary == "模型服务调用失败"


def test_admin_call_trace_list_filters_and_paginates(client, db_factory):
    headers = admin_headers(client)
    with db_factory() as db:
        service = ApiCenterService(db)
        credential_a = service.create_credential(
            ApiCredentialCreate(
                label="筛选 API A",
                base_url="https://filter-a.example.test/v1",
                model_name="gpt-filter-a",
                api_key="sk-filter-a-1234",
            ),
            actor_user_id="admin",
        )
        credential_b = service.create_credential(
            ApiCredentialCreate(
                label="筛选 API B",
                base_url="https://filter-b.example.test/v1",
                model_name="gpt-filter-b",
                api_key="sk-filter-b-1234",
            ),
            actor_user_id="admin",
        )
        search_log = SearchLog(
            keyword="想找一个体现AI互动教学的卖点",
            served_mode="fuzzy",
            result_count=1,
            request_id="req-filter-trace",
        )
        db.add(search_log)
        db.commit()
        service.record_call_traces_from_attempts(
            search_log_id=search_log.id,
            request_id="req-filter-trace",
            branches=[
                {
                    "source": "search_result_recommendation_reason",
                    "status": "failed",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "credential_id": credential_a.id,
                            "provider": "filter-a.example.test",
                            "model": "gpt-filter-a",
                            "status": "failed",
                            "durationMs": 456,
                            "error_code": "connection_failed",
                            "error": "无法连接模型服务",
                        },
                        {
                            "task": "search_candidate_review",
                            "layer": "第四层：候选图片复核",
                            "credential_id": credential_b.id,
                            "provider": "filter-b.example.test",
                            "model": "gpt-filter-b",
                            "status": "ok",
                            "durationMs": 123,
                        },
                    ],
                }
            ],
            persist=True,
        )

    response = client.get(
        "/api/admin/api-center/call-traces",
        headers=headers,
        params={
            "status": "failed",
            "provider": "filter-a",
            "keyword": "AI互动教学",
            "limit": 1,
            "offset": 0,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] == 1
    assert payload["hasMore"] is False
    assert payload["items"][0]["credentialId"] == credential_a.id
    assert payload["items"][0]["errorCode"] == "connection_failed"
    assert payload["items"][0]["errorCategory"] == "connectivity"
    assert payload["items"][0]["errorSeverity"] == "warning"
    assert payload["items"][0]["errorRetryable"] is True
    assert "运行时切换候选" in payload["items"][0]["errorSystemAction"]
    assert payload["items"][0]["searchKeyword"] == "想找一个体现AI互动教学的卖点"

    empty = client.get(
        "/api/admin/api-center/call-traces",
        headers=headers,
        params={
            "status": "failed",
            "credential_id": credential_b.id,
        },
    )

    assert empty.status_code == 200
    assert empty.json()["total"] == 0


def test_runtime_trace_resolves_existing_search_by_request_id(db_factory):
    with db_factory() as db:
        db.add(
            SearchLog(
                keyword="想找一个体现AI互动教学的卖点",
                served_mode="fuzzy",
                result_count=1,
                request_id="search-request-late-trace",
            )
        )
        db.commit()
        service = ApiCenterService(db)
        service.record_call_traces_from_attempts(
            search_log_id=None,
            request_id="search-request-late-trace",
            branches=[
                {
                    "source": "query_understanding",
                    "status": "timed_out",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "provider": "example.test",
                            "model": "gpt-test",
                            "status": "timed_out",
                            "durationMs": 2500,
                            "error": "模型调用已取消",
                        }
                    ],
                }
            ],
        )
        service.uow.commit()
        trace = service.summary().recent_call_traces[0]

    assert trace.search_log_id is not None
    assert trace.request_id == "search-request-late-trace"
    assert trace.search_keyword == "想找一个体现AI互动教学的卖点"
    assert trace.search_result_count == 1
    assert trace.search_timed_out is False


def test_search_log_backfills_traces_written_before_search_finishes(db_factory):
    with db_factory() as db:
        api_center = ApiCenterService(db)
        api_center.record_call_traces_from_attempts(
            search_log_id=None,
            request_id="search-request-early-trace",
            branches=[
                {
                    "source": "query_understanding",
                    "status": "ok",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "provider": "example.test",
                            "model": "gpt-test",
                            "status": "ok",
                            "durationMs": 100,
                        }
                    ],
                }
            ],
        )
        api_center.uow.commit()

        search_log_id = SearchLogService(db).record_search(
            actor_user_id=None,
            keyword="AI互动教学",
            response=SearchResponse(results=[], match_summary="未找到结果"),
            request_id="search-request-early-trace",
        )
        trace = api_center.summary().recent_call_traces[0]

    assert trace.search_log_id == search_log_id
    assert trace.search_keyword == "AI互动教学"


def test_runtime_scheduler_writes_non_search_calls_directly_to_api_center(
    db_factory,
    monkeypatch,
):
    def fake_generate_json(self, request):
        attempts = (
            {
                "provider": "agent.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 7,
                "error": "",
            },
        )
        return ModelCallResult({"answer": "ok", "suggestedQuestions": []}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        service.create_credential(
            ApiCredentialCreate(
                label="Agent Key",
                base_url="https://agent.example.test/v1",
                model_name="gpt-agent",
                api_key="sk-agent-value-1234",
                task_scope=["asset_agent_chat"],
            ),
            actor_user_id="admin",
        )
        provider = service.build_scheduled_provider(
            default_request_id="agent-request-1"
        )
        provider.generate_json(
            ModelRequest(
                task="asset_agent_chat",
                prompt="Return JSON",
                input_text="private agent context is not logged",
                timeout_seconds=15,
            )
        )
        summary = service.summary()

    traces = [
        item
        for item in summary.recent_call_traces
        if item.task == "asset_agent_chat"
    ]
    assert len(traces) == 1
    assert traces[0].status == "ok"
    assert traces[0].search_log_id is None
    assert traces[0].request_id == "agent-request-1"
    assert traces[0].output_summary["kind"] == "runtime"
    assert "private agent context" not in str(traces[0].output_summary)


def test_scheduler_separates_task_budget_from_single_api_limit(
    db_factory,
    monkeypatch,
):
    seen_timeouts = []

    def fake_generate_json(self, request):
        seen_timeouts.append(request.timeout_seconds)
        return ModelCallResult(
            {"ok": True},
            (
                {
                    "provider": "budget.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 5,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        service.ensure_default_slots()
        service.create_credential(
            ApiCredentialCreate(
                label="预算分层 API",
                base_url="https://budget.example.test/v1",
                model_name="gpt-budget",
                api_key="sk-budget-value-1234",
                timeout_seconds=12,
            ),
            actor_user_id="admin",
        )
        provider = service.build_scheduled_provider()
        provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                timeout_seconds=1,
            )
        )

    assert seen_timeouts == [12]


def test_retired_slots_are_not_recreated_and_agent_slot_is_untouched(
    db_factory,
):
    with db_factory() as db:
        service = ApiCenterService(db)
        service.ensure_default_slots()
        image_slot = service.repo.get_slot_by_task("image_content_analysis")
        agent_slot = service.repo.get_slot_by_task("asset_agent_chat")
        assert image_slot is None
        assert agent_slot is not None

        agent_slot.timeout_seconds = 30
        agent_slot.max_parallel = 1
        db.commit()

        service.ensure_default_slots()
        db.refresh(agent_slot)

    assert agent_slot.timeout_seconds == 30
    assert agent_slot.max_parallel == 1


def test_initialize_runtime_prunes_retired_slots(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        service.repo.add_slot(
            ModelRoutingSlot(
                task="image_content_analysis",
                label="上传主图：图片语义分析",
                timeout_seconds=120,
                hedging_delay_ms=6000,
                auto_select_enabled=True,
                backup_credential_ids_json="[]",
                excluded_credential_ids_json="[]",
            )
        )
        db.commit()

        service.initialize_runtime()

        assert service.repo.get_slot_by_task("image_content_analysis") is None
        assert service.repo.get_slot_by_task("search_result_recommendation_reason")
        assert service.repo.get_slot_by_task("asset_agent_chat")


def test_retired_upload_attempt_uses_normal_credential_timeout(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="上传长任务 API",
                base_url="https://upload-budget.example.test/v1",
                model_name="gpt-upload-budget",
                api_key="sk-upload-budget-1234",
                timeout_seconds=20,
            ),
            actor_user_id="admin",
        )
        persisted = service.repo.get_credential(credential.id)
        assert persisted is not None

        upload_timeout = api_center_service._scheduled_attempt_timeout_seconds(
            persisted,
            task="image_content_analysis",
            remaining_seconds=100,
            remaining_candidate_count=0,
        )
        search_timeout = api_center_service._scheduled_attempt_timeout_seconds(
            persisted,
            task="search_result_recommendation_reason",
            remaining_seconds=100,
            remaining_candidate_count=0,
        )

    assert upload_timeout == 20
    assert search_timeout == 20


def test_retired_tasks_are_not_scheduled(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        service.create_credential(
            ApiCredentialCreate(
                label="通用 API",
                base_url="https://general.example.test/v1",
                model_name="gpt-general",
                api_key="sk-general-1234",
            ),
            actor_user_id="admin",
        )
        slot, selected = service.select_credentials_for_task("image_content_analysis")

    assert slot is None
    assert selected == []


def test_transient_text_timeout_does_not_keep_capability_ok():
    checked_at = datetime.now(timezone.utc)
    raw = api_center_service._capability_profile_with_result(
        "{}",
        task="search_result_recommendation_reason",
        status="ok",
        duration_ms=1000,
        error_summary=None,
        checked_at=checked_at,
    )

    updated = api_center_service._capability_profile_with_result(
        raw,
        task="search_result_recommendation_reason",
        status="timed_out",
        duration_ms=55000,
        error_summary="模型响应超时",
        error_code="response_timeout",
        checked_at=checked_at,
    )
    profile = {
        item.capability: item.status
        for item in api_center_service._capability_reads(updated)
    }

    assert profile["text_json"] == "unknown"


def test_unconfigured_runtime_call_is_visible_as_skipped(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        provider = service.build_scheduled_provider()
        with pytest.raises(ModelProviderNotConfigured):
            provider.generate_json(
                ModelRequest(
                    task="asset_agent_chat",
                    prompt="Return JSON",
                    timeout_seconds=1,
                )
            )
        summary = service.summary()

    trace = next(
        item
        for item in summary.recent_call_traces
        if item.task == "asset_agent_chat"
    )
    assert trace.status == "skipped"


def test_cancelled_runtime_call_wins_over_missing_api_configuration(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        cancellation = CancellationSignal()
        cancellation.cancel()
        provider = service.build_scheduled_provider()

        with pytest.raises(ModelProviderCancelled, match="已取消"):
            provider.generate_json(
                ModelRequest(
                    task="asset_agent_chat",
                    prompt="Return JSON",
                    timeout_seconds=1,
                    cancellation=cancellation,
                )
            )

        trace = next(
            item
            for item in service.summary().recent_call_traces
            if item.task == "asset_agent_chat"
        )

    assert trace.status == "timed_out"
    assert trace.credential_id is None


def test_environment_credentials_are_imported_into_api_center(db_factory, monkeypatch):
    settings = SimpleNamespace(
        model_base_url="https://primary.example.test/v1",
        model_name="gpt-primary",
        model_api_key="sk-primary-1111",
        model_temperature=0.2,
        search_fallback_base_url="https://fallback.example.test/v1",
        search_fallback_model_name="gpt-fallback",
        search_fallback_api_key="sk-search-2222",
        search_fallback_temperature=0.2,
        image_analysis_base_url="https://image.example.test/v1",
        image_analysis_model_name="gpt-image",
        image_analysis_api_key="sk-image-3333",
        image_analysis_temperature=0.2,
        asset_phrase_base_url="https://phrase.example.test/v1",
        asset_phrase_model_name="gpt-phrase",
        asset_phrase_api_key="sk-phrase-4444",
        asset_phrase_temperature=0.2,
    )
    monkeypatch.setattr(api_center_service, "get_settings", lambda: settings)

    with db_factory() as db:
        service = ApiCenterService(db)
        service.initialize_runtime()
        summary = service.summary()

    labels = {item.label for item in summary.credentials}
    assert {
        "环境导入 · 搜索主 Key",
        "环境导入 · 搜索备用 Key",
        "环境导入 · Piancton Agent Key",
    }.issubset(labels)
    assert "环境导入 · 主图分析 Key" not in labels
    assert all(not item.api_key_preview.endswith("1111" * 2) for item in summary.credentials)
    search_key = next(item for item in summary.credentials if item.label == "环境导入 · 搜索主 Key")
    assert "search_result_recommendation_reason" in search_key.task_scope
    assert summary.overview.configured_slot_count == 2


def test_environment_import_does_not_overwrite_existing_api_center_credentials(
    db_factory,
    monkeypatch,
):
    settings = SimpleNamespace(
        model_base_url="https://legacy.example.test/v1",
        model_name="legacy-model",
        model_api_key="legacy-key",
        model_temperature=0.2,
        search_fallback_base_url="",
        search_fallback_model_name="",
        search_fallback_api_key="",
        search_fallback_temperature=0.2,
        image_analysis_base_url="",
        image_analysis_model_name="",
        image_analysis_api_key="",
        image_analysis_temperature=0.2,
        asset_phrase_base_url="",
        asset_phrase_model_name="",
        asset_phrase_api_key="",
        asset_phrase_temperature=0.2,
    )
    monkeypatch.setattr(api_center_service, "get_settings", lambda: settings)

    with db_factory() as db:
        service = ApiCenterService(db)
        created = service.create_credential(
            ApiCredentialCreate(
                label="API 中心手动配置",
                base_url="https://center.example.test/v1",
                model_name="center-model",
                api_key="center-key",
                task_scope=["search_result_recommendation_reason"],
            ),
            actor_user_id="admin",
        )
        service.initialize_runtime()

        credentials = service.repo.list_credentials()
        persisted = service.repo.get_credential(created.id)

    assert len(credentials) == 1
    assert persisted is not None
    assert persisted.base_url == "https://center.example.test/v1"
    assert persisted.model_name == "center-model"
    assert persisted.api_key_secret == "center-key"


def test_deleted_api_center_credentials_are_not_restored_from_environment(
    db_factory,
    monkeypatch,
):
    settings = SimpleNamespace(
        model_base_url="https://legacy.example.test/v1",
        model_name="legacy-model",
        model_api_key="legacy-key",
        model_temperature=0.2,
        search_fallback_base_url="",
        search_fallback_model_name="",
        search_fallback_api_key="",
        search_fallback_temperature=0.2,
        image_analysis_base_url="",
        image_analysis_model_name="",
        image_analysis_api_key="",
        image_analysis_temperature=0.2,
        asset_phrase_base_url="",
        asset_phrase_model_name="",
        asset_phrase_api_key="",
        asset_phrase_temperature=0.2,
    )
    monkeypatch.setattr(api_center_service, "get_settings", lambda: settings)

    with db_factory() as db:
        service = ApiCenterService(db)
        service.initialize_runtime()
        imported = service.repo.list_credentials()
        assert len(imported) == 1

        service.delete_credential(imported[0].id)
        service.initialize_runtime()
        summary = service.summary()

    assert summary.credentials == []


def test_disabling_last_api_does_not_fallback_to_environment_provider(
    db_factory,
    monkeypatch,
):
    settings = SimpleNamespace(
        model_base_url="https://legacy.example.test/v1",
        model_name="legacy-model",
        model_api_key="legacy-key",
        model_temperature=0.2,
        search_fallback_base_url="",
        search_fallback_model_name="",
        search_fallback_api_key="",
        search_fallback_temperature=0.2,
        image_analysis_base_url="",
        image_analysis_model_name="",
        image_analysis_api_key="",
        image_analysis_temperature=0.2,
        asset_phrase_base_url="",
        asset_phrase_model_name="",
        asset_phrase_api_key="",
        asset_phrase_temperature=0.2,
    )
    monkeypatch.setattr(api_center_service, "get_settings", lambda: settings)

    with db_factory() as db:
        service = ApiCenterService(db)
        service.initialize_runtime()
        credential = service.repo.list_credentials()[0]
        service.update_credential(
            credential.id,
            ApiCredentialUpdate(status="disabled"),
        )
        provider = service.build_scheduled_provider()

        with pytest.raises(ModelProviderNotConfigured, match="API 中心没有可用"):
            provider.generate_json(
                ModelRequest(
                    task="search_result_recommendation_reason",
                    prompt="Return JSON",
                    timeout_seconds=1,
                )
            )

        trace = next(
            item
            for item in service.summary().recent_call_traces
            if item.task == "search_result_recommendation_reason"
        )

    assert trace.status == "skipped"
    assert trace.credential_id is None


def test_api_center_summary_is_read_only_until_runtime_initialization(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        assert service.summary().routing_slots == []
        service.initialize_runtime()
        assert service.summary().routing_slots


def test_api_center_scheduler_uses_healthy_auto_credentials(db_factory, monkeypatch):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "api.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 9,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        slower = service.create_credential(
            ApiCredentialCreate(
                label="未测试 Key",
                base_url="https://api.example.test/v1",
                model_name="gpt-slow",
                api_key="sk-slow-1111",
                task_scope=["search_result_recommendation_reason"],
                priority=10,
            ),
            actor_user_id="admin",
        )
        faster = service.create_credential(
            ApiCredentialCreate(
                label="健康 Key",
                base_url="https://api.example.test/v1",
                model_name="gpt-fast",
                api_key="sk-fast-2222",
                task_scope=["search_result_recommendation_reason"],
                priority=99,
            ),
            actor_user_id="admin",
        )
        credential = service.repo.get_credential(faster.id)
        assert credential is not None
        credential.last_status = "ok"
        credential.last_latency_ms = 9
        db.commit()

        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=15,
            )
        )

    assert result.value["ok"] is True
    assert calls == ["gpt-fast"]
    assert result.attempts[0]["credential_label"] == "健康 Key"
    assert slower.id != result.attempts[0]["credential_id"]


def test_auto_scheduler_for_search_explanation_uses_text_capability(db_factory, monkeypatch):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        return ModelCallResult(
            {"ok": True, "task": request.task},
            (
                {
                    "provider": "api.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 9,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        unknown = service.create_credential(
            ApiCredentialCreate(
                label="未测视觉 Key",
                base_url="https://api.example.test/v1",
                model_name="text-json",
                api_key="sk-text-json-1111",
                priority=1,
            ),
            actor_user_id="admin",
        )
        lower_priority = service.create_credential(
            ApiCredentialCreate(
                label="低优先级文本 Key",
                base_url="https://api.example.test/v1",
                model_name="fallback-text-json",
                api_key="sk-fallback-text-json-2222",
                priority=99,
            ),
            actor_user_id="admin",
        )
        unknown_credential = service.repo.get_credential(unknown.id)
        ready_credential = service.repo.get_credential(lower_priority.id)
        assert unknown_credential is not None
        assert ready_credential is not None
        unknown_credential.last_status = "ok"
        unknown_credential.last_latency_ms = 9
        ready_credential.last_status = "ok"
        ready_credential.last_latency_ms = 9
        ready_credential.capability_profile_json = (
            api_center_service._capability_profile_with_result(
                "{}",
                task="search_result_recommendation_reason",
                status="ok",
                duration_ms=9,
                error_summary=None,
                checked_at=datetime.now(timezone.utc),
            )
        )
        service.initialize_runtime()
        db.commit()

        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=15,
            )
        )

    assert result.value["ok"] is True
    assert calls == ["text-json"]
    assert result.attempts[0]["credential_label"] == "未测视觉 Key"


def test_api_center_scheduler_balances_repeated_calls_across_healthy_credentials(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "api.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 9,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        model_names = ["gpt-relay-a", "gpt-relay-b", "gpt-relay-c"]
        for index, model_name in enumerate(model_names):
            created = service.create_credential(
                ApiCredentialCreate(
                    label=f"健康中转站 {index + 1}",
                    base_url=f"https://relay-{index + 1}.example.test/v1",
                    model_name=model_name,
                    api_key=f"sk-relay-{index + 1}-1234",
                    priority=100,
                ),
                actor_user_id="admin",
            )
            credential = service.repo.get_credential(created.id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.initialize_runtime()
        db.commit()

        provider = service.build_scheduled_provider()
        for _ in range(6):
            result = provider.generate_json(
                ModelRequest(
                    task="search_result_recommendation_reason",
                    prompt="Return JSON",
                    input_text="test",
                    timeout_seconds=15,
                )
            )
            assert result.value["ok"] is True

    call_counts = [calls.count(model_name) for model_name in model_names]
    assert set(calls) == set(model_names)
    assert max(call_counts) - min(call_counts) <= 1


def test_api_center_scheduler_balances_provider_hosts_before_keys(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "api.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 9,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        credential_specs = [
            ("relay-a-key-1", "https://relay-a.example.test/v1"),
            ("relay-a-key-2", "https://relay-a.example.test/v1"),
            ("relay-b-key-1", "https://relay-b.example.test/v1"),
        ]
        for model_name, base_url in credential_specs:
            created = service.create_credential(
                ApiCredentialCreate(
                    label=model_name,
                    base_url=base_url,
                    model_name=model_name,
                    api_key=f"sk-{model_name}-1234",
                    priority=100,
                ),
                actor_user_id="admin",
            )
            credential = service.repo.get_credential(created.id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.initialize_runtime()
        db.commit()

        provider = service.build_scheduled_provider()
        for _ in range(6):
            provider.generate_json(
                ModelRequest(
                    task="search_result_recommendation_reason",
                    prompt="Return JSON",
                    input_text="test",
                    timeout_seconds=15,
                )
            )

    relay_a_calls = sum(call.startswith("relay-a") for call in calls)
    relay_b_calls = sum(call.startswith("relay-b") for call in calls)
    assert set(calls) == {item[0] for item in credential_specs}
    assert abs(relay_a_calls - relay_b_calls) <= 1


def test_api_center_scheduler_keeps_more_than_four_fallback_candidates(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        if self.model_name != "gpt-candidate-5":
            raise ModelProviderError(
                "中转站临时不可用",
                code="upstream_unavailable",
            )
        return ModelCallResult(
            {"ok": True, "task": request.task},
            (
                {
                    "provider": "fallback.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 9,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        for index in range(5):
            created = service.create_credential(
                ApiCredentialCreate(
                    label=f"候选 API {index + 1}",
                    base_url=f"https://fallback-{index + 1}.example.test/v1",
                    model_name=f"gpt-candidate-{index + 1}",
                    api_key=f"sk-candidate-{index + 1}-1234",
                    priority=index + 1,
                ),
                actor_user_id="admin",
            )
            credential = service.repo.get_credential(created.id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.initialize_runtime()
        db.commit()

        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=45,
            )
        )

    assert result.value["ok"] is True
    assert calls == [
        "gpt-candidate-1",
        "gpt-candidate-2",
        "gpt-candidate-3",
        "gpt-candidate-4",
        "gpt-candidate-5",
    ]


def test_scheduler_protects_relay_budget_in_sequential_mode(db_factory, monkeypatch):
    attempt_timeouts: list[float] = []

    def fake_generate_json(self, request):
        attempt_timeouts.append(request.timeout_seconds or 0)
        raise ModelProviderError(
            "上游暂时不可用",
            code="upstream_unavailable",
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        for index in range(3):
            created = service.create_credential(
                ApiCredentialCreate(
                    label=f"慢 API {index + 1}",
                    base_url=f"https://slow-{index + 1}.example.test/v1",
                    model_name=f"gpt-slow-{index + 1}",
                    api_key=f"sk-slow-{index + 1}-1234",
                    timeout_seconds=60,
                    priority=index + 1,
                ),
                actor_user_id="admin",
            )
            credential = service.repo.get_credential(created.id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 30_000
        service.update_slot(
            "search_result_recommendation_reason",
            RoutingSlotUpdate(
                timeout_seconds=45,
                max_parallel=1,
                hedging_delay_ms=0,
            ),
            actor_user_id="admin",
        )

        provider = service.build_scheduled_provider()
        with pytest.raises(ModelProviderError):
            provider.generate_json(
                ModelRequest(
                    task="search_result_recommendation_reason",
                    prompt="Return JSON",
                    input_text="test",
                    timeout_seconds=45,
                )
            )

    assert len(attempt_timeouts) == 3
    assert attempt_timeouts[0] <= 30
    assert attempt_timeouts[1] >= 8
    assert attempt_timeouts[2] >= 8


def test_scheduler_hedges_slow_attempt_and_uses_first_success(db_factory, monkeypatch):
    slow_started = Event()
    slow_cancelled = Event()
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        if self.model_name == "gpt-slow":
            slow_started.set()
            assert request.cancellation is not None
            request.cancellation.wait(1)
            if request.cancellation.cancelled:
                slow_cancelled.set()
                raise ModelProviderCancelled("模型调用已取消")
            return ModelCallResult({"winner": "slow"}, ())
        assert slow_started.is_set()
        return ModelCallResult(
            {"winner": "fast"},
            (
                {
                    "provider": "fast.example.test",
                    "model": self.model_name,
                    "status": "ok",
                    "duration_ms": 9,
                    "error": "",
                },
            ),
        )

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        slow = service.create_credential(
            ApiCredentialCreate(
                label="慢 Key",
                base_url="https://slow.example.test/v1",
                model_name="gpt-slow",
                api_key="sk-slow-1111",
                priority=1,
            ),
            actor_user_id="admin",
        )
        fast = service.create_credential(
            ApiCredentialCreate(
                label="快 Key",
                base_url="https://fast.example.test/v1",
                model_name="gpt-fast",
                api_key="sk-fast-2222",
                priority=2,
            ),
            actor_user_id="admin",
        )
        for credential_id in [slow.id, fast.id]:
            credential = service.repo.get_credential(credential_id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.update_slot(
            "search_result_recommendation_reason",
            RoutingSlotUpdate(
                timeout_seconds=20,
                max_parallel=2,
                hedging_delay_ms=10,
            ),
            actor_user_id="admin",
        )

        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=20,
            )
        )

    assert result.value == {"winner": "fast"}
    assert calls[:2] == ["gpt-slow", "gpt-fast"]
    assert slow_cancelled.wait(1)


def test_scheduler_reuses_selection_snapshot_metrics_during_request(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        if self.model_name != "gpt-candidate-4":
            raise ModelProviderError("上游暂时不可用", code="upstream_unavailable")
        return ModelCallResult({"ok": True, "winner": self.model_name}, ())

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        for index in range(4):
            created = service.create_credential(
                ApiCredentialCreate(
                    label=f"候选 API {index + 1}",
                    base_url=f"https://snapshot-{index + 1}.example.test/v1",
                    model_name=f"gpt-candidate-{index + 1}",
                    api_key=f"sk-snapshot-{index + 1}-1234",
                    priority=index + 1,
                ),
                actor_user_id="admin",
            )
            credential = service.repo.get_credential(created.id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.update_slot(
            "search_result_recommendation_reason",
            RoutingSlotUpdate(
                timeout_seconds=45,
                max_parallel=1,
                hedging_delay_ms=0,
            ),
            actor_user_id="admin",
        )
        original = service.repo.list_call_traces_since
        metric_query_count = 0

        def counted_list_call_traces_since(*args, **kwargs):
            nonlocal metric_query_count
            metric_query_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(
            service.repo,
            "list_call_traces_since",
            counted_list_call_traces_since,
        )

        result = service.build_scheduled_provider().generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=45,
            )
        )

    assert result.value == {"ok": True, "winner": "gpt-candidate-4"}
    assert calls == [
        "gpt-candidate-1",
        "gpt-candidate-2",
        "gpt-candidate-3",
        "gpt-candidate-4",
    ]
    assert metric_query_count == 1


def test_provider_group_summary_recommends_disable_for_degraded_host(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        relay_a = service.create_credential(
            ApiCredentialCreate(
                label="Relay A-1",
                base_url="https://relay-a.example.test/v1",
                model_name="gpt-a",
                api_key="sk-relay-a-1111",
            ),
            actor_user_id="admin",
        )
        service.create_credential(
            ApiCredentialCreate(
                label="Relay A-2",
                base_url="https://relay-a.example.test/v1",
                model_name="gpt-a",
                api_key="sk-relay-a-2222",
            ),
            actor_user_id="admin",
        )
        service.create_credential(
            ApiCredentialCreate(
                label="Relay B",
                base_url="https://relay-b.example.test/v1",
                model_name="gpt-b",
                api_key="sk-relay-b-1111",
            ),
            actor_user_id="admin",
        )
        service.record_call_traces_from_attempts(
            search_log_id=None,
            request_id="relay-a-outage",
            persist=True,
            branches=[
                {
                    "source": "search_result_recommendation_reason",
                    "status": "timed_out",
                    "attempts": [
                        {
                            "task": "search_result_recommendation_reason",
                            "layer": "第一层：体系路由",
                            "provider": "relay-a.example.test",
                            "model": "gpt-a",
                            "credential_id": relay_a.id,
                            "status": "timed_out",
                            "duration_ms": 20_000,
                            "error": "模型响应超时",
                        }
                        for _ in range(4)
                    ],
                }
            ],
        )
        summary = service.summary()

    group = next(
        item for item in summary.provider_groups
        if item.provider_group == "relay-a.example.test"
    )
    assert group.status == "degraded"
    assert group.credential_count == 2
    assert group.recent_call_count == 4
    assert group.recent_failure_rate == 1
    assert group.recent_timeout_count == 4
    assert "一键停用" in (group.recommendation or "")


def test_disable_provider_group_disables_matching_credentials(client):
    headers = admin_headers(client)
    first = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Relay One A",
            "baseUrl": "https://relay-one.example.test/v1",
            "modelName": "gpt-a",
            "apiKey": "sk-relay-one-a-1234",
        },
    ).json()
    second = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Relay One B",
            "baseUrl": "https://relay-one.example.test/v1",
            "modelName": "gpt-b",
            "apiKey": "sk-relay-one-b-1234",
        },
    ).json()
    other = client.post(
        "/api/admin/api-center/credentials",
        headers=headers,
        json={
            "label": "Relay Two",
            "baseUrl": "https://relay-two.example.test/v1",
            "modelName": "gpt-c",
            "apiKey": "sk-relay-two-1234",
        },
    ).json()

    response = client.post(
        "/api/admin/api-center/provider-groups/relay-one.example.test/disable",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["activeCredentialCount"] == 0
    summary = client.get("/api/admin/api-center/summary", headers=headers).json()
    statuses = {
        item["id"]: item["status"]
        for item in summary["credentials"]
    }
    assert statuses[first["id"]] == "disabled"
    assert statuses[second["id"]] == "disabled"
    assert statuses[other["id"]] == "active"
    logs = client.get("/api/admin/users/audit-logs", headers=headers).json()
    audit_log = next(
        item
        for item in logs
        if item["action"] == "api_center.provider_group.disable"
    )
    assert audit_log["targetId"] == "relay-one.example.test"
    assert set(audit_log["details"]["affectedCredentialIds"]) == {
        first["id"],
        second["id"],
    }
    assert audit_log["details"]["activeCredentialCountBefore"] == 2
    assert audit_log["details"]["activeCredentialCountAfter"] == 0


def test_health_check_targets_are_grouped_by_provider_host():
    groups = api_center_service._group_health_probe_targets_by_provider(
        [
            api_center_service._HealthProbeTarget(
                credential_id="a",
                task="search_result_recommendation_reason",
                provider_group="relay.example.test",
            ),
            api_center_service._HealthProbeTarget(
                credential_id="b",
                task="asset_agent_chat",
                provider_group="relay.example.test",
            ),
            api_center_service._HealthProbeTarget(
                credential_id="c",
                task="search_result_recommendation_reason",
                provider_group="other.example.test",
            ),
        ]
    )

    assert [[target.credential_id for target in group] for group in groups] == [
        ["a", "b"],
        ["c"],
    ]


def test_api_center_scheduler_honors_slot_exclusions(db_factory, monkeypatch):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "api.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 9,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        blocked = service.create_credential(
            ApiCredentialCreate(
                label="本任务屏蔽 Key",
                base_url="https://api.example.test/v1",
                model_name="gpt-blocked",
                api_key="sk-blocked-1111",
                task_scope=["search_result_recommendation_reason"],
                priority=1,
            ),
            actor_user_id="admin",
        )
        allowed = service.create_credential(
            ApiCredentialCreate(
                label="本任务低优先允许 Key",
                base_url="https://api.example.test/v1",
                model_name="gpt-allowed",
                api_key="sk-allowed-2222",
                task_scope=["search_result_recommendation_reason"],
                priority=99,
            ),
            actor_user_id="admin",
        )
        for credential_id in [blocked.id, allowed.id]:
            credential = service.repo.get_credential(credential_id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        service.update_slot(
            "search_result_recommendation_reason",
            RoutingSlotUpdate(
                auto_select_enabled=True,
                excluded_credential_ids=[blocked.id],
            ),
            actor_user_id="admin",
        )

        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="search_result_recommendation_reason",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=15,
            )
        )
        routing = next(
            item
            for item in service.summary().routing_slots
            if item.task == "search_result_recommendation_reason"
        )

    assert result.value["ok"] is True
    assert calls == ["gpt-allowed"]
    assert result.attempts[0]["credential_id"] == allowed.id
    assert routing.excluded_credential_ids == [blocked.id]
    assert routing.excluded_credential_labels == ["本任务屏蔽 Key"]


def test_api_center_scheduler_skips_saturated_credential(db_factory, monkeypatch):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "api.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 11,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        busy = service.create_credential(
            ApiCredentialCreate(
                label="最优但满载 API",
                base_url="https://api.example.test/v1",
                model_name="gpt-busy",
                api_key="sk-busy-1111",
                task_scope=["search_result_recommendation_reason"],
                priority=1,
                max_concurrency=1,
            ),
            actor_user_id="admin",
        )
        idle = service.create_credential(
            ApiCredentialCreate(
                label="可接新请求 API",
                base_url="https://api.example.test/v1",
                model_name="gpt-idle",
                api_key="sk-idle-2222",
                task_scope=["search_result_recommendation_reason"],
                priority=99,
                max_concurrency=1,
            ),
            actor_user_id="admin",
        )
        for credential_id in [busy.id, idle.id]:
            credential = service.repo.get_credential(credential_id)
            assert credential is not None
            credential.last_status = "ok"
            credential.last_latency_ms = 10
        db.commit()

        assert api_center_service._CAPACITY_TRACKER.try_acquire(busy.id, 1)
        try:
            provider = service.build_scheduled_provider()
            result = provider.generate_json(
                ModelRequest(
                    task="search_result_recommendation_reason",
                    prompt="Return JSON",
                    input_text="test",
                    timeout_seconds=15,
                )
            )
            summary = service.summary()
        finally:
            api_center_service._CAPACITY_TRACKER.release(busy.id)

    assert result.value["ok"] is True
    assert calls == ["gpt-idle"]
    assert result.attempts[0]["credential_id"] == idle.id
    busy_read = next(item for item in summary.credentials if item.id == busy.id)
    assert busy_read.current_concurrency == 1
    assert busy_read.capacity_status == "saturated"


def test_api_center_scheduler_honors_cancelled_request_before_capacity_wait(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        return ModelCallResult({"ok": True}, ())

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="已满载 API",
                base_url="https://busy.example.test/v1",
                model_name="gpt-busy",
                api_key="sk-busy-value-1234",
                task_scope=["search_result_recommendation_reason"],
                max_concurrency=1,
            ),
            actor_user_id="admin",
        )
        assert api_center_service._CAPACITY_TRACKER.try_acquire(credential.id, 1)
        cancellation = CancellationSignal()
        cancellation.cancel()
        try:
            provider = service.build_scheduled_provider()
            with pytest.raises(ModelProviderCancelled, match="已取消"):
                provider.generate_json(
                    ModelRequest(
                        task="search_result_recommendation_reason",
                        prompt="Return JSON",
                        input_text="cancelled before capacity wait",
                        timeout_seconds=15,
                        cancellation=cancellation,
                    )
                )
            trace = next(
                item
                for item in service.summary().recent_call_traces
                if item.task == "search_result_recommendation_reason"
            )
        finally:
            api_center_service._CAPACITY_TRACKER.release(credential.id)

    assert calls == []
    assert trace.status == "timed_out"
    assert trace.credential_id is None


def test_manual_slot_uses_explicit_credentials_when_auto_assign_is_disabled(
    db_factory,
    monkeypatch,
):
    calls: list[str] = []

    def fake_generate_json(self, request):
        calls.append(self.model_name)
        attempts = (
            {
                "provider": "manual.example.test",
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 8,
                "error": "",
            },
        )
        return ModelCallResult({"ok": True, "task": request.task}, attempts)

    monkeypatch.setattr(
        OpenAICompatibleModelProvider,
        "generate_json",
        fake_generate_json,
    )

    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="人工指定 Key",
                base_url="https://manual.example.test/v1",
                model_name="gpt-manual",
                api_key="sk-manual-value-1234",
                task_scope=["asset_agent_chat"],
                auto_assign_enabled=False,
            ),
            actor_user_id="admin",
        )
        service.update_slot(
            "asset_agent_chat",
            RoutingSlotUpdate(
                primary_credential_id=credential.id,
                auto_select_enabled=False,
            ),
            actor_user_id="admin",
        )
        provider = service.build_scheduled_provider()
        result = provider.generate_json(
            ModelRequest(
                task="asset_agent_chat",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=5,
            )
        )

    assert result.value["ok"] is True
    assert calls == ["gpt-manual"]


def test_runtime_failure_does_not_disable_or_unassign_manual_credential(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="人工主 API",
                base_url="https://manual-stable.example.test/v1",
                model_name="gpt-manual-stable",
                api_key="sk-manual-stable-1234",
                auto_assign_enabled=False,
            ),
            actor_user_id="admin",
        )
        service.update_slot(
            "asset_agent_chat",
            RoutingSlotUpdate(
                primary_credential_id=credential.id,
                auto_select_enabled=False,
            ),
            actor_user_id="admin",
        )

        service.record_runtime_attempt(
            credential.id,
            status="timed_out",
            duration_ms=5000,
            error_summary="模型响应超时",
        )
        db.commit()
        persisted = service.repo.get_credential(credential.id)
        _, selected = service.select_credentials_for_task("asset_agent_chat")

    assert persisted is not None
    assert persisted.status == "active"
    assert persisted.last_status == "timed_out"
    assert [item.id for item in selected] == [credential.id]


def test_initialize_runtime_normalizes_legacy_health_status_without_losing_manual_slot(
    db_factory,
):
    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="旧 cooling API",
                base_url="https://legacy-cooling.example.test/v1",
                model_name="gpt-legacy",
                api_key="sk-legacy-cooling-1234",
                auto_assign_enabled=False,
            ),
            actor_user_id="admin",
        )
        stored = service.repo.get_credential(credential.id)
        assert stored is not None
        stored.status = "cooling"
        service.update_slot(
            "asset_agent_chat",
            RoutingSlotUpdate(
                primary_credential_id=credential.id,
                auto_select_enabled=False,
            ),
            actor_user_id="admin",
        )
        service.initialize_runtime()
        _, selected = service.select_credentials_for_task("asset_agent_chat")

    assert stored.status == "active"
    assert [item.id for item in selected] == [credential.id]


def test_initialize_runtime_moves_env_imported_keys_off_retired_tasks(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db)
        credential = service.repo.add_credential(
            ModelApiCredential(
                label="环境导入 · 搜索主 Key",
                provider_type="openai_compatible",
                base_url="https://legacy.example.test/v1",
                model_name="gpt-legacy",
                api_key_secret="sk-legacy-1234",
                api_key_fingerprint="legacy",
                api_key_preview="sk-l...1234",
                task_scope_json=json.dumps(
                    [
                        "search_system_routing",
                        "search_intent_understanding",
                        "search_proof_point_understanding",
                    ],
                    ensure_ascii=False,
                ),
                status="active",
                auto_assign_enabled=True,
            )
        )
        manual = service.repo.add_credential(
            ModelApiCredential(
                label="人工旧 Key",
                provider_type="openai_compatible",
                base_url="https://manual.example.test/v1",
                model_name="gpt-manual",
                api_key_secret="sk-manual-1234",
                api_key_fingerprint="manual",
                api_key_preview="sk-m...1234",
                task_scope_json=json.dumps(["search_system_routing"]),
                status="active",
                auto_assign_enabled=True,
            )
        )
        db.commit()

        service.initialize_runtime()

        assert json.loads(credential.task_scope_json) == [
            "search_result_recommendation_reason",
        ]
        assert json.loads(manual.task_scope_json) == ["search_system_routing"]


def test_runtime_attempt_is_committed_in_trace_session(db_factory):
    with db_factory() as db:
        service = ApiCenterService(db, trace_session_factory=db_factory)
        credential = service.create_credential(
            ApiCredentialCreate(
                label="独立状态 Key",
                base_url="https://runtime.example.test/v1",
                model_name="gpt-runtime",
                api_key="sk-runtime-value-1234",
            ),
            actor_user_id="admin",
        )
        service.record_runtime_attempt(
            credential.id,
            status="ok",
            duration_ms=42,
            error_summary=None,
        )

    with db_factory() as db:
        persisted = ApiCenterService(db).repo.get_credential(credential.id)

    assert persisted is not None
    assert persisted.last_status == "ok"
    assert persisted.last_latency_ms == 42
