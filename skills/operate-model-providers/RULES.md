# 模型 Provider 运行规则

用途：替换或增加文本/视觉模型时只调整适配器与配置，不修改业务规则。

## 中立协议

```python
class ModelProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def generate_json(
        self,
        request: ModelRequest,
    ) -> ModelCallResult[dict[str, Any]]: ...

    def generate_validated_json(
        self,
        request: ModelRequest,
        validator: Callable[[dict[str, Any]], T],
    ) -> ModelCallResult[T]: ...
```

`ModelCallResult` 按请求返回模型值和本次调用 attempts；失败则从异常的
`attempts` 读取本次调用记录。Provider/Service 实例不得保存可被并发请求覆盖的
实例级调用遥测状态（例如 `last_attempts` 或 `last_call_attempts`）。

当前运行任务：

- `image_content_analysis`
- `asset_search_phrase_generation`
- `search_system_routing`
- `search_intent_understanding`
- `search_proof_point_understanding`
- `search_candidate_review`
- `search_result_recommendation_reason`
- `copy_selling_point_matching`
- `asset_agent_chat`

## 边界

- 厂商 URL、鉴权、请求/响应 envelope 和多模态编码只存在于适配器。
- Service、Repository、业务 taxonomy 和 Skill 不导入厂商 SDK 或厂商响应结构。
- Provider 返回先 normalizer，再 Pydantic schema，再业务目录校验；失败不允许部分持久化。
- 多 Provider 按显式顺序逐级尝试，每一级保留自己的任务预算；不得让第一级耗尽整条链。
- 业务高置信本地路径允许跳过模型；模型失败不得清空已有可信本地结果。
- 日志不得记录 API key、Authorization、完整 Prompt、业务图片字节或未脱敏外部响应。
- 批量外发评测必须取得明确授权，并单独报告业务准确性与 Provider 可用性。
