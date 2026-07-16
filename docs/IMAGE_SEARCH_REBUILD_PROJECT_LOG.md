# 图片搜索改造项目日志

更新时间：2026-07-16
当前范围：Phase 0～Phase 6
当前状态：Phase 0～6 工程改造完成；旧图片数据已清零，等待新素材重新建立 Phase 0/4 真实业务基线

> 本文档记录项目实际做过的工作、迁移、验证结果和遗留事项。架构原则、业务决策与后续阶段路线仍以 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为唯一事实来源。后续日志按日期追加，不覆盖历史记录。

---

## 2026-07-15：完成 Phase 0～Phase 3 工程改造

### 一、本轮目标

- 将原有“单张图片 + 固定标签”结构逐步改造成“业务概念 + 素材组 + 多对多关系”。
- 保证六大体系稳定，但下层业务内容可以修改、合并、拆分和跨体系复用。
- 主图可以先发布，延展尺寸、备选版本和修订版本可以后续追加。
- 将 AI 识别出的客观画面内容与业务负责人确认的业务关系彻底分离。
- 控制模块体积和单点压力，继续保持 Model、Repository、Service、API 分层。
- 本轮不提前实现 Phase 4 在线搜索编排和 Phase 5 完整端侧改版。

### 二、Phase 0：搜索评测基线

完成内容：

- 扩展搜索评测用例结构，支持：
  - 强相关素材组；
  - 可接受素材组；
  - 禁止出现素材组；
  - 期望业务概念；
  - 查询歧义说明；
  - 是否允许少结果；
  - 数据集完整状态。
- 搜索评测脚本增加执行耗时、Top 素材组、缺失素材、禁止素材和 P95 统计。
- 建立首批 15 条查询的基线数据集。
- 将 `SE004` 绑定到当前唯一有效的真实素材组。
- 生成基线报告：`docs/PHASE0_BASELINE_REPORT_2026-07-15.json`。

当前结果：

- 数据集状态：`partial`。
- 查询数量：15 条。
- 真实素材绑定：1 条。
- `SE004`：Top 1 命中。
- 本地精准搜索 P95：`37.26ms`。
- 当前总体命中率不能作为搜索质量结论，因为正式搜索库只有 1 张可搜索代表图。

主要文件：

- `backend/app/domain/search_eval.py`
- `backend/scripts/run_search_eval.py`
- `taxonomy/search_eval_cases.json`
- `docs/PHASE0_BASELINE_REPORT_2026-07-15.json`

### 三、Phase 1：业务概念层

完成内容：

- 新增可版本化业务概念模型。
- 支持一个概念关联多个业务体系。
- 支持概念之间的相似、替代、合并等关系。
- 将通用搜索表达挂在业务概念层，避免每张图片重复保存相同搜索语言。
- 新增业务概念 Repository、Service、Schema、Serializer 和管理 API。
- 新增幂等概念种子脚本，从现有 taxonomy 和业务意图配置初始化概念数据。
- 种子脚本连续执行两次验证通过，第二次新增和更新均为 0。

当前数据：

- 业务概念：16 个。
- 概念与体系关系：21 条。
- 概念搜索表达：433 条。
- 概念关系：14 条。

主要文件：

- `backend/app/models/business_concept.py`
- `backend/app/repositories/business_concept_repository.py`
- `backend/app/services/business_concept_service.py`
- `backend/app/services/business_concept_serializers.py`
- `backend/app/schemas/business_concept.py`
- `backend/app/api/v1/business_concepts.py`
- `backend/scripts/seed_business_concepts.py`

### 四、Phase 2：素材组、主图和延展图

完成内容：

- 新增素材组模型，将同一套画面的主图、延展图、备选图和修订版归入同一组。
- 首次上传自动建立素材组，不再强制首次上传必须填写业务标签。
- 支持后续追加：
  - 延展尺寸 `derivative`；
  - 备选版本 `alternative`；
  - 修订版本 `revision`。
- 图片新增素材角色、尺寸、宽高比、渠道、版本号和当前版本等字段。
- 上传暂存阶段记录图片宽度和高度。
- 搜索响应按 `asset_group_id` 去重，同一套图只占一个搜索位置，并优先展示主图。
- 保留原图片响应结构，降低旧页面和旧接口的迁移压力。
- 新增素材 Repository、Service、Schema、Serializer 和 API。

当前数据：

- 素材组：2 个。
- 旧图片已完成一图一组回填。

主要文件：

- `backend/app/models/asset.py`
- `backend/app/repositories/asset_repository.py`
- `backend/app/services/asset_service.py`
- `backend/app/services/asset_serializers.py`
- `backend/app/schemas/asset.py`
- `backend/app/api/v1/assets.py`
- `backend/app/services/search_response_builder.py`
- `backend/app/services/storage_service.py`

### 五、Phase 3：图片理解和负责人确认

完成内容：

- 将图片语义升级为 Semantic Profile V2。
- AI 客观识别结果拆分为：
  - 画面事实；
  - OCR 文字；
  - 主体；
  - 场景；
  - 动作；
  - 视觉风格；
  - 画面中可见的产品功能；
  - 素材独有搜索表达；
  - 负向画面概念。
- 取消为了凑数量强制生成 18～22 个标签的规则，改为要求内容真实和维度覆盖。
- AI 只提出业务概念关系建议，默认状态为 `pending`。
- 业务负责人可以确认图片与业务概念的：
  - 主要表达 `expresses`；
  - 可以支持 `supports`；
  - 不适用/排除。
- 人工确认结果作为金标准，与 AI 建议分开保存。
- AI 重新分析时保留已接受、已拒绝和人工确认的关系，不允许覆盖人工结果。
- 图片独有搜索短语进入独立素材搜索短语表，不再混入通用内容标签。
- 保留旧 `ImageBusinessLabel` 兼容读取，计划在 Phase 6 下线。
- 前端现有 AI 详情面板切换为 V2 客观字段展示，并重新生成 OpenAPI 类型。

当前数据：

- 素材概念关系：1 条。
- Semantic Profile 已完成 V1 → V2 数据回填。

主要文件：

- `backend/app/schemas/ai.py`
- `backend/app/ai/normalizer.py`
- `backend/app/services/image_analysis_service.py`
- `backend/app/services/image_semantic_profile_service.py`
- `backend/app/services/asset_relation_service.py`
- `skills/analyze-image-content/RULES.md`
- `client/src/pages/ImageDetail/ImageAiAnalysisPanel.tsx`
- `client/src/types/openapi.d.ts`

### 六、数据库迁移

本轮新增三段独立迁移：

1. `20260715_0009_business_concepts.py`
   - 新建业务概念、概念体系关系、概念关系和概念搜索表达表。
2. `20260715_0010_asset_groups.py`
   - 新建素材组并补充图片版本字段；旧图片回填为素材组。
3. `20260715_0011_asset_semantics_v2.py`
   - 新建素材概念关系和素材搜索短语表；旧关系及 Semantic Profile V1 数据迁移到新结构。

迁移结果：

- 实际本地数据库已升级到 `20260715_0011 (head)`。
- 在数据库副本上完成 `0005 → 0011` 升级验证。
- 完成 `0011 → 0010 → 0011` 降级和重新升级验证。
- Phase 3 降级时会先把 Semantic Profile V2 回写为旧版本可读取的兼容结构。
- `/tmp` 中的数据库只用于迁移验证，不作为长期备份。

### 七、模块分层与维护性处理

本轮按照以下边界拆分代码：

```text
API：鉴权、请求参数和响应输出
  ↓
Service：单一业务工作流
  ↓
Repository：数据库查询和写入
  ↓
Model：数据结构和关系
```

具体处理：

- 业务概念、素材组、素材关系使用三个独立模块承载。
- API 不直接写数据库。
- Repository 不处理 HTTP 和业务编排。
- `ImageAnalysisService` 不直接承担素材关系表的持久化细节，交由 `AssetRelationService` 处理。
- 搜索结果素材组去重放在响应构建层，不塞进图片上传服务。
- 新增架构测试，阻止 API、Service、Repository 重新混成大文件。
- Phase 4 的多路召回、总超时、缓存、降级和 Reranker 未提前塞入本轮模块。

### 八、验证结果

后端：

- Ruff：通过。
- Pyright：0 error。
- Pytest：`96 passed`。
- 数据库迁移升降级：通过。
- `git diff --check`：通过。

前端：

- TypeScript typecheck：通过。
- ESLint：通过。
- Vitest：通过。
- Vite production build：通过。

新增重点测试：

- Phase 0 评测结构和真实素材绑定。
- 业务概念多体系关系及幂等种子。
- 首次上传自动建素材组。
- 延展图后续追加。
- 搜索结果素材组级去重。
- Semantic Profile V1 → V2 兼容。
- AI 建议与人工确认隔离。
- AI 重跑不覆盖人工结果。
- P0～P3 模块架构边界。

测试文件：

- `backend/tests/test_phase_0_3_rebuild.py`
- `backend/tests/test_architecture.py`
- `backend/tests/test_ai_analysis_rules.py`
- `backend/tests/test_search_service.py`
- `backend/tests/test_security_and_images.py`

### 九、未完成事项

- Phase 0 仍缺少 2～5 张已审核代表主图。
- 需要业务负责人确认代表图的“主要表达/可以支持/不适用”关系。
- 需要将 10～20 条查询绑定到真实素材组后重新运行基线。
- 搜索 P95 `2.5s` 目标仍待用户最终确认。
- 当前概念初始类型统一为 `business_term`，后续可由负责人逐步细化。
- （当时状态）Phase 4 在线并行召回、总超时、缓存、降级和 Reranker 尚未开始；现已完成工程改造。
- （当时状态）Phase 5 设计师端和业务搜索端完整交互尚未开始；现已完成工程改造。
- Phase 6 双读迁移、旧标签职责下线和正式切换尚未开始。

### 十、下一步

1. 补充 2～5 张已审核代表主图。
2. 完成负责人业务概念关系确认。
3. 扩充真实查询绑定并重新运行 Phase 0 基线。
4. 更新改造总纲的跨窗口接力区。
5. 开始 Phase 4 搜索核心改造。

---

## 2026-07-15：完成 Phase 4 在线搜索编排改造

### 本轮目标

- 将串行搜索改造成并行、限时、可缓存、可监控和可降级的在线链路。
- 任一外部模型或索引不可用时，数据库概念/短语搜索仍能返回结果。
- 候选融合后只执行一次 Reranker，移除默认链路中的第二次生成式图片摘要裁判。
- 搜索以素材组为排序和展示单位。

### 完成内容

- 新增 `AsyncSearchOrchestrator`，`SearchService` 缩为薄门面和依赖装配入口。
- 将外部分支启动、缓存和主会话水合拆到 `SearchExternalBranches`，将总截止内唯一一次重排拆到 `SearchRerankCoordinator`；总编排器由 455 行收口到 256 行。
- 搜索 API 改为异步 `await search_async(...)`，同步脚本保留兼容入口。
- Meilisearch、Embedding、复杂查询理解在独立线程分支同时启动。
- 外部分支只返回候选 ID/向量，ORM 图片在请求主会话统一装载，避免线程共享 Session。
- 新增版本化概念名称、概念搜索表达和负责人确认素材关系召回。
- 新增多路候选融合和一致性加分。
- 同一素材组在 Reranker 之前合并，最多对 Top 20 素材组调用一次 Reranker。
- Reranker、Embedding、Meilisearch 或生成式查询理解失败时自动降级。
- 查询理解和 Embedding 查询向量增加进程内 TTL/LRU 缓存。
- 增加总截止和分支预算：总计 `2.5s`、Meilisearch `0.2s`、Embedding `0.65s`、复杂查询理解 `0.9s`、Reranker `0.7s`。
- 每次搜索返回并持久化分支状态、耗时、候选数、缓存命中、降级来源和 Reranker 使用信息。
- Meilisearch 派生文档增加素材组和业务概念字段。
- 两到三个字的泛化词只允许完整查询精确匹配，避免“课程/教材”等词在长句中造成跨概念误召回。
- 搜索运营页增加 P95、超时、缓存命中和 Reranker 使用指标。

### 主要文件

- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_rerank_coordinator.py`
- `backend/app/services/search_branch_runner.py`
- `backend/app/services/search_diagnostics_service.py`
- `backend/app/services/search_cache.py`
- `backend/app/services/concept_search_recall.py`
- `backend/app/services/query_profile_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/search_ranking_service.py`
- `backend/app/services/meilisearch_recall_service.py`
- `backend/app/services/embedding_recall_service.py`
- `backend/app/repositories/image_repository.py`
- `backend/app/services/search_index.py`
- `backend/app/models/search_log.py`
- `backend/tests/test_phase4_search_orchestration.py`
- `client/src/pages/AdminSearchOps/components/SearchOpsSections.tsx`

### 数据迁移

- 新增 `20260715_0012_search_orchestration_metrics.py`。
- `search_logs` 增加素材组结果、总耗时、超时、缓存、Reranker、降级来源和各分支状态字段。
- 数据库副本完成 `0011 → 0012 → 0011 → 0012` 往返验证。
- 实际本地数据库已升级至 `20260715_0012 (head)`。

### 测试结果

- 后端 Ruff：通过。
- 后端 Pyright：0 error。
- 后端 Pytest：`106 passed`（含编排分层与文件体量护栏）。
- 前端 OpenAPI 类型：已重新生成。
- 前端 TypeScript、ESLint、Vitest、production build：全部通过。
- Meilisearch 文档重建：dry-run 通过；本机服务未运行，未正式提交索引重建。
- 当前本地精准评测：15 条查询，P95 `49.7ms`，无超时、无降级、无禁止素材。

### 遗留问题

- 当前只有 1 条查询绑定真实素材，无法完成跨概念误判率业务验收。
- 尚未在真实 Meilisearch、Embedding、查询理解模型和 Reranker 全部开启时执行端到端 P95 压测。
- Phase 4 工程完成，但真实数据验收继续标记为 `partial`。

### 下一步

1. 补充 2～5 张代表素材与负责人关系。
2. 将 10～20 条真实查询绑定到素材组。
3. 启动 Meilisearch 后执行正式全量索引重建。
4. 开启真实外部 Provider，完成并发、故障和 P95 压测。
5. 验收通过后再进入 Phase 5。

---

## 2026-07-15：完成 Phase 5 两个使用端改造

### 本轮目标

- 设计师可以先上传一张主图，再在素材详情中维护业务关系、延展尺寸和主图版本。
- 普通业务人员只面对一个搜索框，可选六大体系筛选，并按素材组选择合适尺寸下载。
- 保持页面、hooks、API、Service、Repository 分层，避免上传页或搜索入口成为新的大模块。

### 完成内容

设计师端：

- 上传弹窗改为只强制选择图片，标题由文件名兜底；渠道、主要表达概念和搜索话术均可选。
- 素材详情新增版本工作区，可追加延展图、备选图和修订版，也可替换正式主图。
- 素材详情新增业务概念关系审核，支持逐条或批量接受 AI 建议，并保持人工关系不被 AI 重跑覆盖。
- 素材详情新增素材级搜索话术审核，继续复用素材组继承关系。
- 追加延展图后同步派生索引；替换主图时旧主图退为历史版本并删除旧索引，新主图写入索引。

业务端：

- 删除普通用户可见的“精准/智能”切换，统一为一个业务搜索框。
- 增加六大体系快捷筛选；只有显式选择时才执行硬过滤，默认允许跨体系结果。
- 搜索结果卡改为素材组级展示，提供正式主图、当前延展尺寸、渠道和版本选择。
- 卡片展示可解释的匹配原因、主要表达概念和可以支持概念，不暴露内部搜索模式和等级分组。
- 增加单卡“不相关”反馈，反馈能追溯到具体图片和素材组，但不会修改审批与人工关系。
- 外部 Provider 未配置或超时时仍展示数据库可用结果和简洁降级提示。

分层处理：

- 前端请求集中到 `client/src/api/asset.ts`，查询和 mutation 集中到 `client/src/features/assets/` hooks。
- 版本维护、概念审核、话术审核和搜索结果卡保持独立组件；页面文件只做编排。
- 后端用 `SearchSystemFilter` 管显式体系过滤，用 `SearchAssetPresenter` 组装业务展示字段；搜索编排器只调用它们，不吸收具体展示逻辑。
- 素材组业务继续由 `AssetService` 和 `AssetRelationService` 分工，API 不直接写数据库。

### 主要修改文件

- `backend/app/api/v1/assets.py`
- `backend/app/services/asset_service.py`
- `backend/app/services/asset_relation_service.py`
- `backend/app/services/search_system_filter.py`
- `backend/app/services/search_asset_presenter.py`
- `backend/app/services/search_orchestrator.py`
- `backend/app/schemas/asset.py`
- `backend/app/schemas/image.py`
- `backend/app/models/search_feedback.py`
- `backend/tests/test_phase5_endpoints.py`
- `client/src/api/asset.ts`
- `client/src/features/assets/`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/pages/ImageHome/GlobalImageSearch.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/`
- `client/src/pages/ImageDetail/asset/`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`

### 数据迁移

- 新增 `20260715_0013_result_feedback_targets.py`。
- `search_feedback_events` 增加可空的 `result_image_id` 与 `asset_group_id` 外键和索引。
- 数据库副本完成 `0012 → 0013 → 0012 → 0013` 往返验证。
- 实际本地数据库已升级到 `20260715_0013 (head)`。

### 测试结果

- 后端 Ruff：`app/tests/scripts` 与本轮迁移通过。
- 后端 Pyright：0 error。
- 后端 Pytest：`109 passed`。
- 前端 TypeScript、ESLint：通过。
- 前端 Vitest：2 个测试文件、3 个测试通过。
- 前端 production build：通过。
- OpenAPI 类型：已从当前后端重新生成。
- `git diff --check`：通过。
- 隔离临时数据库页面走查：登录、单搜索框、六体系可选筛选、无外部 Provider 降级和简化上传弹窗正常；浏览器控制台无错误。

### 遗留问题

- Phase 0 仍缺 2～5 张已审核代表图、负责人关系确认和 10～20 条真实查询绑定。
- Phase 4 仍需在真实 Meilisearch、Embedding、查询理解和 Reranker 全部开启后完成 P95 压测。
- 当前真实数据不足，Phase 5 完成表示工作流和工程验收通过，不表示搜索质量业务验收已经通过。
- 后端兼容搜索模式参数和旧标签读取仍保留，统一放到 Phase 6 双读核查后下线。

### 下一步

1. 补齐代表素材、负责人确认关系和真实查询绑定。
2. 启动真实搜索增强服务并重建派生索引，完成端到端压测。
3. 开始 Phase 6 前更新总纲接力区，明确双读范围、迁移校验和回滚开关。
4. 对比新旧搜索结果、修复迁移遗漏，再逐步下线旧字段职责。

---

## 2026-07-15：清空旧图片数据，从空素材库重新录入

### 本轮决定

- 用户明确舍弃全部旧图片及其业务数据，不再迁移旧素材。
- 保留账号、六大体系标签、版本化业务概念和概念搜索表达，作为新素材录入基础。
- Phase 6 取消旧图片数据迁移和基于旧素材的新旧搜索双读；保留新链路验证、配置回滚和旧代码职责下线。

### 清理前数据

- 图片：2。
- 素材组：2。
- 素材概念关系：1。
- 图片标签关系：2。
- 图片分类：2。
- AI 内容标签：29。
- 旧二级分类结果：4。
- 旧图片业务标签：1。
- 本地原图：2 个，缩略图：2 个。

### 已清理内容

- `images`、`asset_groups`。
- 素材概念关系和素材搜索话术。
- 图片标签、分类、内容标签、旧二级分类和旧业务标签。
- 图片分析记录和 Embedding。
- 搜索日志及搜索反馈，避免旧数据影响新素材运营指标。
- `storage/images` 中的原图、缩略图、暂存文件和回收站文件；目录结构及 `.gitkeep` 保留。

### 保留内容

- 用户账号：3。
- 标签体系节点：22。
- 业务概念：16。
- 概念搜索表达：433。
- 概念体系关系和概念间关系。
- 数据库结构、迁移版本和 Phase 0～5 工程代码。

### 验证结果

- 图片及所有图片关联业务表：均为 0。
- 素材组及素材关系表：均为 0。
- 搜索日志和反馈：均为 0。
- 本地图片文件：0。
- SQLite `foreign_key_check`：无异常。
- 数据库迁移版本仍为 `20260715_0013 (head)`。
- 当前 `SEARCH_BACKEND=database`，Meilisearch 未配置，因此不存在需要清理的外部派生索引。

### 后续录入方式

1. 从 1 张已审核主图开始上传，不要求一次补齐全部素材。
2. 在素材详情确认“主要表达/可以支持/不适用”关系。
3. 延展尺寸和替换主图后续按需追加。
4. 累积 3～6 张代表素材后重新建立 Phase 0 基线；累积 10～20 条真实查询后再评价搜索质量。

---

## 2026-07-15：Phase 6 空库旧代码职责下线

### 本轮目标

- 在用户明确舍弃全部旧图片、从空库重新录入的前提下，删除旧图片标签与分类职责。
- 保持模块分层：体系地图、业务概念、素材关系、客观画面语义、搜索编排分别归属独立模块。
- 删除端侧兼容入口和旧搜索模式，保证后续维护不需要同时理解两套业务模型。

### 完成内容

- 删除 `ImageTag`、`ImageCategory`、`ImageLevel2Category`、`ImageBusinessLabel` Model 及对应 Repository、Service、API 写入/读取逻辑。
- 删除旧标签管理、图片标签编辑、旧业务标签审核、旧分类筛选、标签树浏览和 `/tag/:tagId` 页面。
- `tags` 运行数据由 22 个旧树节点收口为 6 个稳定体系节点；16 个业务概念、21 条体系关系、433 条概念表达继续独立存在。
- 图片 AI 分析契约删除 `image_type`、旧 `secondary_labels` 和重复负向字段，统一为 Semantic Profile V2、客观内容标签和 `concept_suggestions`。
- 搜索理解契约删除一级标签/二级分类命名，统一为 `expanded_terms`、`matched_business_concepts`、`excluded_concepts`。
- 删除 `precise/smart/configured` 请求模式、`search_logs.requested_mode` 和相关运营统计；保留的 `search_mode` 只描述实际搜索来源。
- 删除不再使用的生成式图片摘要裁判 Service、模型任务和项目 Skill；在线候选仍最多执行一次 Reranker。
- 搜索运营页切换为 AI 概念关系审核池、业务概念健康度和命中概念统计。
- OpenAPI 前端类型从当前后端重新生成。

### 主要修改文件

- 数据与模型：`backend/app/models/image.py`、`tag.py`、`search_log.py`、`models/__init__.py`。
- 数据访问：`image_repository.py`、`tag_repository.py`、`search_ops_repository.py`。
- 工作流：`image_service.py`、`image_analysis_service.py`、`image_semantic_profile_service.py`、`asset_relation_service.py`、`search_*` 系列服务。
- API 与契约：`api/v1/images.py`、`api/v1/tags.py`、`schemas/image.py`、`schemas/ai.py`、`schemas/search_ops.py`。
- 前端：首页、图片详情、搜索结果、搜索运营页、`features/images` hooks、`api/image.ts` 和类型文件。
- 删除文件：旧标签工作流、旧强标签过滤器、旧图片摘要裁判，以及前端标签面板、筛选弹窗、标签树与标签浏览页。

### 数据迁移

- 新增 `20260715_0014_remove_legacy_image_semantics.py`。
- 删除 `image_tags`、`image_categories`、`image_level2_categories`、`image_business_labels`。
- 删除 `search_logs.requested_mode`，将 `matched_category` 重命名为 `matched_concept`。
- 删除 `tags` 中非体系节点；业务概念数据不删除。
- 在数据库副本完成 `0013 → 0014 → 0013 → 0014`，旧空结构可降级恢复，再升级结果一致。
- 正式本地数据库已升级到 `0014`；迁移前备份：`data/piancton.db.before-phase6-cleanup-20260715`。
- 升级后数据：账号 3、图片 0、体系节点 6、业务概念 16、概念表达 433；SQLite 外键检查无异常。

### 测试结果

- 后端 Ruff：通过。
- 后端 Pyright：0 error、0 warning。
- 后端 Pytest：`82 passed`。
- 前端 TypeScript：通过。
- 前端 ESLint：通过。
- 前端 Vitest：1 个测试文件、`2 passed`。
- 前端 production build：通过。
- 空库首图上传、预览、下载、回收站、统一搜索日志、AI 内容分析及概念建议均有接口回归测试。
- `git diff --check`：通过。

### 遗留问题

- 当前正式素材仍为 0；Phase 0/4 的真实搜索质量验收仍是 `partial`，不能用纯工程测试宣称搜索质量完成。
- Meilisearch、Embedding、查询理解 Provider 和 Reranker 全开启后的真实 P95 仍待新代表素材建立后压测。
- 数据库降级只恢复空旧兼容结构，不恢复已舍弃的旧图片或旧标签树数据。

### 下一步

1. 从 1 张已审核主图开始重新录入，在素材详情确认主要表达/可以支持/不适用关系。
2. 累积 3～6 张代表图后重建 Phase 0 基线。
3. 累积 10～20 条真实查询并启用实际外部 Provider 后，完成 Phase 4 全链路质量与时延验收。

---

## 2026-07-15：建立 Phase 0～6 回滚点并治理文档漂移

### 本轮目标

- 在继续录入真实素材前，把当前 Phase 0～6 工程成果保存为独立、可推送、可回滚的 Git 版本。
- 使用全新 PostgreSQL 环境验证迁移和全量检查，不只依赖本地 SQLite。
- 统一当前执行文档口径，明确历史文档边界，并用自动化测试阻止旧口径回流。

### 回滚点与 PostgreSQL CI

- 创建分支：`codex/image-search-phase6-checkpoint`。
- 创建回滚提交：`7529cee Checkpoint image search rebuild phases 0-6`。
- 推送到 GitHub 后触发 CI run `29425274877`。
- 后端任务使用 PostgreSQL 17，从空数据库执行 Alembic `upgrade head` 到 `20260715_0014`，随后 Ruff、Pyright 和 Pytest 全部通过。
- 前端任务执行 `npm ci`、ESLint、TypeScript、Vitest 和 production build，全部通过。

### 文档治理

- 重写根 README 的当前能力、阶段状态、真实素材入口、统一搜索和服务器验收口径。
- 更新 `backend/README.md`、`ARCHITECTURE.md`、`SEARCH_MODES_AND_AI.md`、`SERVER_DEPLOYMENT_CHECKLIST.md` 和 Meilisearch ADR，使其与 Phase 6 代码一致。
- 为旧前端施工文档、旧优化总表、旧改造总控、旧业务意图地图和旧标签改造方案增加“历史文档说明”。
- `IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 增加发布回滚点、文档治理记录、D026 文档状态决策和 D027 静态概念种子/AI Prompt 偏差记录。
- `DEVELOPMENT_GUARDRAILS.md` 增加当前执行文档、历史文档和自动检查规则。

### 自动防漂移

- 新增 `backend/tests/test_documentation_consistency.py`：
  - 阻止首次上传标签必选、18～22 个标签硬指标、普通用户搜索模式切换等旧契约回到当前执行文档；
  - 要求当前执行文档引用改造总纲；
  - 要求历史施工资料保留明确状态标记；
  - 要求总纲和项目日志发布同一个当前 Phase。
- `make check` 增加前端 ESLint，使本地统一检查与 GitHub CI 口径一致。

### 数据迁移

- 本轮没有新增或修改数据库迁移。
- 本地数据库仍为 `20260715_0014`，正式素材仍为 0。

### 测试结果

- 本地后端 Pytest：`86 passed`，其中新增文档一致性测试 `4 passed`。
- Ruff：通过。
- Pyright：0 error、0 warning。
- 前端 TypeScript、ESLint、Vitest（`2 passed`）和 production build：通过。
- `git diff --check`：通过。
- 首个 Phase 0～6 回滚提交的 GitHub PostgreSQL/前端 CI：通过。

### 遗留问题

- 真实素材、负责人关系和真实查询绑定仍为空，Phase 0/4 业务验收继续是 `partial`。
- D027 尚未落实：概念种子和 AI Prompt 仍以静态 taxonomy 为输入，开放概念长期维护前需要改为不覆盖数据库人工事实并读取当前启用概念。
- 目标服务器的 HTTPS、持久化、权限、备份和恢复演练仍未执行。

### 下一步

1. 后续文档或契约变化继续运行 `make check`，并保留回滚提交与文档治理提交的独立边界。
2. 从空库录入首批 3～6 张代表素材并完成负责人关系确认。
3. 绑定 10～20 条真实查询，重建 Phase 0/4 基线。

---

## 2026-07-15：真实录入前的概念与搜索话术交互收口

### 本轮目标

- 澄清首次上传的“主要表达概念”与六大体系不是固定一级/二级树关系。
- 避免把体系错误理解成普通查询必须先经过的路由层。
- 把素材搜索话术从多行文本框改为更适合业务录入的逐条添加交互。

### 完成内容

- 上传页文案改为“主要表达卖点（业务概念）”，并提示它不是六大体系；体系关系由概念配置复用。
- 首次上传继续只选择一个主要表达概念，提交后确认 `expresses` 关系；不会把图片锁定到唯一体系。
- 明确普通搜索同时使用概念、概念话术、素材独有话术、画面语义和可降级外部分支；只有用户显式选择六大体系筛选时才进行体系硬过滤。
- “业务人员可能怎么搜索”多行文本框改为编号输入项，可通过“添加一条”追加，最多 5 条，支持单条删除。
- 上传页明确通用业务话术维护在概念层，当前素材只补充独有画面、文案或使用场景表达。

### 修改文件

- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/pages/ImageHome/uploadSearchPhrases.test.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`
- `backend/tests/test_documentation_consistency.py`

### 数据迁移

- 无。接口仍接收字符串数组，数据库继续使用 `asset_search_phrases`，仅调整录入交互和说明。

### 测试结果

- 前端 TypeScript、ESLint：通过。
- 前端 Vitest：2 个测试文件、`3 passed`。
- 总纲文档一致性测试增加 D028 和逐条话术交互断言。

### 遗留问题

- 真实素材仍需按新的录入交互上传并观察业务人员是否能区分概念通用话术与素材独有话术。
- 概念体系关系的长期维护仍受 D027 约束，开放业务概念编辑前需要把静态种子和 AI Prompt 收口到数据库事实源。

### 下一步

1. 使用 3～6 张代表图片录入主要表达概念和少量素材独有话术。
2. 在素材详情补充“可以支持/不适用”关系，不在首次上传堆叠全部业务判断。
3. 使用真实模糊句和明确卖点词验证跨概念召回、概念直达和显式体系筛选差异。

---

## 2026-07-15：全项目 UX/UI 第一轮重设计

### 本轮目标

- 修正“最多 5 条”容易被理解为素材永久限制的问题。
- 以资深 UX/UI 视角统一全项目的信息架构、视觉层级、文字和主流程交互。
- 优先解决上传弹窗失衡、说明堆叠、首页双搜索入口、后台表单缺少层级和浏览器原生 `prompt` 等体验问题。

### 完成内容

- 新增 `UX_UI_DESIGN_SYSTEM.md`，定义角色主任务、单页单主任务、渐进披露、布局、上传、搜索、文案、响应式和防漂移规则。
- 更新全局视觉令牌：冷静蓝靛主色、低饱和背景、统一圆角、阴影、焦点和表单状态。
- 全局导航统一为“业务素材中心”，重排主导航和账号菜单，减少头部工具条噪音。
- 首页删除第二个本地搜索框，只保留统一业务搜索；六大体系继续作为可选筛选，素材浏览只保留排序和明确空状态。
- 上传窗口重构为双栏布局：左侧选图与预览，右侧可选信息，底部固定发布；首次话术采用编号逐条添加，明确“首次 5 条、发布后可持续补充”。
- 素材详情统一图片舞台、信息卡、版本、卖点关系和话术维护层级；话术面板支持回车添加并显示已确认数量。
- 用户管理改为带标签的创建表单、中文角色和可扫描列表；密码重置从浏览器 `prompt` 改为专用弹窗。
- 登录、回收站、审计日志、搜索运营和 404 页面统一页面标题、卡片和空状态。

### 修改文件

- 设计系统与公共组件：`tailwind-theme.css`、`button.tsx`、`input.tsx`、`dialog.tsx`、`select.tsx`、`PageHeader.tsx`、`EmptyState.tsx`、`Layout.tsx`。
- 首页与上传：`ImageHome/*`、`UploadAssetPicker.tsx`、`UploadSearchPhraseFields.tsx`、`uploadSearchPhrases.ts`。
- 素材详情：`ImageDetail/*`、`ImageDetail/asset/*`。
- 后台与辅助页面：`AdminUsers`、`AdminAudit`、`AdminSearchOps`、`Trash`、`Login`、`NotFound`。
- 文档与防漂移：改造总纲、项目日志、开发护栏、UX/UI 设计规范和文档一致性测试。

### 数据迁移

- 无。首次上传仍最多发送 5 条初始素材话术；详情页继续通过已有 `asset_search_phrases` 接口持续添加，不存在 5 条数据库总限制。

### 测试结果

- 前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build：通过。
- 浏览器走查：首页、空素材状态、新上传窗口和用户管理页面正常；上传窗口可访问名称和首次/后续话术说明正确。
- 本地 `make check` 全部通过：后端 Pytest `86 passed`、Ruff、Pyright，以及前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 均通过。

### 遗留问题

- 当前素材库仍为空，详情页的真实长内容、不同尺寸版本和 AI 审核密度需要在首批 3～6 张代表素材录入后继续视觉调优。
- 永久删除仍使用现有确认方式，后续可统一为项目内危险操作弹窗，但不阻塞真实素材录入。
- D027 数据库概念事实源偏差仍待落实。

### 下一步

1. 用真实代表图片走一遍上传、分析、卖点确认、话术补充、搜索和下载闭环。
2. 收集业务用户的真实搜索句和失败反馈，确认“概念通用话术/素材独有话术”的文字是否足够易懂。
3. 根据真实图片比例与后台数据密度完成第二轮细节调优，不再凭空增加装饰。

---

## 2026-07-16：产品名称统一为“卖点智库”

### 本轮目标

- 将用户确认的正式产品名称写入界面与当前执行文档，防止品牌文案漂移。

### 完成内容

- 全局导航、登录页和浏览器标题统一显示“卖点智库”。
- 用户进一步指出首页仍保留旧标题“业务素材库”；首页主标题已按 D031 统一为“卖点智库”，英文眉题同步改为 `Selling Point Library`。
- README 与 UX/UI 设计规范同步正式名称；总纲新增 D030。
- `piancton` 保留为仓库、数据库、Cookie 和部署服务等内部技术标识，不做无业务收益的底层改名。

### 修改文件

- 前端：`branding.ts`、`Layout.tsx`、`Login.tsx`、`index.html`。
- 文档：README、改造总纲、项目日志、UX/UI 设计规范和文档一致性测试。

### 数据迁移

- 无。

### 测试结果

- 前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build：通过。
- 文档一致性测试：`4 passed`。
- 浏览器走查：全局导航显示“卖点智库 / 素材搜索与运营”，首页一级标题和浏览器标题均显示“卖点智库”；旧首页标题不再出现，本地 Web、后端和 PostgreSQL 容器均健康。

### 遗留问题

- 无命名遗留；“搜索运营”等后台功能名称可以保留，但首页不再使用“业务素材库”。

### 下一步

1. 使用真实代表素材继续验证上传、搜索和卖点关系维护闭环。

---

## 2026-07-16：首张真实素材搜索修正

### 本轮目标

- 修复“课程同步”素材已经人工确认“同步校内”，但查询“和学校课程一致”仍返回 0 张的问题。
- 保证外部搜索服务失败时，人工确认概念及常见表达仍能由本地链路召回。

### 完成内容

- 新增“学校课程一致/同步/对齐”等 5 条概念级表达，查询不再误判为“动画精讲”。
- 高置信本地概念查询跳过查询 Embedding 和模型查询理解；模糊查询继续并行使用外部分支。
- 实测当前 Provider 延迟后，把查询 Embedding/Reranker 预算调整为 `1.8s/1.4s`，总截止保持 `2.5s`；Docker Compose 显式传递全部搜索预算配置。
- 恢复 Meilisearch 容器，重建 1 张正式素材的派生索引，并完成健康、临时索引写入、真实查询和清理验证；本地 `.env` 启用 `COMPOSE_PROFILES=search`。
- 业务端降级文案改为“智能语义搜索响应较慢，已使用基础搜索”，技术分支名称和超时诊断继续只在管理员搜索运营页展示。

### 修改文件

- 搜索：`business_intents.json`、`search_external_branches.py`、`search_orchestrator.py`、`config.py`、`docker-compose.yml` 和环境示例。
- 前端：`SemanticSearchResult/index.tsx`。
- 测试：`test_business_intents.py`、`test_phase4_search_orchestration.py`、`test_documentation_consistency.py`。
- 文档：改造总纲、项目日志、开发护栏、搜索说明、UX/UI 规范和 README。

### 数据迁移

- 无结构迁移。后端启动时幂等同步 5 条新增概念表达，当前 `concept_search_phrases=454`；Meilisearch 正式派生索引已重建 1 张素材。

### 测试结果

- 失败优先回归：修改前两个专项测试均失败，错误归一为“动画精讲”；修改后通过。
- 专项回归：业务意图、Phase 4 编排和文档一致性共 `21 passed`。
- `make check`：后端 `87 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Provider 单次实测：Embedding `1.648s`、模型查询理解 `9.589s`、单候选 Reranker `1.269s`。
- 真实数据库完整链路：`134ms`、1 张、无降级；关闭全部外部分支：`76ms`、仍返回同一张。
- 浏览器走查：查询“和学校课程一致”显示 1 张“课程同步”，匹配原因包含“学校课程一致”和“同步校内”，无降级警告。

### 遗留问题

- 当前只有 1 张真实素材和 1 条已复验查询，Phase 0/4 搜索质量仍为 `partial`，不能据此宣称整体搜索质量验收完成。
- 当前模型查询理解约 `9.6s`，不适合作为 2.5 秒在线主链路依赖；模糊查询优先依靠本地概念、Meilisearch 和 Embedding，模型结果允许超时丢弃。

### 下一步

1. 继续录入 2～5 张代表素材，并为每张建立明确查询、口语改写和禁止素材。
2. 累计 10～20 条真实查询后重跑 Phase 0/4 基线，观察零结果率、Top 3 命中率和 P95。
3. 根据更多真实延迟样本决定是否更换更快的查询理解模型，不在样本不足时放宽 2.5 秒总截止。

---

## 2026-07-16：公共话术、素材话术与搜索反馈分层优化

### 本轮目标

- 让“卖点公共话术”和“当前素材独有话术”拥有清晰、可进入、可维护的独立入口。
- 明确公共话术、素材话术、客观标签在真实搜索中的作用与优先级。
- 补齐“就是这张”正向标记，为后续真实话术归档建立数据入口。

### 完成内容

- 新增管理员“卖点管理”二级页，按卖点集中查看、添加、修改、停用和恢复公共话术，并展示话术来源与类型。
- 公共话术按标准化文本去重展示，短词单独归入默认折叠的“辅助关键词”；同文本的多来源记录停用或恢复时同步，避免页面重复和状态漂移。
- 公共话术更新使用概念版本号；初始词库话术允许停用但不能直接改名，避免种子再次添加原词造成重复。
- 上传时选择主要表达卖点后自动显示继承公共话术的数量与前 5 条示例；公共话术为空时管理员可以就地添加。
- 上传和素材详情统一使用“当前素材独有话术”，并在素材详情单独展示从关联卖点继承的公共话术及管理入口。
- 素材详情进一步区分已确认话术与 AI 待确认候选；两类内容进入固定最大高度、支持鼠标和键盘纵向滚动的列表，添加入口保持在列表外，避免候选过多拉长整页。
- “手动补充确认关系”调整为默认关闭的按需开关；开启后才显示业务概念、关系类型和确认按钮，已确认关系与 AI 建议不受影响。
- 搜索结果卡新增“就是这张/不相关”双向反馈；正向反馈进入搜索运营数据，但不生成搜索问题，也不自动修改人工业务事实。
- Meilisearch 搜索字段顺序改为已确认卖点公共语言优先于素材独有语言、素材独有语言优先于客观内容标签；数据库权重用自动化测试固定为 `0.95/0.90/0.80`。
- FastAPI OpenAPI TypeScript 类型已重新生成；本地 Docker 后端、Web、PostgreSQL 和 Meilisearch 已重建运行。

### 修改文件

- 后端：业务概念 schema/service/API、搜索反馈 schema、搜索运营归因、Meilisearch 字段设置。
- 前端：卖点管理页、公共话术 API/hooks、上传继承面板、素材详情话术面板、导航与搜索结果正向反馈。
- 测试：Phase 1 概念话术生命周期、Phase 5 正向反馈、数据库/Meilisearch 搜索优先级、文档一致性。
- 文档：README、改造总纲、项目日志、架构、搜索说明和 UX/UI 规范。

### 数据迁移

- 无数据库结构迁移。公共话术继续使用 `concept_search_phrases` 与业务概念版本字段；正向反馈继续使用现有 `search_feedback_events.feedback_type` 字符串字段。

### 测试结果

- 失败优先回归：新增公共话术 PATCH 测试在接口实现前稳定返回 `404`，实现后通过。
- 专项回归：概念话术、正向反馈、搜索索引和搜索服务共 `15 passed`。
- `make check`：后端 `89 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build全部通过。
- Docker production build：后端和前端镜像构建通过，PostgreSQL、Meilisearch、后端和 Web 容器健康。
- 浏览器验收：上传“同步校内”显示 `20` 条去重公共话术和 `11` 个辅助关键词；素材详情正确拆分继承话术与单图独有话术；搜索“和学校课程一致”命中“课程同步”且显示“就是这张/不相关”。验收过程中未提交反馈，未污染真实运营数据。

### 遗留问题

- 当前只有 1 张真实素材，新的字段优先级已有工程测试，但多图片之间的 Reranker 顺序仍需再补充 2～5 张代表图后验收。
- 搜索运营页已能看到正向反馈，自动聚类相似查询并生成“待归档公共话术”的审批队列仍属于后续优化，不在本轮自动改写词库。
- D027 数据库概念事实源偏差仍待落实；本轮只开放公共话术维护，没有开放业务概念长期新增、改名或合并。

### 下一步

1. 上传教材版本图，与现有章节对应图共同验证“同步校内”公共话术继承和素材独有话术区分。
2. 使用“内容跟课本进度一致”“支持人教版教材”等真实查询确认两张素材的召回和排序。
3. 累积正向/负向反馈后设计待归档话术队列，不把每次搜索自动写入正式词库。

---

## 2026-07-16：延展版本删除与回收闭环

### 本轮目标

- 允许设计师在素材详情删除误传或不再使用的延展尺寸，同时保护正式主图和素材组业务关系。
- 沿用现有回收站生命周期，让误操作可恢复并避免前后端状态、素材组展示和搜索索引漂移。

### 完成内容

- 新增素材组范围的非主图版本删除接口；后端校验图片必须属于当前素材组，并拒绝直接删除正式主图。
- 删除只设置图片 `deleted_at` 并移入回收站，不影响素材组、主图、业务概念关系、公共/素材话术或其他尺寸。
- 素材组序列化统一排除已删除版本，搜索索引同时移除对应图片；回收站仍可按既有流程恢复。
- 素材详情为每个非主图版本增加常驻删除按钮；正式主图不显示删除按钮，并保留“替换主图”作为唯一身份变更入口。
- 删除前弹窗明确说明影响范围、可恢复性和主图保护，成功后即时刷新版本列表。

### 修改文件

- 后端：素材组 API、素材服务、素材组序列化和 Phase 5 端点回归测试。
- 前端：素材 API、素材操作 hooks、版本面板、独立删除确认弹窗和 OpenAPI TypeScript 类型。
- 文档：README、改造总纲、项目日志、架构和 UX/UI 规范；文档一致性测试同步锁定 D036 与关键交互。

### 数据迁移

- 无数据库结构迁移。继续复用图片现有 `deleted_at`、回收站恢复和永久删除生命周期。

### 测试结果

- 失败优先回归：新增非主图删除测试在接口实现前稳定返回 `404`，实现后通过。
- 后端专项检查：Ruff、Pyright 通过；Phase 5 与图片安全生命周期测试共 `14 passed`。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重新构建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实详情页只为非主图版本显示 1 个删除按钮，正式主图无删除入口；确认弹窗正确说明影响范围与可恢复性。验收点击“取消”，真实延展版本仍保留，页面无控制台错误。

### 遗留问题

- 当前真实素材只有一个非主图版本；浏览器验收只打开并取消确认弹窗，不实际删除用户真实数据，删除与恢复由隔离测试数据库覆盖。

### 下一步

1. 继续按需上传正确的延展尺寸；误传版本可在版本卡移入回收站。
2. 后续若需要永久清理，统一从回收站执行并继续保留二次确认。

---

## 2026-07-16：修复删除版本后仍显示为相关素材

### 本轮目标

- 修复延展版本移入回收站后，“版本与尺寸”已移除但“相关素材”仍显示旧卡片的问题。
- 收口信息架构：同一素材组的版本不是独立相关素材，只能在版本面板中出现。

### 完成内容

- 相关素材服务在评分前排除当前图片和同一素材组的全部版本，延展、备选和历史版本不再进入“相关素材”。
- 素材版本新增、替换和删除成功后，前端同时刷新图片详情缓存；相关素材与版本面板使用最新服务端状态。
- 回归测试加入同组延展版本候选，先稳定复现错误，再验证只返回其他素材组的相关图片。
- 文档新增 D037，明确“相关素材”和“版本与尺寸”的对象边界并加入一致性自动测试。

### 修改文件

- 后端：相关素材服务及搜索服务回归测试。
- 前端：素材操作缓存同步。
- 文档：README、改造总纲、项目日志、架构、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或接口迁移。

### 测试结果

- 失败优先回归：加入同组延展版本后，旧实现错误返回 2 张相关图片，测试失败；修正后只返回另一个素材组，专项 `2 passed`。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：刷新真实素材详情后，“相关素材”标题与已删除版本链接均为 0，“版本与尺寸”保留且只显示正式主图；页面无控制台错误。

### 遗留问题

- 当前正式库只有一个素材组；修复后该详情页没有真正的其他相关素材，因此“相关素材”区域应整体隐藏。

### 下一步

1. 补充第二个真实素材组后，再验证跨素材组的相关素材质量和排序。

---

## 2026-07-16：明确素材需求入口并统一结果卡下拉箭头

### 本轮目标

- 保留整次搜索的“结果不相关”反馈，同时让素材需求入口明确说明提交原因。
- 修正搜索结果卡尺寸/渠道下拉箭头过于靠边且与项目其他下拉不一致的问题。

### 完成内容

- “提交素材需求”改为“没有合适素材提交需求”；“结果不相关”“结果太少”“想要别的风格”保持不变。
- 结果卡尺寸/渠道选择从浏览器原生下拉改为项目标准 `Select` 组件，箭头固定距右边框 `16px`，输入文字同步预留右侧空间。
- 新增前端反馈文案回归测试，并用 D038 与文档一致性测试锁定文案和标准下拉组件。

### 修改文件

- 前端：搜索反馈常量、结果卡和文案回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或接口迁移。

### 测试结果

- 失败优先回归：旧文案未包含“没有合适素材提交需求”，新增测试先失败，修改后通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（3 个文件、`4 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实搜索结果同时显示“结果不相关”和“没有合适素材提交需求”；尺寸/渠道下拉箭头距右边框实测 `16px`，文字右侧预留 `44px`，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 继续从真实业务搜索中观察四个整次反馈选项的使用率，避免继续增加含义重叠的按钮。

---

## 2026-07-16：修复继承公共话术重复展示

### 本轮目标

- 修复同一个“同步校内”公共话术卡在素材详情重复出现两次的问题。
- 保留人工确认和 AI 建议的审计来源，不用删除业务记录掩盖展示层问题。

### 完成内容

- 只读核查真实 PostgreSQL：当前素材同时存在一条 `manual/accepted/expresses` 和一条 `ai/accepted/expresses`，二者指向同一个“同步校内”卖点。
- 新增 `selectInheritedConcepts`，先筛选已接受且非排除关系，再按卖点 ID 集合从概念列表选取，每个卖点只返回一次。
- 素材详情继承公共话术区域改用去重后的卖点列表；人工事实和 AI 审计记录均保持不变。
- 新增前端回归测试，并以 D039 和文档一致性测试锁定展示规则。

### 修改文件

- 前端：卖点话术展示工具、素材详情话术面板和回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或数据迁移；不删除现有人工或 AI 来源关系。

### 测试结果

- 失败优先回归：人工和 AI 两条已接受关系指向同一卖点时，旧实现没有去重函数，新增测试先失败；实现后专项测试通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情中的“同步校内 · 20 条公共话术”标题和对应管理入口均只出现 1 次，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续新增任何按关系渲染的摘要面板时，同样先明确是展示“来源记录”还是展示“唯一卖点”。

---

## 2026-07-16：继承公共话术严格跟随人工已确认关系

### 本轮目标

- 让“从卖点继承的公共话术”与上方“已确认关系”保持完全一致。
- 当前只有“同步校内”一个人工已确认卖点时，只展示这一张公共话术卡；AI 审计记录不能额外生成继承卡。

### 完成内容

- 将继承条件收紧为 `origin=manual`、`reviewStatus=accepted` 且关系不是 `excludes`，与已确认关系面板采用同一业务事实口径。
- 继续按卖点 ID 去重，保留人工和 AI 来源记录用于审计，不删除或改写现有数据。
- 新增 AI-only 已接受卖点的回归场景，固定它不能在缺少人工确认关系时触发继承。
- 新增 D040、UX/UI 防漂移规则和文档一致性断言；后续新增人工确认卖点后才自动增加对应继承卡。

### 修改文件

- 前端：卖点话术展示工具及回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构、接口或数据迁移；AI 审计记录继续保留。

### 测试结果

- 失败优先回归：加入一条只有 AI accepted 关系的卖点后，旧规则错误返回 `sync-school` 和 `ai-only`；增加人工来源约束后专项测试、TypeScript 和 ESLint 通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情中“同步校内 · 主要表达”已确认关系、对应公共话术卡和管理入口均各出现 1 次，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续补充并人工确认新的业务卖点关系时，核对详情页只新增该卖点的一张公共话术卡。

---

## 2026-07-16：延展版本改为纯上传并保护主图话术

### 本轮目标

- 尺寸/渠道延展只作为同一主视觉的附加尺寸上传，不再执行完整 AI 分析。
- 阻止非主图分析替换素材组已有 AI 关系或话术，避免延展图污染主图语义。

### 完成内容

- 延展上传接口无论客户端是否传入 `autoAnalyze=true` 都不创建分析任务；前端也明确发送关闭分析。
- AI 分析接口拒绝对 `derivative` 手动发起完整分析，并返回明确业务错误。
- 素材组级 AI 建议与候选话术只允许正式主图分析刷新；备选等非主图的客观分析只保存在图片自身。
- 延展弹窗明确说明“只上传并识别尺寸、不运行 AI 分析、继承主图关系和话术”，成功提示删除“正在后台分析”。
- 新增 D041，并同步 README、架构、AI 说明、UX/UI 规范和文档一致性防漂移测试。

### 修改文件

- 后端：素材版本接口、AI 分析接口、图片分析持久化边界和 Phase 5 回归测试。
- 前端：素材 API、版本弹窗与成功反馈。
- 文档：改造总纲、项目日志、README、架构、AI 说明、UX/UI 规范及文档一致性测试。

### 数据迁移

- 无数据库结构迁移。
- 真实素材中由已删除延展图遗留的 5 条错误 AI 待确认话术已通过现有审核状态改为拒绝；5 条人工已确认话术和业务关系保持不变。

### 测试结果

- 失败优先回归：旧实现会排队分析延展图，并把 `正确主图候选` 替换成 `错误延展候选`；两项测试修改前均失败，修正后 Phase 5 专项 `6 passed`。
- `make check`：后端 `92 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：延展弹窗明确显示“只上传文件并识别尺寸，不运行 AI 分析”；真实素材中的 5 条错误 AI 候选均已拒绝并从待确认区域消失，5 条人工话术保持可见，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续真实上传一个正确尺寸延展，确认只增加版本卡和尺寸，不新增分析状态或 AI 候选。

---

## 后续日志模板

后续每次改造在本文末尾追加以下内容：

```markdown
## YYYY-MM-DD：本轮标题

### 本轮目标

### 完成内容

### 修改文件

### 数据迁移

### 测试结果

### 遗留问题

### 下一步
```
