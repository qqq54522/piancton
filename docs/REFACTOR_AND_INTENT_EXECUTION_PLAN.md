# 项目改造与意图识别施工总控

> **历史文档说明**：本文是 2026-06-28 旧六阶段施工总控，相关工程已经完成并被新的图片搜索改造 Phase 0～6 取代。本文只用于追溯，不再是当前施工入口；当前唯一事实来源是 `IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`。

版本：2026-06-28  
定位：下一轮项目改造的唯一施工入口与执行标准。  
目标：先把项目结构拆清楚、边界收住，再接入业务话术词库和搜索意图识别，避免把项目越改越重。

本文件是后续改造的总控文档。实际施工时以本文档的顺序、边界和验收标准为准；其他文档作为事实来源、背景说明或专项参考。

如果其他文档与本文档出现冲突：

1. 当前真实代码和测试结果优先。
2. 架构边界以 `docs/ARCHITECTURE.md` 为硬约束。
3. 改造顺序、阶段边界和是否开工，以本文档为准。
4. 搜索话术和标签材料以专项文档为参考，不直接替代本文档中的施工顺序。

---

## 1. 先看哪些文档

当前项目文档按用途分成四类。

本文档不是要替代所有文档，而是把它们收束成一个执行入口：

```text
README / ARCHITECTURE / SEARCH_MODES_AND_AI
  提供当前项目事实

OPTIMIZATION_PLAN
  提供长期优化纪律

SEARCH_BUSINESS_INTENT_MAP / TAGGING_SYSTEM_IMPROVEMENT_PLAN
  提供业务意图和标签改造材料

REFACTOR_AND_INTENT_EXECUTION_PLAN
  决定现在按什么顺序施工
```

### 1.1 当前事实与运行入口

- `README.md`  
  项目能力、本地开发、Docker 部署、服务器验收入口。

- `docs/ARCHITECTURE.md`  
  当前架构边界、强制约束、图片生命周期、部署事实源。

- `docs/SEARCH_MODES_AND_AI.md`  
  当前精准搜索、智能搜索、AI 图片语义补标、Embedding/Reranker 位置。

### 1.2 优化路线与纪律

- `docs/OPTIMIZATION_PLAN.md`  
  总优化路线、禁止事项、每轮验收格式、已完成改造记录。

### 1.3 这次新增的业务理解材料

- `docs/SEARCH_BUSINESS_INTENT_MAP.md`  
  从业务原文档整理出的业务话术词库、家长痛点、意图簇和语义总结匹配信号。

- `docs/TAGGING_SYSTEM_IMPROVEMENT_PLAN.md`  
  标签系统和 AI 打标如何分层治理：稳定二级标签、意图簇、语义总结、隐性标签。

### 1.4 部署与决策记录

- `docs/SERVER_DEPLOYMENT_CHECKLIST.md`  
  服务器部署验收记录。

- `docs/adr/0001-search-engine.md`  
  搜索引擎选型与 Meilisearch 的边界。

---

## 2. 当前总判断

现在不要直接把业务话术词库塞进搜索代码，也不要马上大改标签系统。

原因：

- 项目已经有一定重量，`ImageService` 和 `SearchService` 仍需要继续收口。
- 搜索问题暴露出的不是“标签不够多”，而是“业务话术没有稳定归一到核心标签”。
- 如果现在直接把大量话术塞进 `taxonomy/catalog.json`、AI prompt 或 `SearchService`，后续会更难维护。

正确顺序：

```text
先改造项目边界
  ↓
再接业务意图层
  ↓
再优化搜索排序和结果收紧
  ↓
最后扩展更多意图簇和评测集
```

这次改造的核心原则：

> 不把项目加厚，而是把业务理解能力外挂成独立一层。

---

## 3. 覆盖范围与不覆盖范围

本文档覆盖下一阶段项目改造的主路径，包括：

- 后端服务边界收口。
- 图片上传、删除、恢复、打标、AI 分析相关职责拆分。
- 搜索服务边界预拆。
- 业务意图识别层的接入顺序。
- 搜索强意图结果收紧。
- AI 图片语义总结增强。
- 搜索评测集建设。
- 每阶段验收口径。

本文档不直接覆盖：

- 服务器生产部署的逐项操作，仍以 `docs/SERVER_DEPLOYMENT_CHECKLIST.md` 为准。
- 搜索引擎选型争议，仍以 `docs/adr/0001-search-engine.md` 为准。
- 业务话术全集的内容维护，仍在 `docs/SEARCH_BUSINESS_INTENT_MAP.md` 中扩展。
- 标签和 AI 打标的长期治理细节，仍在 `docs/TAGGING_SYSTEM_IMPROVEMENT_PLAN.md` 中扩展。

这些专项文档可以补充本文档，但不能绕过本文档直接开工。

---

## 4. 开工前准备清单

任何代码改造开始前，必须先完成本节检查。

### 4.1 代码状态

- [ ] 确认当前分支和工作区状态。
- [ ] 明确哪些未提交改动是本轮相关，哪些是历史遗留。
- [ ] 不回滚用户已有改动。
- [ ] 确认本轮是否需要新建分支。

建议命令：

```bash
git status --short
git branch --show-current
```

### 4.2 当前能力基线

- [ ] 后端测试能跑通，或者明确当前已知失败项。
- [ ] 前端 typecheck 能跑通，或者明确当前已知失败项。
- [ ] 上传、详情、打标、删除、恢复、搜索主流程当前能用。
- [ ] AI Provider 是否配置清楚。
- [ ] Meilisearch 是否启用清楚。

建议记录：

```text
后端测试：
前端检查：
Docker 状态：
AI Provider：
Meilisearch：
当前已知问题：
```

### 4.3 数据与环境保护

- [ ] 如果使用真实数据，先确认数据库和图片目录已有备份。
- [ ] 不在未备份真实数据上做批量迁移、批量重分析、批量删除。
- [ ] 本轮默认不改数据库 schema，除非任务单明确说明。
- [ ] 本轮默认不批量重建旧图 AI 分析结果。

### 4.4 文档准备

- [ ] 本文档已读。
- [ ] `docs/ARCHITECTURE.md` 的强制边界已读。
- [ ] `docs/OPTIMIZATION_PLAN.md` 的禁止事项已读。
- [ ] 本轮任务只解决一个阶段目标。

### 4.5 搜索评测准备

如果本轮涉及搜索或意图识别，必须先准备至少 3 个已知问题案例：

- [ ] `AI错题本`
- [ ] `AI拍题精学`
- [ ] `专家规划`

每个案例至少包含：

- query
- 真实意图
- 期望标签
- 当前错误表现
- 截图或结果记录

### 4.6 2026-06-28 开工前基线记录

本次基线确认来自当前仓库、线程 `019f0c41-e1e6-7003-b9ee-08242cef84f9` 和 2026-06-28 截图内容。

代码状态：

- 当前分支：`main`。
- 工作区已有文档改动和旧文档删除，后续施工不得回滚用户已有改动。
- 本次准备阶段只补充本文档基线记录，不改业务代码。

能力基线：

- 后端测试：`./.venv/bin/python -m pytest`，56 passed。
- 前端检查：`npm run typecheck`，通过。
- Docker 状态：`backend`、`web`、`postgres`、`meilisearch` 均为 healthy。
- Web 健康检查：`http://127.0.0.1/health` 返回 ready。
- 本地 Vite dev server：`127.0.0.1:5173` 当前未运行；Docker Web `:80` 可用。
- Meilisearch：服务健康；索引统计需要 master key，不作为本轮开工门槛。
- AI Provider / Embedding / Reranker：环境中已配置对应 provider，施工中不得泄露密钥值。

数据基线：

- Docker PostgreSQL 当前图片数为 0，适合做结构改造和空库验证。
- `data/piancton.db` 存在，但 Alembic 版本停在 `20260623_0002`，缺少后续业务标签表，不适合作为本轮 AI/业务标签验收数据源。
- 如需用真实图片验证搜索质量，必须先确认真实数据所在环境，并确认备份。

服务边界基线：

- `ImageService` 当前同时承担列表、详情、上传、标题、人工标签、AI 建议审核、删除、恢复、永久删除、下载计数和索引同步。
- `SearchService` 当前同时承担搜索编排、Meilisearch、Embedding、Reranker、数据库召回、评分、分级和匹配原因组装。
- 第一阶段仍以 `ImageLifecycleService` 和 `ImageTaggingService` 拆分为优先，不直接做业务意图词库和搜索排序改动。

已知风险：

- 如果直接在 `SearchService` 中加业务话术规则，会违背本文档“先减重，再接意图”的顺序。
- 如果直接使用旧 SQLite 数据验收，会误判当前业务标签能力。
- 如果真实素材在服务器或其他数据库中，必须先做只读数据确认，再跑搜索评测。

### 4.7 2026-06-28 六阶段完成后复核

六阶段改造已经完成，本文档仍作为施工入口，但下一轮不再重复执行阶段一到阶段六。

当前完成状态：

- `ImageService` 已拆出生命周期、标签审核和 AI 分析持久化相关服务。
- `SearchService` 已拆出 query expansion、query understanding、ranking 和语义画像相关边界。
- `taxonomy/business_intents.json` 已扩展到 16 个业务意图，覆盖六大体系和全部当前二级业务标签。
- `taxonomy/search_eval_cases.json` 已扩展到 50 条搜索评测用例。
- 前端主搜索只保留精准搜索和智能搜索两种入口。

当前复核结果：

- 后端全量测试：83 passed。
- 后端 Ruff：通过。
- 后端 Pyright：通过。
- 前端 TypeScript：通过。
- 前端 Vitest：通过。
- 搜索评测资产：50 条结构校验通过。

下一轮优先级：

- 先清理前端旧类型、文档状态漂移和旧文档引用。
- 再基于真实素材库跑搜索评测，记录 top3 命中和 top5 误召回。
- 暂不继续大拆 `SearchRankingService`、图片公共基础服务或前端大组件，除非真实评测暴露明确阻塞。

---

## 5. 开工门槛

满足以下条件，才可以进入代码改造：

- 当前主流程没有未解释的严重故障。
- 本轮目标可以用一句话说明。
- 本轮不做事项已经明确。
- 已知道改动会触及哪些模块。
- 已知道验收要跑哪些测试。

如果不能满足，先补文档、补测试记录或补现状排查，不直接写代码。

---

## 6. 本轮施工目标

本轮不是做完整大重构，也不是一次性把搜索做到最终形态。

本轮目标：

1. 让核心服务边界更清楚。
2. 给业务意图识别预留独立模块位置。
3. 用最小范围验证 `AI错题本`、`AI拍题精学`、`专家规划` 三个意图簇。
4. 避免继续扩大 `ImageService`、`SearchService` 和 `taxonomy/catalog.json` 的职责。

---

## 7. 推荐施工顺序

### 阶段 0：改造前冻结与确认

目标：确认当前代码和文档状态，避免边改边偏。

任务：

- 确认 `README.md`、`ARCHITECTURE.md`、`OPTIMIZATION_PLAN.md` 与当前真实代码一致。
- 确认服务器部署验收是否已经完成；如果没有，不把项目标为生产已验证。
- 确认当前搜索测试问题都先记录为评测案例，不急着写规则修补。
- 确认本轮只解决一类问题：服务边界和后续意图识别承接。

验收：

- 能明确本轮不做的事。
- 能明确本轮会动哪些模块。

本阶段不要做：

- 不新增大量标签。
- 不大改前端页面。
- 不把意图规则写死在 `SearchService`。

### 阶段 1：服务边界收口

目标：先降低项目重量，让后面的搜索/AI 意图能力有干净入口。

当前已有基础：

- `ImageAnalysisService` 已经独立存在。
- `search_index.py`、`search_index_sync.py`、`meilisearch_client.py` 已经把部分索引职责拆出。
- `taxonomy_catalog.py` 已经承担稳定目录读取和校验。

建议继续拆：

```text
ImageService
  保留图片读取、列表、详情聚合入口

ImageUploadService
  负责上传、文件校验、缩略图、入库前后清理

ImageLifecycleService
  负责删除、恢复、永久删除

ImageTaggingService
  负责人工标签、AI 建议标签、确认/驳回状态

ImageAnalysisService
  保持负责 analysis run、AI 结果落库、分析状态

SearchService
  保留搜索编排入口

SearchIndexService
  负责索引文档构造、同步、重建
```

第一阶段建议先拆最有收益的两块：

1. `ImageLifecycleService`
2. `ImageTaggingService`

原因：

- 删除/恢复/purge 和标签状态流转都容易继续膨胀。
- 它们和搜索意图识别关系不强，先拆风险较低。

验收：

- `ImageService` 变薄。
- 原上传、列表、详情、删除、恢复、打标行为不变。
- 后端测试通过。
- 架构测试补上“不允许 ImageService 重新持有过多 AI/标签持久化职责”的规则。

### 阶段 2：搜索服务边界预拆

目标：给意图识别、召回、排序留出位置，但先不做复杂搜索升级。

建议拆成：

```text
SearchService
  搜索总编排，处理模式、降级、响应组装

QueryExpansionService
  当前 taxonomy aliases / evidence / copy_points 扩展

QueryUnderstandingService
  后续承接业务话术 -> 主意图标签

SearchRankingService
  后续承接 S/A/B/C 分级、兜底收紧、匹配原因

ImageSemanticProfileService
  把 image_summary、content_tags、business labels 拼成可搜索画像
```

本阶段先做：

- 把已有 query expansion 从 domain 函数逐步包成清晰入口。
- 把搜索结果评分/匹配原因的纯逻辑从 `SearchService` 中分出去。
- 保持外部 API 不变。

本阶段不要做：

- 不直接引入完整业务意图词库。
- 不一次性重写 Meilisearch 查询。
- 不改搜索前端交互。

验收：

- 搜索结果和现有行为基本一致。
- 搜索相关单测通过。
- 新增边界测试，防止 Repository 反向依赖搜索业务。

### 阶段 3：最小业务意图层

目标：用独立配置承接业务话术，不污染 catalog 和 SearchService。

新增建议：

```text
taxonomy/business_intents.json
```

先只放三个意图簇：

- `AI错题本`
- `AI拍题精学`
- `专家规划`

结构建议：

```json
{
  "code": "ai_error_book_intent",
  "target_system_code": "sync_self_study",
  "target_label_code": "ai_error_book",
  "phrases": [],
  "pain_points": [],
  "must_have_concepts": [],
  "nice_to_have_concepts": [],
  "exclude_concepts": [],
  "result_policy": "strict_allow_few_results"
}
```

同步新增：

```text
backend/app/domain/business_intents.py
backend/app/services/query_understanding_service.py
```

职责：

- `business_intents.py` 只负责读取、校验、渲染 prompt/规则材料。
- `QueryUnderstandingService` 负责把 query 归一到主意图和二级标签。
- `SearchService` 只调用它，不内置业务话术规则。

验收：

- 三个意图簇的精准词、功能表达、痛点表达都能归一到正确标签。
- 即使模型 Provider 不可用，也能用本地词库做基础归一。
- 不影响现有精准搜索。

### 阶段 4：强意图搜索收紧

目标：解决现在测试中最明显的问题：正确图被放在 C 级兜底，泛学习图片补满页面。

规则：

- 当 `primary_intent_confidence` 足够高时，启用 strict 策略。
- strict 策略下，主结果只保留强相关和中相关。
- C 级兜底不进入主结果区。
- 强相关图片只有 1 张，就只返回 1 张。
- 匹配原因必须说明命中了什么：主标签、业务话术、语义总结、排除项。

先验证三个 query 簇：

- 错题本 / 上传错题 / 整理错题费功夫又容易忘
- 拍题 / 体现拍题精学 / 拍题只抄答案考试不会
- 专家规划 / 体现专家规划 / 出卷人编教材的人设计课程

验收：

- Top 1 命中正确图。
- Top 3 不被泛学习图污染。
- 强相关不足时不强行补满 15 张。
- 前端能看到合理匹配原因。

### 阶段 5：AI 打标语义增强

目标：让上传图片生成的 `image_summary` 更能支撑自然语言搜索。

改造点：

- 更新 `skills/analyze-image-content/RULES.md`。
- 要求 summary 明确画面主体、界面功能、业务卖点、排除边界。
- `recommended_search_words` 同时包含短词、功能词和真实家长痛点句。
- `negative_tags` 记录容易误召回的相近概念。
- `secondary_labels.reason` 要说明为什么是这个标签，为什么不是相近标签。

验收：

- 新上传图片的 summary 能被业务长句匹配。
- AI 建议标签 reason 可供设计师审核。
- 重新分析不覆盖人工确认标签。

### 阶段 6：扩展评测集与全量推广

目标：从 3 个意图簇扩展到 6 大体系。

节奏：

- 第一批：15 条评测 query。
- 第二批：30 条评测 query。
- 第三批：50 条评测 query。

每条评测记录包含：

- query
- 真实意图
- 期望体系
- 期望二级标签
- 强相关图片
- 不应该出现的图片
- 评分标准
- 截图或结果记录

验收：

- 每次搜索逻辑变更后都能对比评测结果。
- 不再依赖“感觉好像准了”。

---

## 8. 阶段验收总表

| 阶段 | 核心目标 | 主要交付物 | 必须验证 |
|---|---|---|---|
| 阶段 0 | 冻结现状 | 状态记录、任务边界 | 明确不做事项 |
| 阶段 1 | 服务边界收口 | 更薄的 `ImageService`，独立 lifecycle/tagging 职责 | 上传、详情、删除、恢复、打标不变 |
| 阶段 2 | 搜索边界预拆 | Query expansion / ranking 逻辑有独立入口 | 搜索行为基本不变 |
| 阶段 3 | 最小业务意图层 | `business_intents.json`、`QueryUnderstandingService` | 三个意图簇能归一 |
| 阶段 4 | 强意图搜索收紧 | strict result policy、匹配原因 | 不再用 C 级兜底污染主结果 |
| 阶段 5 | AI 语义增强 | 更业务化的 summary、search words、negative tags | 新图能被长话术搜到 |
| 阶段 6 | 评测集扩展 | 15/30/50 条评测 query | 每次搜索改动可对比 |

每个阶段完成后，都要按 `docs/OPTIMIZATION_PLAN.md` 的格式写一条变更记录。

---

## 9. 本轮明确不做

为了控制项目重量，本轮不做这些事：

- 不新增大量二级标签。
- 不把业务原文档所有长句塞进 `taxonomy/catalog.json`。
- 不把 `SearchService` 改成所有规则的大杂烩。
- 不直接重写前端图片库页面。
- 不让 AI 输出绕过 normalizer、schema 和 taxonomy 校验。
- 不让 Meilisearch 变成事实源。
- 不一次性重跑所有旧图 AI 分析，等 prompt 和意图层稳定后再做。

---

## 10. 推荐第一张任务清单

如果现在开始动代码，建议第一张任务单这样写：

```text
目标：为搜索意图识别做结构准备，不改变现有用户主流程。

范围：
1. 拆薄 ImageService 的删除/恢复/永久删除职责。
2. 拆出 ImageTaggingService，集中人工标签与 AI 建议标签状态流转。
3. 梳理 SearchService 中的 query expansion 和 ranking 逻辑，准备后续独立服务。
4. 新增或补强架构测试，防止职责回流。

不做：
- 不新增业务意图词库。
- 不调整搜索排序。
- 不修改前端搜索体验。
- 不批量重跑 AI 分析。

验收：
- 后端测试通过。
- 前端 typecheck 通过。
- 上传、详情、打标、删除、恢复、搜索主流程不变。
```

---

## 11. 改造完成后再开始意图识别

服务边界收口完成后，第二张任务单再做：

```text
目标：接入最小业务意图层，先验证 3 个核心意图簇。

范围：
1. 新增 business_intents.json。
2. 新增 BusinessIntentCatalog / QueryUnderstandingService。
3. 只放 AI错题本、AI拍题精学、专家规划。
4. SearchService 调用 QueryUnderstandingService，但不内置业务规则。
5. 用 15 条搜索评测 query 验证。

验收：
- 三个意图簇能从精准词、功能描述、家长痛点归一到正确标签。
- 强意图下允许少结果，不强行补满。
- C 级兜底不污染主结果。
```

---

## 12. 总结

现在最稳的路线是：

```text
先减重
  拆服务边界，避免 ImageService / SearchService 继续膨胀

再接意图
  business_intents 独立承接业务原文档和家长痛点

再调搜索
  强意图下收紧结果，减少兜底污染

最后扩展
  扩到更多体系、更多评测 query、更多旧图重分析
```

这条路线的好处是：业务理解能力会增强，但项目结构不会被越堆越厚。
