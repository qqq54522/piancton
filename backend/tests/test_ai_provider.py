from pathlib import Path
from types import SimpleNamespace

from app.ai import factory
from app.ai.contracts import ModelRequest
from app.ai.fallback import FallbackModelProvider
from app.ai.openai_compatible import OpenAICompatibleModelProvider
from app.api.dependencies import _provider_attempt_count


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

    assert result["original_query"] == "老师"
    assert result["normalized_query"] == "老师"


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

    assert "第一层路由决策员" in router_system
    assert "不得提前判断卖点或具体图片" in router_system
    assert "第二层卖点决策员" in selling_point_system
    assert "不得让通用结果词或方法细节覆盖更主要的入口证据" in selling_point_system


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


def test_provider_order_keeps_unspecified_slots_as_fallbacks():
    assert factory._provider_order("fallback2") == (
        "fallback2",
        "primary",
        "fallback1",
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
