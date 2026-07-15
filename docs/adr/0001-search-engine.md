# ADR 0001：Meilisearch 作为可选派生搜索索引

状态：已采用
日期：2026-06-25

## 背景

项目需要支持标题、文件名、人工标签、AI 隐性内容标签、业务标签和自然语言表达的搜索。本地开发仍以 SQLite 为主，部署环境以 PostgreSQL 为主，数据库必须继续作为事实源。

仅靠数据库模糊搜索可以兜底，但中文分词、错字、前缀和更自然的业务搜索体验有限。因此需要一个可以随时重建、故障时不阻断主流程的搜索索引。

## 决策

使用 Meilisearch Community Edition 作为可选派生搜索索引。

当前结构（Phase 4～6）：

```text
SQLite / PostgreSQL：权威主数据
Meilisearch：可重建搜索索引
SearchService：统一搜索门面
AsyncSearchOrchestrator：数据库 / Meilisearch / Embedding / 查询理解并行融合
SearchRerankCoordinator：总截止内最多一次重排
```

Meilisearch 不保存唯一事实，不承接权限判断，不阻断上传、编辑、删除、恢复和 AI 分析。

## 原因

- 中文搜索体验比纯数据库模糊搜索更适合当前素材库。
- Docker Compose 中可以作为单独 profile 启动，不影响默认服务。
- 索引文档可由数据库和 AI 分析结果完全重建。
- 搜索服务异常时，后端已有数据库搜索兜底。
- 当前规模不需要 Elasticsearch/OpenSearch 这类更重的集群方案。

## 当前实现

- `SEARCH_BACKEND=database` 是默认路径，数据库概念/短语召回始终可用。
- 设置 `SEARCH_BACKEND=meilisearch` 且配置 `MEILISEARCH_URL` 后启用关键词增强分支。
- 上传、改标题、素材版本变化、删除、恢复、永久删除和 AI 分析完成后，会尽力同步索引。
- 同步失败只记录日志，不影响主流程。
- `scripts.verify_search_index` 用于验证真实 Meilisearch 写入和查询。
- `scripts.rebuild_search_index` 可从主数据库重建正式索引。
- 普通用户不选择搜索模式；`search_mode` 只记录本次实际服务来源。

## 降级策略

- Meilisearch 不可用：返回数据库模糊搜索结果，并标记 fallback。
- 模型 Provider 未配置：跳过复杂查询理解，仍保留本地概念理解和数据库搜索。
- 索引落后或丢失：用重建脚本从主数据库恢复。

## 重新评估条件

出现以下情况时再评估 pgvector、Qdrant 或 OpenSearch：

- 图片规模或并发超过单节点 Meilisearch 能力。
- 需要成熟的以图搜图、多向量检索或复杂向量过滤。
- 真实搜索评测证明 Meilisearch 的中文召回无法满足业务。
- 运维环境已经具备更重搜索集群的维护能力。
