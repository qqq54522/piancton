---
name: maintain-piancton-architecture
description: "在卖点智库中新增功能、重构、修复或审查代码时维护API、Service、Domain、Repository、Storage、ModelProvider、搜索编排和前端组件边界。用于任何可能改变项目结构或图片搜索链路的开发任务；必须先读取项目总纲和护栏，并同步测试与决策记录。"
---

# 维护卖点智库架构

## 开始前

1. 完整阅读项目 `AGENTS.md`、`docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 和 `docs/DEVELOPMENT_GUARDRAILS.md`。
2. 根据任务读取相关正式 Skill、服务、Schema、迁移和测试；涉及六体系卖点时使用 `understand-image-search-intent` 或 `govern-selling-point-knowledge`。
3. 检查工作树并保留用户已有改动；不重置、不覆盖不相关文件。

## 实施纪律

- 完整读取 `RULES.md` 并遵守依赖方向。
- API 只做鉴权和传输；Service 编排用例；Domain 保存纯规则；Repository 只读写数据库；Storage 只处理文件；Provider 只处理厂商协议。
- 搜索理解、召回、过滤、评分、响应、外部分支和唯一一次 Reranker 保持独立边界。
- 可版本化规则进入 taxonomy、Skill 或独立策略服务，不在编排器追加业务词特判。
- 数据模型、搜索契约或业务边界变化先新增总纲决策；Phase/范围变化同步项目日志与当前执行文档。
- 实现后运行与风险相称的专项测试、全量测试、静态检查和真实评测。

## 交付

说明修改文件、迁移、测试结果、没有改变的业务事实、遗留风险和是否需要重启。没有完成验证时不要宣称完成。

## 资源

- `RULES.md`：当前项目依赖方向与分层边界。

