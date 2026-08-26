from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import sleep
from types import SimpleNamespace

import httpx
import pytest

from app.ai import factory
from app.ai.contracts import (
    CancellationSignal,
    ModelCallResult,
    ModelProviderCancelled,
    ModelProviderError,
    ModelRequest,
)
from app.ai.fallback import FallbackModelProvider
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.api.dependencies import _provider_attempt_count
from app.schemas.ai import SearchUnderstanding
from app.services.ai_service import AiService
from tests.conftest import ModelProviderStub


def test_openai_compatible_provider_extracts_json_from_markdown_wrapped_content(monkeypatch):
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="vision-model",
    )

    def fake_post(_payload):
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            '```json\n{"original_query":"老师","normalized_query":"老师"}\n```'
                        )
                    }
                }
            ]
        }

    monkeypatch.setattr(provider, "_post_chat_completions", fake_post)
    result = provider.generate_json(
        ModelRequest(
            task="search_intent_understanding",
            prompt="Return JSON",
            input_text="老师",
        )
    )

    assert result.value["original_query"] == "老师"
    assert result.value["normalized_query"] == "老师"


def test_openai_compatible_provider_sends_image_as_data_url(tmp_path: Path, monkeypatch):
    image = tmp_path / "sample.png"
    image.write_bytes(b"fake-image-bytes")
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="vision-model",
    )
    captured = {}

    def fake_post(payload):
        captured.update(payload)
        return {"choices": [{"message": {"content": '{"image_type":"function"}'}}]}

    monkeypatch.setattr(provider, "_post_chat_completions", fake_post)
    provider.generate_json(
        ModelRequest(
            task="image_content_analysis",
            prompt="Return JSON",
            image_path=image,
        )
    )

    content = captured["messages"][1]["content"]
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_openai_compatible_provider_uses_request_specific_timeout(monkeypatch):
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="search-model",
        timeout_seconds=120,
    )
    captured = {}

    def fake_post(_payload, *, timeout_seconds=None):
        captured["timeout_seconds"] = timeout_seconds
        return {"choices": [{"message": {"content": '{"ok":true}'}}]}

    monkeypatch.setattr(provider, "_post_chat_completions", fake_post)
    provider.generate_json(
        ModelRequest(
            task="search_system_routing",
            prompt="Return JSON",
            input_text="拍题后分步点拨",
            timeout_seconds=8,
        )
    )

    assert captured["timeout_seconds"] == 8


def test_openai_compatible_provider_closes_transport_when_cancelled(monkeypatch):
    class SlowClient:
        instances = []

        def __init__(self, **_kwargs):
            self.started = Event()
            self.closed = Event()
            self.close_calls = 0
            self.__class__.instances.append(self)

        def post(self, *_args, **_kwargs):
            self.started.set()
            self.closed.wait(timeout=2)
            raise httpx.ReadError(
                "transport closed",
                request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            )

        def close(self):
            self.close_calls += 1
            self.closed.set()

    monkeypatch.setattr("app.ai.openai_compatible.httpx.Client", SlowClient)
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="search-model",
        timeout_seconds=30,
    )
    cancellation = CancellationSignal()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            provider.generate_json,
            ModelRequest(
                task="search_system_routing",
                prompt="Return JSON",
                cancellation=cancellation,
                timeout_seconds=30,
            ),
        )
        assert SlowClient.instances[0].started.wait(timeout=1)
        cancellation.cancel()
        with pytest.raises(ModelProviderCancelled):
            future.result(timeout=1)

    assert SlowClient.instances[0].close_calls >= 1


def test_openai_compatible_provider_maps_timeout_race_to_cancelled(monkeypatch):
    class TimeoutClient:
        def __init__(self, **_kwargs):
            self.closed = False

        def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout(
                "request timed out",
                request=httpx.Request(
                    "POST",
                    "https://example.test/v1/chat/completions",
                ),
            )

        def close(self):
            self.closed = True

    monkeypatch.setattr("app.ai.openai_compatible.httpx.Client", TimeoutClient)
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="search-model",
    )
    cancellation = CancellationSignal()
    cancellation.cancel()

    with pytest.raises(ModelProviderCancelled):
        provider.generate_json(
            ModelRequest(
                task="search_system_routing",
                prompt="Return JSON",
                cancellation=cancellation,
            )
        )


def test_search_tasks_receive_layer_specific_decision_roles():
    provider = OpenAICompatibleModelProvider(
        base_url="https://example.test/v1",
        api_key="test-key",
        model_name="search-model",
    )

    router_system = provider._messages(
        ModelRequest(
            task="search_system_routing",
            prompt="Return JSON",
            input_text="一键拍照",
        )
    )[0]["content"]
    selling_point_system = provider._messages(
        ModelRequest(
            task="search_intent_understanding",
            prompt="Return JSON",
            input_text="一键拍照",
        )
    )[0]["content"]
    proof_point_system = provider._messages(
        ModelRequest(
            task="search_proof_point_understanding",
            prompt="Return JSON",
            input_text="一键拍照",
        )
    )[0]["content"]

    assert "第一层路由决策员" in router_system
    assert "不得提前判断卖点或具体图片" in router_system
    assert "第二层卖点决策员" in selling_point_system
    assert "不得让通用结果词或方法细节覆盖更主要的入口证据" in selling_point_system
    assert "本层不得判断证明点" in selling_point_system
    assert "第三层证明点决策员" in proof_point_system
    assert "不得新增、删除或改写卖点" in proof_point_system


def test_ai_service_runs_strict_system_selling_point_proof_point_chain():
    class RecordingProvider(ModelProviderStub):
        name = "recording"
        configured = True

        def __init__(self):
            self.requests = []

        def generate_json(self, request):
            self.requests.append(request)
            if request.task == "search_system_routing":
                return ModelCallResult(
                    {
                        "original_query": request.input_text,
                        "route_type": "single_system",
                        "candidate_systems": [
                            {
                                "code": "sync_school",
                                "relation": "primary",
                                "reason": "动画讲解",
                                "weight": 0.98,
                            }
                        ],
                    }
                )
            if request.task == "search_intent_understanding":
                return ModelCallResult(
                    {
                        "original_query": "想找短小的动画课",
                        "normalized_query": "动画精讲",
                        "search_intent": "动画讲解",
                        "query_type": "business_intent_search",
                        "matched_business_concepts": [
                            {
                                "concept": "animation_explanation",
                                "relation": "direct",
                                "reason": "明确要求动画讲解",
                                "weight": 0.98,
                            }
                        ],
                        "matched_proof_points": [],
                        "matched_evidence_points": [],
                    }
                )
            return ModelCallResult(
                {
                    "original_query": "想找短小的动画课",
                    "matched_proof_points": [
                        {
                            "code": "pp_animation_pedagogy_design",
                            "concept_code": "animation_explanation",
                            "name": "模型名称会被规范化",
                            "reason": "短小、单点讲透",
                            "weight": 0.95,
                            "evidence_terms": ["5-8 分钟动画微课"],
                        }
                    ],
                    "matched_evidence_points": [],
                }
            )

    provider = RecordingProvider()
    result = AiService(provider).understand_search("想找短小的动画课").value

    assert [request.task for request in provider.requests] == [
        "search_system_routing",
        "search_intent_understanding",
        "search_proof_point_understanding",
    ]
    assert "### 证明点" not in provider.requests[1].prompt
    assert "候选体系证据表达点目录" not in provider.requests[1].prompt
    assert "pp_animation_pedagogy_design" in provider.requests[2].prompt
    assert "pp_school_quiz_immediate_feedback" not in provider.requests[2].prompt
    assert [item.code for item in result.matched_proof_points] == [
        "pp_animation_pedagogy_design"
    ]


def test_ai_service_normalizes_system_route_shape_and_keeps_scoped_proof_hints():
    class RecordingProvider(ModelProviderStub):
        name = "recording"
        configured = True

        def generate_json(self, request):
            if request.task == "search_system_routing":
                return ModelCallResult(
                    {
                        "route_type": "single",
                        "systems": [
                            {
                                "system": "同步校内",
                                "reason": "模型用中文体系名返回",
                                "weight": "0.96",
                            }
                        ],
                    }
                )
            return ModelCallResult(
                {
                    "original_query": request.input_text,
                    "normalized_query": "动画精讲",
                    "search_intent": "短时间讲透一个知识点",
                    "query_type": "single_intent_search",
                    "matched_business_concepts": [
                        {
                            "concept": "animation_explanation",
                            "relation": "direct",
                            "reason": "模型返回稳定卖点 code",
                            "weight": 0.97,
                        }
                    ],
                    "matched_proof_points": [
                        {
                            "code": "pp_animation_pedagogy_design",
                            "concept_code": "animation_explanation",
                            "name": "模型名称会被规范化",
                            "reason": "短时间讲透一个知识点",
                            "weight": 0.94,
                            "evidence_terms": ["5-8 分钟动画微课"],
                        },
                        {
                            "code": "pp_photo_guided_socratic_method",
                            "concept_code": "photo_guided_learning",
                            "name": "跨卖点证明点会被丢弃",
                            "reason": "越界",
                            "weight": 0.9,
                            "evidence_terms": [],
                        },
                    ],
                    "matched_evidence_points": [],
                }
            )

    service = AiService(RecordingProvider())
    routing = service.route_search_system("一节课不长，一个点能讲透").value
    result = service.understand_selling_points_from_route(
        "一节课不长，一个点能讲透",
        routing,
    ).value

    assert [item.code for item in routing.candidate_systems] == ["sync_school"]
    assert routing.route_type == "single_system"
    assert [item.code for item in result.matched_proof_points] == [
        "pp_animation_pedagogy_design"
    ]


def test_ai_service_accepts_search_understanding_shorthand_payload():
    class ShorthandProvider(ModelProviderStub):
        name = "shorthand"
        configured = True

        def generate_json(self, request):
            return ModelCallResult(
                {
                    "query_state": "business_intent_search",
                    "matched_business_concepts": [
                        {
                            "code": "learning_report",
                            "evidence": ["家长可以查看学习结果"],
                            "concept": "",
                        }
                    ],
                    "matched_proof_points": [],
                    "matched_evidence_points": [],
                    "excluded_concepts": [],
                    "expanded_terms": ["学习结果查看", "学习反馈"],
                    "search_strategy": "指向向家长反馈学习结果/学习情况的卖点。",
                }
            )

    service = AiService(ShorthandProvider())
    result = service._run(
        ModelRequest(
            task="search_intent_understanding",
            prompt="Return JSON",
            input_text="第一层候选体系：sync_companion\n原始查询：家长可以查看学习结果",
        ),
        result_type=SearchUnderstanding,
    ).value

    assert result.original_query == "家长可以查看学习结果"
    assert result.query_type == "business_intent_search"
    assert result.matched_business_concepts[0].concept.endswith("学情报告反馈")
    assert result.matched_business_concepts[0].relation == "direct"
    assert result.expanded_terms[0].term == "学习结果查看"


def test_factory_respects_explicit_provider_order(monkeypatch):
    settings = SimpleNamespace(
        model_provider="openai_compatible",
        model_provider_order="fallback2,fallback1,primary",
        model_name="gpt-5.5",
        model_base_url="https://gpt.example.test/v1",
        model_api_key="gpt-key",
        model_temperature=0.2,
        model_timeout_seconds=120,
        fallback1_name="deepseek-v4-pro",
        fallback1_base_url="https://deepseek.example.test/v1",
        fallback1_api_key="deepseek-key",
        fallback1_temperature=0.2,
        fallback2_name="kimi-k2.7-code",
        fallback2_base_url="https://kimi.example.test/v1",
        fallback2_api_key="kimi-key",
        fallback2_temperature=0.2,
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    provider = factory.get_model_provider()

    assert isinstance(provider, FallbackModelProvider)
    assert [item.model_name for item in provider.providers] == [
        "kimi-k2.7-code",
        "deepseek-v4-pro",
        "gpt-5.5",
    ]


def test_factory_isolates_image_phrase_and_search_credentials(monkeypatch):
    settings = SimpleNamespace(
        model_provider="openai_compatible",
        model_provider_order="primary",
        model_name="gpt-5.5",
        model_base_url="https://primary.example.test/v1",
        model_api_key="search-primary-key",
        model_temperature=0.2,
        model_timeout_seconds=120,
        image_analysis_model_name="gpt-5.5",
        image_analysis_base_url="https://primary.example.test/v1",
        image_analysis_api_key="image-key",
        image_analysis_temperature=0.2,
        asset_phrase_model_name="gpt-5.5",
        asset_phrase_base_url="https://primary.example.test/v1",
        asset_phrase_api_key="phrase-key",
        asset_phrase_temperature=0.2,
        search_fallback_model_name="gpt-5.5",
        search_fallback_base_url="https://fallback.example.test/v1",
        search_fallback_api_key="search-fallback-key",
        search_fallback_temperature=0.2,
    )
    monkeypatch.setattr(factory, "get_settings", lambda: settings)

    image = factory.get_model_provider(purpose="image_analysis")
    phrase = factory.get_model_provider(purpose="asset_phrase")
    search = factory.get_model_provider(purpose="search")

    assert isinstance(image, OpenAICompatibleModelProvider)
    assert image.api_key == "image-key"
    assert isinstance(phrase, OpenAICompatibleModelProvider)
    assert phrase.api_key == "phrase-key"
    assert isinstance(search, FallbackModelProvider)
    assert [item.api_key for item in search.providers] == [
        "search-primary-key",
        "search-fallback-key",
    ]
    assert [item.base_url for item in search.providers] == [
        "https://primary.example.test/v1",
        "https://fallback.example.test/v1",
    ]


def test_provider_order_uses_only_explicit_slots():
    assert factory._provider_order("primary") == ("primary",)
    assert factory._provider_order("fallback2") == ("fallback2",)
    assert factory._provider_order("") == (
        "primary",
        "fallback1",
        "fallback2",
    )


def test_fallback_chain_exposes_attempt_count_for_search_budget():
    providers = [
        OpenAICompatibleModelProvider(
            base_url=f"https://provider-{index}.example.test/v1",
            api_key=f"key-{index}",
            model_name=f"model-{index}",
        )
        for index in range(3)
    ]
    chain = FallbackModelProvider(providers)

    assert chain.attempt_count == 3
    assert _provider_attempt_count(chain) == 3
    assert _provider_attempt_count(providers[0]) == 1


def test_fallback_chain_records_provider_attempts():
    class Provider:
        configured = True

        def __init__(self, provider_label: str, *, fails: bool):
            self.provider_label = provider_label
            self.model_name = "gpt-5.5"
            self.fails = fails

        def generate_json(self, _request):
            attempt = {
                "provider": self.provider_label,
                "model": self.model_name,
                "status": "failed" if self.fails else "ok",
                "duration_ms": 12,
                "error": "模型服务调用失败" if self.fails else "",
            }
            if self.fails:
                raise ModelProviderError("模型服务调用失败", attempts=(attempt,))
            return ModelCallResult({"ok": True}, (attempt,))

    chain = FallbackModelProvider(
        [
            Provider("laozhang", fails=True),
            Provider("ohmygpt", fails=False),
        ]
    )

    result = chain.generate_json(
        ModelRequest(task="search_system_routing", prompt="")
    )
    assert result.value == {"ok": True}
    assert [(item["provider"], item["status"]) for item in result.attempts] == [
        ("laozhang", "failed"),
        ("ohmygpt", "ok"),
    ]


def test_fallback_chain_stops_after_request_cancellation():
    called = []

    class Provider:
        configured = True

        def __init__(self, name: str, *, cancel: bool = False):
            self.provider_label = name
            self.model_name = "gpt-5.5"
            self.cancel = cancel

        def generate_json(self, request):
            called.append(self.provider_label)
            if self.cancel:
                assert request.cancellation is not None
                request.cancellation.cancel()
                raise ModelProviderError("模型服务调用失败")
            return {"ok": True}

    chain = FallbackModelProvider(
        [
            Provider("first", cancel=True),
            Provider("second"),
        ]
    )
    cancellation = CancellationSignal()

    with pytest.raises(ModelProviderError):
        chain.generate_json(
            ModelRequest(
                task="search_system_routing",
                prompt="Return JSON",
                cancellation=cancellation,
            )
        )

    assert called == ["first"]


def test_fallback_chain_does_not_start_when_request_is_already_cancelled():
    called = []

    class Provider:
        configured = True

        def __init__(self, name: str):
            self.provider_label = name
            self.model_name = name

        def generate_json(self, _request):
            called.append(self.provider_label)
            return {"ok": True}

    chain = FallbackModelProvider([Provider("first"), Provider("second")])
    cancellation = CancellationSignal()
    cancellation.cancel()

    with pytest.raises(ModelProviderCancelled, match="已取消"):
        chain.generate_json(
            ModelRequest(
                task="search_system_routing",
                prompt="Return JSON",
                cancellation=cancellation,
            )
        )

    assert called == []


def test_fallback_chain_keeps_attempts_request_scoped_under_concurrency():
    class Provider:
        configured = True
        provider_label = "shared-provider"
        model_name = "shared-model"

        def generate_json(self, request):
            sleep(0.01 if request.input_text == "slow" else 0.001)
            attempt = {
                "provider": self.provider_label,
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 1,
                "request": request.input_text,
            }
            return ModelCallResult(
                {"request": request.input_text},
                (attempt,),
            )

    chain = FallbackModelProvider([Provider()])

    def run(input_text: str):
        return chain.generate_json(
            ModelRequest(
                task="search_system_routing",
                prompt="Return JSON",
                input_text=input_text,
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, "slow"), pool.submit(run, "fast")]
        results = [future.result() for future in futures]

    assert {result.value["request"] for result in results} == {"slow", "fast"}
    assert {
        result.attempts[0]["request"]
        for result in results
    } == {"slow", "fast"}


def test_ai_service_fallback_chain_tries_next_provider_on_invalid_structure():
    class Provider:
        configured = True
        model_name = "gpt-5.5"

        def __init__(self, provider_label: str, payload):
            self.provider_label = provider_label
            self.payload = payload

        def generate_json(self, _request):
            attempt = {
                "provider": self.provider_label,
                "model": self.model_name,
                "status": "ok",
                "duration_ms": 9,
                "error": "",
            }
            return ModelCallResult(
                self.payload,
                (attempt,),
            )

    chain = FallbackModelProvider(
        [
            Provider(
                "laozhang",
                {
                    "original_query": "期中期末一键划重点",
                    "route_type": "single_system",
                    "candidate_systems": [],
                },
            ),
            Provider(
                "ohmygpt",
                {
                    "original_query": "期中期末一键划重点",
                    "route_type": "single_system",
                    "candidate_systems": [
                        {
                            "code": "sync_exam",
                            "relation": "primary",
                            "reason": "考试阶段重点梳理",
                            "weight": 0.97,
                        }
                    ],
                },
            ),
        ]
    )

    result = AiService(chain).route_search_system("期中期末一键划重点")

    assert [item.code for item in result.value.candidate_systems] == ["sync_exam"]
    assert [(item["provider"], item["status"]) for item in result.attempts] == [
        ("laozhang", "failed"),
        ("ohmygpt", "ok"),
    ]
    assert result.attempts[0]["error"] == "模型返回内容未通过项目校验"


def test_fallback_chain_error_includes_sanitized_attempt_summary():
    class FailingProvider:
        configured = True
        model_name = "gpt-5.5"

        def __init__(self, provider_label: str):
            self.provider_label = provider_label

        def generate_json(self, _request):
            attempt = {
                "provider": self.provider_label,
                "model": self.model_name,
                "status": "failed",
                "duration_ms": 7,
                "error": "模型服务返回异常状态：400",
            }
            raise ModelProviderError(
                "模型服务返回异常状态：400",
                attempts=(attempt,),
            )

    chain = FallbackModelProvider(
        [FailingProvider("laozhang"), FailingProvider("ohmygpt")]
    )

    try:
        chain.generate_json(ModelRequest(task="search_system_routing", prompt=""))
    except ModelProviderError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected fallback chain to fail")

    assert "laozhang/gpt-5.5 failed" in message
    assert "ohmygpt/gpt-5.5 failed" in message
    assert "sk-" not in message
