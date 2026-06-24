# 模型 Provider Skill

用途：替换文本或视觉模型时，只新增适配器，不修改业务规则。

## Provider 协议

```python
class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(self, request: ModelRequest) -> dict[str, Any]: ...
```

Supported tasks:

- `image_content_analysis`
- `secondary_selling_point_classification`
- `search_intent_understanding`
- `copy_selling_point_matching`

Environment placeholders:

- `MODEL_PROVIDER`
- `MODEL_NAME`
- `MODEL_BASE_URL`
- `MODEL_API_KEY`

Business services must remain unaware of vendor SDKs and response envelopes.
