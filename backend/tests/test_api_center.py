from types import SimpleNamespace

import pytest

from app.ai.contracts import (
    CancellationSignal,
    ModelCallResult,
    ModelProviderCancelled,
    ModelProviderNotConfigured,
    ModelRequest,
)
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.schemas.api_center import (
    ApiCredentialCreate,
    ApiCredentialUpdate,
    RoutingSlotUpdate,
)
from app.services import api_center_service
from app.services.api_center_service import ApiCenterService
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
    )


@pytest.fixture(autouse=True)
def no_environment_provider_import(monkeypatch):
    api_center_service._CAPACITY_TRACKER.reset_for_tests()
    monkeypatch.setattr(api_center_service, "get_settings", _empty_provider_settings)
    yield
    api_center_service._CAPACITY_TRACKER.reset_for_tests()


def admin_headers(client) -> dict[str, str]:
    csrf = login(client, "admin", "admin-password")
    return {"X-CSRF-Token": csrf, "Origin": "http://localhost:5173"}


def test_admin_api_center_summary_initializes_default_slots(client):
    headers = admin_headers(client)

    response = client.get("/api/admin/api-center/summary", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    tasks = {item["task"] for item in payload["routingSlots"]}
    assert {
        "search_system_routing",
        "search_intent_understanding",
        "search_proof_point_understanding",
        "search_candidate_review",
    }.issubset(tasks)
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
            "taskScope": ["search_system_routing"],
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
    assert "apiKey" not in payload

    disable = client.patch(
        f"/api/admin/api-center/credentials/{payload['id']}",
        headers=headers,
        json={"status": "disabled"},
    )
    assert disable.status_code == 200
    assert disable.json()["status"] == "disabled"


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
            "taskScope": ["search_system_routing"],
        },
    ).json()
    slot = client.patch(
        "/api/admin/api-center/routing-slots/search_system_routing",
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
        if item["task"] == "search_system_routing"
    )
    assert routing["primaryCredentialId"] is None
    assert routing["backupCredentialIds"] == []


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
        json={"task": "search_system_routing"},
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
    assert health_traces[0]["task"] == "search_system_routing"
    assert health_traces[0]["layerName"] == "健康检查"
    assert health_traces[0]["credentialLabel"] == "OpenAI-健康测试"


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
            "taskScope": ["search_system_routing"],
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
            "taskScope": ["search_system_routing"],
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
                            "task": "search_system_routing",
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
        provider = service.build_scheduled_provider()
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
    assert traces[0].output_summary["kind"] == "runtime"
    assert "private agent context" not in str(traces[0].output_summary)


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
        "环境导入 · 主图分析 Key",
        "环境导入 · 话术生成 Key",
    }.issubset(labels)
    assert all(not item.api_key_preview.endswith("1111" * 2) for item in summary.credentials)
    search_key = next(item for item in summary.credentials if item.label == "环境导入 · 搜索主 Key")
    assert "search_system_routing" in search_key.task_scope
    assert summary.overview.configured_slot_count >= 4


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
                task_scope=["search_system_routing"],
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
                    task="search_system_routing",
                    prompt="Return JSON",
                    timeout_seconds=1,
                )
            )

        trace = next(
            item
            for item in service.summary().recent_call_traces
            if item.task == "search_system_routing"
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
                task_scope=["search_system_routing"],
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
                task_scope=["search_system_routing"],
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
                task="search_system_routing",
                prompt="Return JSON",
                input_text="test",
                timeout_seconds=15,
            )
        )

    assert result.value["ok"] is True
    assert calls == ["gpt-fast"]
    assert result.attempts[0]["credential_label"] == "健康 Key"
    assert slower.id != result.attempts[0]["credential_id"]


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
                task_scope=["search_system_routing"],
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
                task_scope=["search_system_routing"],
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
                    task="search_system_routing",
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
                task_scope=["search_system_routing"],
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
                        task="search_system_routing",
                        prompt="Return JSON",
                        input_text="cancelled before capacity wait",
                        timeout_seconds=15,
                        cancellation=cancellation,
                    )
                )
            trace = next(
                item
                for item in service.summary().recent_call_traces
                if item.task == "search_system_routing"
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
