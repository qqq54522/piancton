from pathlib import Path

from app.ai.contracts import ModelRequest
from app.ai.openai_compatible import OpenAICompatibleModelProvider


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
                            '```json\n{"original_query":"老师",'
                            '"normalized_query":"老师"}\n```'
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
