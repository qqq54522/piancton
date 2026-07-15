# 统一搜索、AI 理解与图片语义分析

状态：Phase 4～6 工程完成。普通业务用户和后端请求均不再存在“精准/智能”模式选择；系统使用一条自动限时、缓存、可降级的搜索编排。

> 当前阶段、数据边界和后续验收以 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为唯一事实来源。

## 一个搜索入口

业务用户只输入想找的业务点、用户痛点、结果诉求、画面、渠道或尺寸，不需要理解内部召回方式。

六大体系是稳定业务地图和可选快捷筛选：

- 未选择体系时，搜索允许跨体系召回。
- 用户显式选择体系时，该体系才进入硬过滤。
- `search_mode` 只描述本次实际服务来源，例如数据库模糊路径或 Meilisearch，不是用户可选模式。

## 在线搜索编排

在线链路按配置启动以下来源：

```text
本地概念与概念搜索表达 ─┐
数据库图片/素材短语召回 ─┼─> 候选融合 ─> 体系过滤 ─> 素材组折叠 ─> 一次可选 Reranker
Meilisearch 关键词召回 ───┤
Embedding 语义召回 ──────┤
复杂查询模型理解 ─────────┘
```

职责边界：

- `SearchService` 只装配依赖并提供同步/异步门面。
- `AsyncSearchOrchestrator` 只串联流水线。
- `SearchExternalBranches` 管理外部分支、缓存和主会话水合。
- `SearchRerankCoordinator` 管理总截止内唯一一次重排。
- 外部分支先返回轻量候选 ID 或向量，不在线程间共享 SQLAlchemy Session。

默认时间预算：

| 环节 | 当前预算 |
|---|---:|
| 总截止 | 2.5 秒 |
| Meilisearch | 0.2 秒 |
| Embedding | 1.8 秒；高置信本地概念查询跳过 |
| 复杂查询理解 | 0.9 秒 |
| Top 20 Reranker | 1.4 秒，且受剩余总截止约束 |

这些数值来自首张真实素材和当前 Provider 的单次延迟校准；样本仍不足，后续需要随代表素材和真实查询继续完成 P95 验收。

## 降级规则

- Meilisearch 不可用：继续数据库概念/短语召回和其他可用分支。
- Embedding 不可用：继续数据库与 Meilisearch。
- 查询理解模型不可用：继续本地概念理解和已有召回。
- Reranker 不可用或超时：使用本地融合分数排序。
- 所有外部能力不可用：数据库路径仍必须返回可用结果。

生成式“图片摘要裁判”已经退出在线链路；候选融合后最多调用一次 Reranker。

## 上传阶段的 AI

设计师首次上传只要求图片文件，标题可以由文件名生成。业务概念、渠道、素材独有搜索语和延展尺寸均可后补。

模型 Provider 已配置时，上传后可以异步执行：

- OCR 与画面事实提取；
- 主体、场景、动作、风格和可见产品功能分析；
- Semantic Profile V2；
- 客观 `content_tags`；
- 业务概念关系建议；
- 素材独有搜索表达；
- Embedding 与派生搜索索引刷新。

Provider 未配置或分析失败不影响图片上传、预览、下载和人工关系维护。

## 客观语义与业务事实分离

图片客观语义保存在 Semantic Profile V2 和 `content_tags`。AI 对业务含义的判断只能写成素材概念关系建议：

- `origin=ai`；
- `review_status=pending`；
- 关系为 `expresses` 或 `supports`；
- 必须给出证据与相邻概念排除边界。

负责人确认后形成 `origin=manual`、`review_status=accepted` 的业务事实。AI 重跑不得覆盖人工确认或人工拒绝结果。

## 业务概念与搜索语言

- 六大体系稳定节点位于 `tags`。
- 可变化业务概念位于 `business_concepts`。
- 通用业务话术位于 `concept_search_phrases`，在概念层复用。
- 图片独有画面或场景表达位于 `asset_search_phrases`。
- 图片与概念的主要表达、支持或排除关系位于 `asset_concept_links`。

当前 16 个概念和初始表达由 taxonomy 源文件幂等初始化。概念层是运行事实来源；静态种子与 AI Prompt 如何跟随数据库概念变更，是进入概念长期运营前必须收口的已知技术债。

## 搜索结果与反馈

搜索按素材组返回：

- 同一主视觉的横版、竖版和渠道延展只占一张结果卡；
- 用户在卡片内选择需要的尺寸或渠道；
- 匹配原因来自真实命中链路，不由模型自由编写；
- 单结果“不相关”反馈记录查询、图片和素材组，只用于搜索优化，不修改发布审批或人工概念关系。

## 当前配置边界

核心配置包括：

```env
SEARCH_BACKEND=database
SEARCH_TOTAL_TIMEOUT_SECONDS=2.5
SEARCH_MEILISEARCH_TIMEOUT_SECONDS=0.2
SEARCH_EMBEDDING_TIMEOUT_SECONDS=1.8
SEARCH_UNDERSTANDING_TIMEOUT_SECONDS=0.9
SEARCH_RERANKER_TIMEOUT_SECONDS=1.4
SEARCH_CANDIDATE_LIMIT=20
```

需要时再分别配置模型 Provider、Meilisearch、Embedding 和 Reranker。任何一个外部能力都不是上传或基础搜索的单点依赖。

## 当前验收边界

- 工程故障注入已经覆盖任一外部分支失败时仍有数据库结果。
- 当前正式素材库已有 1 张已审核代表主图；单图、单查询验证不代表整体搜索质量。
- 再补充 2～5 张代表素材并累计绑定 10～20 条真实查询后，重新生成 Phase 0/4 基线。
- 开启实际外部 Provider 后，执行全链路质量、超时、降级和 P95 验收。
