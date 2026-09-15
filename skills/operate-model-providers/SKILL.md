---
name: operate-model-providers
description: "审计卖点智库历史文本/视觉模型 Provider，防止已退役的 API 中心、Kimi、DeepSeek、GPT、Embedding 或 Reranker 被误接回当前运行时。当前在线 AI 能力统一由 Viking AI Search 提供。"
---

# 运维模型 Provider

当前业务运行时不得构造或调用通用 `ModelProvider`。执行历史代码清理、迁移审计或未来重新立项前，完整读取 `RULES.md` 和总纲中当前单一 AI Search、数据外发与评测决策。

## 工作流

1. 确认当前页面、路由、后台 Worker 和业务依赖只调用 Viking AI Search。
2. 搜索旧 `ModelProvider`、API Center、Embedding、Reranker 和知识库路由引用，区分历史迁移资料与当前可达运行代码。
3. 历史数据库表和迁移不做破坏性删除；页面、HTTP API、Worker 和业务消费者必须不可达。
4. 部署模板不得再要求额外模型 Key；旧 Key 即使残留在服务器环境文件中也必须被忽略。
5. 用自动化测试验证退役路由返回 404，Agent 无 AI Search 时明确失败且不会调用第二供应商。
6. 未来若要恢复额外 Provider，必须由用户明确改变架构决策并新增总纲记录，不可作为临时降级偷偷接入。

## 资源

- `RULES.md`：中立协议、任务目录、降级和安全边界。
