---
name: operate-model-providers
description: "接入、切换、诊断和验证卖点智库的文本或视觉模型Provider、Kimi到DeepSeek到GPT降级链、超时预算与Provider级遥测。用于模型配置、适配器开发、鉴权排查或降级验证；不得把厂商协议写进业务服务，也不得暴露或移动密钥。"
---

# 运维模型 Provider

保持业务服务只依赖中立 `ModelProvider`。执行接入或诊断前完整读取 `RULES.md` 和总纲中当前 Provider、超时、数据外发与评测决策。

## 工作流

1. 识别任务需要文本、视觉或多模态能力，并核对其现有 JSON schema。
2. 新厂商只增加适配器或配置槽位，不修改业务 Prompt、卖点目录和审核规则。
3. 使用最小无敏感内容请求检查鉴权、模型名、JSON 模式和多模态兼容性。
4. 按 `MODEL_PROVIDER_ORDER` 组装去重后的 Provider 链；当前顺序保持 Kimi → DeepSeek → GPT，除非用户明确调整。
5. 每次尝试分别记录 provider、model、task、耗时、状态和安全错误摘要，不记录密钥、完整请求体或图片内容。
6. 用故障注入验证前一 Provider 失败时后备仍有完整预算；再用获授权的小样本验证真实调用。
7. 改动 Provider 后运行模型适配器测试、搜索降级测试和必要的端到端评测；模型连通不等于业务准确性通过。

## 资源

- `RULES.md`：中立协议、任务目录、降级和安全边界。

