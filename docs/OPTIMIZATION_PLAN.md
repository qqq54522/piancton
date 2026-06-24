# 项目优化文档：架构收口、标签系统与 AI 搜索闭环

版本：2026-06-24  
适用阶段：本地版已跑通，准备进入稳定优化与后续线上部署规划阶段  
文档类型：改造指南 + 架构约束 + 变更记录  
核心目标：在不推倒重来的前提下，把现有项目从“功能可用”收口成“边界清晰、逻辑闭环、后续可扩展”的图片标签与智能检索系统。

这份文档不是一次性的想法记录，而是后续项目改造的施工准则。任何一轮优化都应该先看本文档，再动代码；每一轮完成后，也要把“改了什么、没改什么、验证了什么、遗留了什么”补回本文档或对应的变更记录中。

---

## 0. 使用方式与改造纪律

### 0.1 本文档解决什么问题

本文档用于约束后续优化，避免出现以下情况：

- 为了优化而大拆，导致原本可用的系统变乱。
- 新功能直接塞进已有大文件，导致边界越来越模糊。
- AI、搜索、标签、上传逻辑互相缠绕，后期无法维护。
- 文档和真实代码状态不一致，后续开发者误判系统。
- 每一轮改造完成后没有记录，导致不知道系统到底被改过什么。

### 0.2 每轮改造必须遵守的四条铁律

1. 不改变主流程体验  
   图片上传、自动分析、查看详情、搜索图片、标签展示这些主流程不能被破坏。

2. 不做无目标大重构  
   每轮只解决一类问题。比如“只更新文档与边界测试”“只拆 AI 分析服务”“只优化搜索评测”，不能多个方向混在一起乱改。

3. 不让 AI 输出直接污染业务数据  
   AI 结果必须经过 schema、taxonomy、来源状态校验，才能进入数据库或搜索索引。

4. 每轮必须有验收  
   至少要确认后端测试、前端类型检查、Docker 服务状态、关键业务流程是否正常。

### 0.3 每轮改造必须填写的记录

每次完成一轮或一个阶段性改造，都要补一条记录。格式如下：

```md
### YYYY-MM-DD：第 X 轮优化 - 标题

改造目标：
- 

实际改动：
- 

明确没有改动：
- 

验证结果：
- 后端测试：
- 前端检查：
- Docker 状态：
- 手工业务验证：

风险与遗留：
- 

下一步：
- 
```

### 0.4 改造时的禁止事项

除非单独确认，否则不要做这些事：

- 不要推倒重写后端服务层。
- 不要一次性重写前端页面。
- 不要删除已有业务字段。
- 不要把六大体系写死在多个 if else 中。
- 不要让 Meilisearch 替代数据库成为事实源。
- 不要让 AI 标签覆盖人工标签。
- 不要把密钥、模型配置、部署环境写死在代码里。
- 不要手工长期维护自动生成的 OpenAPI 类型文件。
- 不要在没有搜索评测集的情况下反复凭感觉调搜索规则。

### 0.5 改造完成的最低验收线

每一轮优化完成后，至少要满足：

- 后端测试通过。
- 前端 typecheck 通过。
- Docker 主要服务能启动。
- 上传图片主流程正常。
- 图片详情页正常。
- 搜索功能至少能正常返回结果。
- AI 分析失败时不影响图片基础可用性。
- 文档记录本轮改了什么。

---

## 1. 总体判断

当前项目不是一个“乱补丁项目”。它已经具备了比较完整的业务闭环：

- 图片上传、存储、缩略图、读取链路已经成立。
- 六大体系与二级标签已经进入系统，并通过 taxonomy catalog 管理。
- AI 图片分析、隐性标签、业务标签、分析记录已经形成闭环。
- 数据库搜索与 Meilisearch 智能搜索的双轨结构已经搭起来。
- Docker 本地部署已经跑通，具备后续线上迁移的基础。

但项目现在正处在一个容易变复杂的阶段。后续如果继续加入三级标签、更多业务表达、AI 搜索理解、OCR、向量检索、线上任务队列，就必须提前收口模块边界，否则容易变成“功能都能跑，但每次改动都牵一大片”。

当前更准确的状态是：

> 功能方向正确，核心闭环成立；但部分服务层开始膨胀，搜索逻辑与 AI 逻辑需要进一步模块化，文档和测试边界需要补强。

---

## 2. 当前架构目标

后续优化要围绕以下几个原则展开。

### 2.1 六大体系永远是主锚点

所有 AI 打标、业务搜索、隐性标签、推荐分类，都不能脱离六大体系。

六大体系与二级标签应该作为系统的“业务坐标系”：

- 设计师上传图片时，可以选择所属体系与二级标签。
- AI 可以补充建议标签，但不能随意发明主体系。
- 业务端搜索结果应该能解释“为什么这张图匹配这个搜索”。
- 后续新增二级、三级标签时，应该通过 catalog 配置扩展，而不是大面积改代码。

### 2.2 数据库是事实源，搜索引擎是派生索引

系统的主数据应该永远在数据库里，包括：

- 图片基础信息
- 人工选择的标签
- AI 建议标签
- 业务标签
- 审核状态
- 六大体系分类关系
- 分析记录

Meilisearch 不应该成为事实源，它只是为了提高搜索体验而生成的派生索引。

这意味着：

- 数据库数据是最终可信数据。
- Meilisearch 可以随时重建。
- 搜索索引丢失不影响主数据。
- 后续线上部署时，可以单独迁移搜索服务。

### 2.3 AI 是“建议与理解层”，不是不可控的决策层

AI 的角色应该是：

- 图片语义理解
- 隐性标签补充
- 搜索意图理解
- 业务表达扩展
- 辅助匹配六大体系

但 AI 不应该绕过系统规则直接写入不可解释的数据。

合理做法是：

- AI 输出必须经过 schema 校验。
- AI 标签必须关联到已存在的体系或标签。
- AI 建议与人工选择要能区分来源。
- 关键业务标签最好有 review 状态。
- AI 失败时，系统仍然可以上传和搜索基础图片。

### 2.4 本地与线上尽量保持同构

本地可以用 Docker Compose 跑：

- backend
- web
- postgres
- meilisearch

线上也尽量沿用同样的服务拆分思路。这样本地验证通过的逻辑，迁移线上时不会大幅变形。

---

## 3. 当前模块评估

### 3.1 后端分层

当前后端大致已经形成：

```text
API 层
  ↓
Service 层
  ↓
Repository / UnitOfWork
  ↓
Database

旁路能力：
StorageService
AiService / ModelProvider
SearchService / MeilisearchClient
TaxonomyCatalog
```

这个方向是正确的。

目前比较健康的部分：

- API、Service、Repository 基本有分层意识。
- UnitOfWork 已经承担事务边界。
- StorageService 独立处理图片文件和安全校验。
- AiService 与 ModelProvider 没有直接散落在 API 各处。
- taxonomy catalog 已经成为业务标签体系的核心约束。
- SearchService 已经开始承担搜索编排。

主要问题：

- ImageService 责任过多，开始变成“大服务”。
- 上传接口里有部分 AI 自动分析调度逻辑，API 层略厚。
- Repository 中包含部分搜索扩展逻辑，数据读取层与搜索业务层边界不够干净。
- AI 后台任务目前依赖 FastAPI BackgroundTasks，适合本地与 MVP，不适合更稳定的线上任务体系。

### 3.2 前端分层

当前前端已经有：

- pages
- features
- api
- types
- components

方向是对的。

主要问题：

- ImageDetail 页面过大，里面混合了数据加载、AI 状态、业务标签展示、操作按钮、权限判断。
- ImageHome 页面与 useImageBrowser hook 承担了搜索、筛选、上传、标签面板、分页等过多职责。
- 搜索模式、AI 分析状态、业务标签确认等未来会继续增长，如果不拆，页面会越来越重。

建议后续逐步拆成：

- ImageDetailHeader
- ImagePreviewPanel
- ImageAnalysisPanel
- BusinessLabelPanel
- ContentTagsPanel
- ImageActionsPanel
- useImageListQuery
- useImageSearch
- useImageFilters
- useUploadDialog

---

## 4. 当前已经成立的业务闭环

### 4.1 图片上传闭环

当前链路：

```text
设计师上传图片
  ↓
后端校验图片格式 / 大小 / 像素
  ↓
文件进入 storage
  ↓
数据库写入 image 记录
  ↓
可生成缩略图
  ↓
前端可查看图片
```

这个闭环已经成立。

需要继续优化的点：

- 上传后的 AI 分析应该由独立的分析服务编排。
- 文件最终落库与数据库提交之间要继续保持异常回滚。
- 线上阶段需要考虑对象存储或持久化卷。

### 4.2 AI 图片分析闭环

当前链路：

```text
图片上传完成
  ↓
触发 AI 分析任务
  ↓
调用大模型理解图片
  ↓
生成 summary / content tags / business labels
  ↓
经过结构校验与 taxonomy 校验
  ↓
写入数据库
  ↓
前端展示 AI 分析结果
```

这个闭环已经基本成立。

需要继续优化的点：

- 后台任务应从 BackgroundTasks 升级为可靠任务队列。
- analysis_runs 应记录更完整的状态，如 error_code、error_message、retry_count、completed_at。
- AI 分析结果应该区分“自动建议”“人工确认”“人工驳回”。

### 4.3 搜索闭环

当前搜索已经有两条路径：

```text
精准搜索：数据库规则搜索
智能搜索：AI 意图理解 + 业务词扩展 + Meilisearch
```

这个方向是正确的。

需要继续优化的点：

- 搜索模式命名要更清晰。
- 业务端应该看到“为什么匹配”。
- 需要建立搜索评测集，不能只靠主观体验。
- 长句搜索、模糊搜索、业务表达搜索应该重点进入 Meilisearch / AI 理解链路。

---

## 5. 主要风险点

### 5.1 ImageService 过大

这是当前第一优先级的结构风险。

ImageService 当前同时处理：

- 上传
- 删除 / 恢复 / 彻底删除
- 修改标题
- 人工标签
- AI 分析结果保存
- analysis run 创建
- 搜索索引同步
- 图片内容读取
- 下载

建议拆分为：

```text
ImageUploadService
ImageLifecycleService
ImageTaggingService
ImageAnalysisService
ImageSearchIndexService
```

短期可以先拆 AI 分析相关逻辑，因为这部分后面最容易继续膨胀。

### 5.2 API 层开始承担业务编排

上传接口现在不仅负责接收文件，还参与自动分析任务调度。

建议目标：

```text
API 只处理 HTTP、鉴权、请求响应
Service 负责业务用例
Task/Worker 负责异步任务
Provider 负责外部模型调用
```

这样以后从本地 BackgroundTasks 切到线上任务队列时，不需要大改 API。

### 5.3 搜索逻辑分散

当前数据库 repository 中已有一些搜索扩展逻辑。短期没问题，但长期应该把搜索意图、业务词扩展、召回策略、排序策略收口到 SearchService 或独立 SearchDomain 中。

理想结构：

```text
SearchService
  ├─ QueryUnderstandingService
  ├─ QueryExpansion
  ├─ DatabaseSearchAdapter
  ├─ MeilisearchAdapter
  └─ SearchRankingService
```

### 5.4 AI 任务不够耐久

FastAPI BackgroundTasks 适合现在阶段，但线上可能出现：

- 服务重启导致任务丢失
- 并发任务难以控制
- 失败后没有自动重试
- 没有任务队列监控

后续可以考虑：

- RQ
- Celery
- Dramatiq
- Arq

项目现阶段不必马上引入，但架构上要预留。

### 5.5 文档与实际状态有偏差

部分旧文档仍然保留了“真实模型未接入”“Docker 未验证”等旧状态。后续必须同步更新，否则会误导后续开发。

---

## 6. 推荐优化路线

### P0：文档与边界收口

目标：先把“现在项目真实状态”和“下一步边界”固定下来，防止后面越改越乱。

任务：

- 更新架构文档中的过期内容。
- 明确当前搜索模式：精准搜索、智能搜索，以及后端配置默认模式 `configured`；混合搜索保留为第三轮目标。
- 明确 AI 标签来源：`origin=manual/ai`，AI 建议用 `review_status=pending/accepted/rejected` 流转。
- 明确 Meilisearch 是派生索引，不是主数据源。
- 增加架构测试规则。

验收标准：

- 文档能准确描述当前真实项目。
- 后续开发者能看懂每个模块边界。
- 不再出现“为了一个功能随便塞进 ImageService”的情况。

### P1：拆分核心服务

目标：降低 ImageService 膨胀风险。

建议拆分：

```text
ImageService
  保留图片基础读取与聚合入口

ImageUploadService
  负责上传、文件校验、入库

ImageLifecycleService
  负责删除、恢复、彻底删除

ImageTaggingService
  负责人工标签、AI 标签、业务标签 review

ImageAnalysisService
  负责 analysis run、AI 结果落库、分析状态

ImageSearchIndexService
  负责同步 / 重建搜索索引
```

验收标准：

- ImageService 不再承担所有职责。
- AI 分析相关逻辑有独立入口。
- 删除 / 恢复 / purge 与上传逻辑分离。
- 搜索索引同步逻辑不散落在多个业务方法里。

### P2：搜索体系升级

目标：解决业务端“怎么搜都能搜准”的核心痛点。

建议搜索模式：

```text
精准搜索
  数据库字段 + 标签 + 标题 + 业务词扩展

智能搜索
  AI 搜索意图理解 + Meilisearch 模糊召回

混合搜索
  数据库召回 + Meilisearch 召回 + 规则重排 + 匹配原因
```

需要新增：

- 搜索评测集
- 业务表达词库
- 家长痛点词库
- 六大体系同义词
- 搜索结果匹配原因
- 搜索模式切换开关

示例搜索评测集：

| 搜索词 | 期望匹配方向 |
|---|---|
| 孩子写作业磨蹭 | AI 自学 / 规划 / 陪学相关图片 |
| 家长不知道怎么给孩子规划 | 同步规划体系 |
| 中考冲刺提分 | 同步考点 / 培养 / 规划相关图片 |
| AI 私教答疑 | 同步自学体系 |
| 教材动画讲解 | 同步校内体系 |
| 错题本整理 | 同步自学 / 考点体系 |

验收标准：

- 业务端输入短词、长句、模糊表达都能召回合理图片。
- 每条搜索结果能展示匹配原因。
- 至少建立 50 条人工评测 query。
- 每次搜索逻辑变更后，可以跑评测集对比效果。

### P3：AI 打标升级

目标：让设计师上传图片后，自动生成更完整、可解释、可审核的隐性标签。

推荐流程：

```text
设计师上传图片
  ↓
选择主体系 / 二级标签 / 可选人工标签
  ↓
图片保存成功
  ↓
自动触发 AI 分析
  ↓
AI 生成隐性标签、业务标签、可能匹配的其他二级标签
  ↓
系统区分人工选择与 AI 建议
  ↓
设计师可确认、驳回、重新分析
  ↓
最终进入搜索索引
```

关键规则：

- 人工选择优先级高于 AI 建议。
- AI 可以补充其他适配标签，但不能覆盖人工选择。
- AI 标签必须有 confidence。
- AI 标签必须能说明 reason。
- 重新分析不应该直接清空人工确认结果，除非用户明确选择覆盖。

验收标准：

- 上传后无需手动点击即可进入 AI 分析。
- 分析状态可见：queued、running、succeeded、failed。
- AI 建议与人工确认状态清晰区分。
- 重新分析不会误伤人工标签。

### P4：线上部署与任务可靠性

目标：从本地可跑升级到线上稳定运行。

建议改造：

- 引入任务队列处理 AI 分析。
- 数据库迁移从应用启动中拆成 release step。
- storage 后续可切换对象存储。
- Meilisearch 增加备份与索引重建脚本。
- 增加模型调用超时、重试、限流、成本记录。
- 增加日志与错误监控。

验收标准：

- 服务重启不丢 AI 任务。
- AI 调用失败可重试。
- 搜索索引可一键重建。
- 线上环境变量与密钥不写死在代码中。
- Docker Compose / 部署文档可以完整复现。

---

## 7. 标签系统优化规则

### 7.1 标签来源必须明确

当前业务标签必须同时明确来源和审核状态：

```text
origin:
  manual
  ai
  system，可选

review_status:
  accepted
  pending
  rejected
```

含义：

- `origin=manual`：设计师或管理员人工选择，默认 `review_status=accepted`。
- `origin=ai` + `review_status=pending`：AI 自动建议，未人工确认。
- `origin=ai` + `review_status=accepted`：AI 建议后被人工确认，可提升为人工附加标签。
- `origin=ai` + `review_status=rejected`：AI 建议后被人工驳回，后续重新分析不应反复推回。
- `origin=system`：系统根据规则自动产生，当前只作为后续扩展口径。

如果前端或文档需要展示 `ai_suggested`、`ai_confirmed`、`ai_rejected`，只能作为上述字段组合的展示别名，不能新增一套事实来源字段。

### 7.2 标签层级必须稳定

推荐层级：

```text
六大体系
  ↓
二级标签
  ↓
三级标签，可选
  ↓
业务表达词 / 隐性标签
```

注意：

- 六大体系和二级标签是结构标签。
- 业务表达词和隐性标签是搜索增强标签。
- 不要把所有词都混成同一种标签，否则后期会无法治理。

### 7.3 新增标签不能导致大面积改代码

后续新增二级或三级标签时，理想流程应该是：

```text
修改 catalog
  ↓
运行 catalog 校验
  ↓
同步数据库 tags
  ↓
更新 AI prompt/skill 规则
  ↓
重建搜索索引
```

不应该出现：

- 到处改 if else
- 前端写死标签名
- 后端写死业务体系名称
- AI prompt 与 catalog 不一致

---

## 8. 搜索系统优化规则

### 8.1 搜索不是单一关键词匹配

业务方可能输入：

- 单个词：`中考`
- 短语：`AI 私教`
- 一句话：`家长想找一张孩子学习规划的图`
- 模糊表达：`孩子不自觉，没人管`
- 业务标题：`同步教材动画讲解，当天学当天会`

所以搜索系统必须同时支持：

- 精准字段匹配
- 标签匹配
- 业务表达词匹配
- 同义词扩展
- AI 意图理解
- 模糊召回
- 结果重排

### 8.2 搜索结果要有匹配原因

业务端最好不要只看到图片，还要知道为什么出来。

示例：

```text
匹配原因：
- 命中标签：同步自学体系 / AI 私教答疑
- 命中业务表达：孩子不会题、随时答疑
- 命中家长痛点：没人辅导、作业卡住
```

这会极大提高业务方对系统的信任。

### 8.3 搜索优化必须有评测集

后续不能只靠“感觉好像搜得准”。

建议建立 `search_eval_cases`，至少包含：

- query
- 期望图片 id
- 期望体系
- 期望二级标签
- 期望业务表达
- 允许召回的相关图片
- 不应该出现的图片

这样每次改搜索逻辑，都可以对比：

- 召回率
- 前 3 命中率
- 前 5 命中率
- 误召回情况

---

## 9. 测试与质量保障

当前测试已经覆盖部分后端逻辑，但还需要补强。

建议新增测试：

### 9.1 架构边界测试

- Service 不允许导入 FastAPI。
- Repository 不允许调用 commit。
- Repository 不允许依赖 Service。
- API 不直接操作数据库模型细节。
- AI 输出必须经过 normalizer。
- 搜索索引必须可以从数据库重建。

### 9.2 AI 分析测试

- 图片分析成功写入 content tags。
- AI 标签必须绑定 catalog 中存在的体系。
- AI 返回脏数据时必须被拦截。
- 重新分析不覆盖人工确认标签。
- 模型失败时 analysis run 标记 failed。

### 9.3 搜索测试

- 精准搜索能命中标题。
- 标签搜索能命中标签。
- 业务表达能命中相关图片。
- 长句搜索能进入智能搜索路径。
- Meilisearch 不可用时能降级到数据库搜索。

### 9.4 前端测试

- 上传后显示 AI 分析状态。
- 搜索模式切换有效。
- AI 标签与人工标签展示不同状态。
- 重新分析按钮不会误导用户。

---

## 10. 建议的文件级改造清单

### 后端

优先关注：

```text
backend/app/services/image_service.py
backend/app/services/analysis_tasks.py
backend/app/services/search_service.py
backend/app/repositories/image_repository.py
backend/app/api/v1/images.py
backend/app/ai/normalizer.py
backend/app/domain/taxonomy_catalog.py
```

建议新增：

```text
backend/app/services/image_upload_service.py
backend/app/services/image_lifecycle_service.py
backend/app/services/image_tagging_service.py
backend/app/services/image_analysis_service.py
backend/app/services/image_search_index_service.py
backend/app/services/query_understanding_service.py
backend/app/domain/search_eval.py
```

### 前端

优先关注：

```text
client/src/pages/ImageDetail/ImageDetail.tsx
client/src/pages/ImageHome/ImageHome.tsx
client/src/features/images/useImageBrowser.ts
client/src/pages/ImageHome/UploadDialog.tsx
client/src/pages/ImageHome/SemanticSearchResult.tsx
```

建议新增：

```text
client/src/features/images/hooks/useImageListQuery.ts
client/src/features/images/hooks/useImageSearch.ts
client/src/features/images/hooks/useImageFilters.ts
client/src/features/images/components/ImageAnalysisPanel.tsx
client/src/features/images/components/BusinessLabelPanel.tsx
client/src/features/images/components/ContentTagsPanel.tsx
client/src/features/images/components/SearchModeSwitch.tsx
```

### 文档

需要同步更新：

```text
docs/ARCHITECTURE.md
docs/PROJECT_HANDOVER.md
docs/SEARCH_MODES_AND_AI.md
docs/AI_SEARCH_ARCHITECTURE.md
docs/TAG_SYSTEM_AUDIT.md
```

---

## 11. 推荐执行顺序

不要一次性大重构。建议分五轮执行。每一轮只解决一个主要问题，完成后必须把实际改动补回“改造变更记录”。

### 第一轮：文档和边界

目标：先把项目真实状态、模块边界、改造规则固定下来。第一轮主要是“加护栏”，不是大动业务代码。

允许改动：

- 更新过期文档。
- 明确当前真实架构。
- 增加架构测试。
- 明确标签来源与搜索模式。

禁止改动：

- 不重写上传流程。
- 不重写搜索流程。
- 不改变数据库主结构，除非只是补充非破坏字段。
- 不改变前端主交互。
- 不删除已有 AI 分析结果结构。

交付物：

- 更新后的架构文档。
- 更新后的搜索与 AI 文档。
- 架构边界测试。
- 标签来源规则说明。
- 本文档中的变更记录。

验收标准：

- 后端测试通过。
- 前端 typecheck 通过。
- Docker 服务正常。
- 文档描述与当前代码一致。
- 后续开发者能根据文档判断某段逻辑应该放在哪一层。

### 第二轮：拆 ImageService

目标：降低 ImageService 继续膨胀的风险，但保持外部接口稳定。

允许改动：

- 先拆 AI 分析相关逻辑。
- 再拆生命周期逻辑。
- 保持接口不大改，避免前端震荡。

建议拆分顺序：

1. 先拆 `ImageAnalysisService`  
   负责 analysis run、AI 分析结果保存、重新分析规则、分析状态流转。

2. 再拆 `ImageLifecycleService`  
   负责删除、恢复、彻底删除、文件清理策略。

3. 再拆 `ImageTaggingService`  
   负责人工标签、AI 标签、业务标签确认/驳回。

4. 最后整理 `ImageSearchIndexService`  
   负责搜索索引同步、重建、失败降级。

禁止改动：

- 不一次性重写全部图片服务。
- 不改变已有 API 响应结构，除非同步更新前端类型和文档。
- 不让新服务绕过 UnitOfWork 直接提交事务。
- 不让 AI 分析服务直接处理 HTTP 请求。

交付物：

- 拆分后的 service 文件。
- 旧 ImageService 只保留聚合入口或基础图片能力。
- 对应单元测试或至少回归测试。
- 本文档中的变更记录。

验收标准：

- 上传、删除、恢复、详情、AI 分析、搜索全部正常。
- 现有后端测试通过。
- 前端无需大面积适配。
- 新服务职责能用一句话讲清楚。

### 第三轮：搜索优化

目标：解决业务端“怎么搜都能搜准”的核心体验问题。

允许改动：

- 建搜索评测集。
- 补业务表达词。
- 增加匹配原因。
- 优化智能搜索与 Meilisearch 的切换逻辑。

建议拆分：

- `QueryUnderstandingService`：理解用户搜索意图。
- `QueryExpansion`：扩展业务表达、家长痛点、六大体系同义词。
- `DatabaseSearchAdapter`：负责数据库召回。
- `MeilisearchAdapter`：负责搜索引擎召回。
- `SearchRankingService`：负责排序与匹配原因。

禁止改动：

- 不把 Meilisearch 改成唯一数据源。
- 不因为智能搜索而删掉数据库精准搜索。
- 不让搜索结果无法解释。
- 不只凭主观感觉调搜索规则，必须逐步建立评测集。

交付物：

- 搜索评测集。
- 搜索模式说明。
- 匹配原因字段或展示方案。
- 业务表达词库与家长痛点词库。
- 智能搜索失败降级逻辑。

验收标准：

- 单词、短语、长句、模糊表达都能正常搜索。
- Meilisearch 不可用时能回退。
- 至少 50 条搜索评测 query。
- 搜索结果能说明命中了标题、标签、业务表达还是体系词。

### 第四轮：AI 打标升级

目标：让设计师上传图片后，AI 自动生成的隐性标签、业务标签和体系建议更完整、可解释、可审核，同时不污染人工标签。

允许改动：

- 补强 AI 分析状态流转：queued、running、succeeded、failed。
- 明确 content tags、business labels、体系建议的来源、confidence、reason。
- 增加 AI 建议的确认、驳回、重新分析规则。
- 优化 AI normalizer、taxonomy catalog 校验和异常拦截。
- 让前端清晰展示人工标签、AI 建议、已确认、已驳回状态。

禁止改动：

- 不让 AI 覆盖人工标签。
- 不让重新分析默认清空人工确认结果。
- 不跳过 schema 校验和 taxonomy 校验直接写库。
- 不把模型 prompt 或模型输出当成事实源。
- 不让 AI 分析失败影响图片基础上传和查看。

交付物：

- AI 标签状态流转说明。
- AI 建议确认/驳回/重新分析方案或接口。
- AI 输出校验与脏数据拦截测试。
- 前端 AI 标签状态展示方案。
- 本文档中的变更记录。

验收标准：

- 上传后能自动进入 AI 分析，或明确显示等待分析状态。
- AI 建议与人工标签状态清晰区分。
- AI 脏数据不会进入正式业务标签。
- 重新分析不会误伤人工确认标签。
- 模型失败时图片仍然可用，并能看到失败状态。

### 第五轮：线上稳定性

目标：把本地可用系统升级成线上更稳定的系统。

允许改动：

- 引入任务队列。
- 拆部署 migration step。
- 增加错误监控。
- 增加搜索索引重建与模型调用成本控制。

禁止改动：

- 不把线上部署逻辑写死在本地开发逻辑中。
- 不在应用启动时做不可控的重型任务。
- 不让 AI 任务失败影响图片基础上传。
- 不让搜索索引不可重建。

交付物：

- 任务队列方案。
- AI 任务重试与失败记录。
- 部署 checklist。
- 搜索索引重建脚本。
- 模型调用超时、重试、错误日志。

验收标准：

- 服务重启不丢已入队任务。
- AI 分析失败可重试。
- 搜索索引可一键重建。
- 本地和线上环境变量清晰分离。
- Docker 部署流程可复现。

---

## 12. 改造变更记录

本节用于记录每一轮实际改造内容。后续每完成一次阶段性优化，都必须补充记录。

### 2026-06-24：优化文档升级 - 改造指南与约束

改造目标：

- 将原本的优化路线图升级为后续改造的施工指南。
- 增加改造纪律、禁止事项、验收标准、每轮改造合同。
- 明确后续每轮优化必须记录“改了什么、没改什么、验证了什么、遗留了什么”。

实际改动：

- 新增“使用方式与改造纪律”章节。
- 新增每轮改造的允许改动、禁止改动、交付物、验收标准。
- 新增改造变更记录章节。
- 明确第一轮以文档和边界为主，不动核心业务主流程。
- 明确第二轮拆 ImageService 时保持 API 稳定。
- 明确第三轮搜索优化必须建立评测集。
- 明确第四轮 AI 打标升级要处理状态流转、确认/驳回、重新分析与脏数据拦截。
- 明确第五轮线上稳定性要处理任务队列、索引重建、部署流程。

明确没有改动：

- 没有改动后端业务代码。
- 没有改动前端页面。
- 没有改动数据库结构。
- 没有改变当前上传、AI 分析、搜索主流程。

验证结果：

- 文档已写入 `docs/OPTIMIZATION_PLAN.md`。
- 本次仅为文档约束升级，不涉及代码测试。

风险与遗留：

- 现有架构文档、交接文档中仍可能存在旧状态描述，第一轮优化时需要同步更新。
- 后续代码改造完成后，需要继续在本节补充真实变更记录。

下一步：

- 执行第一轮优化：文档同步、架构测试补强、标签来源和搜索模式规则固化。

### 2026-06-24：优化文档修正 - 执行轮次对齐

改造目标：

- 统一“推荐优化路线”和“推荐执行顺序”的轮次口径。
- 避免 AI 打标升级被混入搜索优化、服务拆分或线上稳定性改造中。

实际改动：

- 将推荐执行顺序从四轮修正为五轮。
- 新增“第四轮：AI 打标升级”的允许改动、禁止改动、交付物和验收标准。
- 将原“第四轮：线上稳定性”顺延为“第五轮：线上稳定性”。
- 更新上一条文档升级记录中的轮次说明。

明确没有改动：

- 没有改动后端业务代码。
- 没有改动前端页面。
- 没有改动数据库结构。
- 没有改变当前上传、AI 分析、搜索主流程。

验证结果：

- 已检查文档中不再存在“四轮”与 `P0-P4` 的冲突描述。
- 本次仅为文档修正，不涉及代码测试。

风险与遗留：

- 第一轮优化时仍需同步检查其他文档是否沿用旧的四轮口径。

下一步：

- 执行第一轮优化：文档同步、架构测试补强、标签来源和搜索模式规则固化。

### 2026-06-24：第一轮优化 - 文档同步与架构护栏

改造目标：

- 解决“优化越改越乱”的风险，先补边界和验证护栏。
- 同步过期文档中的模型、搜索、标签来源和部署状态口径。
- 增加轻量架构测试，防止后续把业务逻辑塞错层。

实际改动：

- 更新 `docs/ARCHITECTURE.md`，明确 OpenAI-compatible Provider、Meilisearch 派生索引、AI 输出校验和标签来源流转。
- 更新 `docs/PROJECT_HANDOVER.md` 中容易误导的“真实模型未接入”旧表述。
- 更新 `docs/TAG_SYSTEM_AUDIT.md` 和 `docs/AI_SEARCH_ARCHITECTURE.md` 的当前状态说明。
- 修正本文档中 AI 标签来源口径：以 `origin=manual/ai` 和 `review_status=pending/accepted/rejected` 为真实字段。
- 修正本文档中搜索模式口径：当前是精准搜索、智能搜索和后端 `configured` 默认模式；混合搜索保留为第三轮目标。
- 补强 `backend/tests/test_architecture.py`，新增 Repository 不提交事务、路由层不依赖 Repository/SQLAlchemy、应用代码不直接建表/删表、外部搜索不进入 Repository、AI 服务必须调用 normalizer 等护栏。

明确没有改动：

- 没有改动上传、删除、恢复、详情、搜索、AI 分析等业务主流程代码。
- 没有改动前端页面和交互。
- 没有改动数据库结构和 Alembic migration。
- 没有引入新的依赖或服务。

验证结果：

- 后端测试：`49 passed`。
- 前端检查：`npm run typecheck` 通过。
- Docker 状态：backend、web、postgres、meilisearch 均为 `Up` 且 `healthy`。
- 健康检查：`/health/live` 与 `/health/ready` 均返回成功。

风险与遗留：

- 本轮只做边界收口，没有拆分 `ImageService`。
- 交接素材稿仍是历史素材，不应作为后续改造依据；后续以 README、架构文档、搜索模式文档和当前代码为准。
- 上传/分析/搜索的完整手工业务回归可在第二轮改造前后再跑一次。

下一步：

- 进入第二轮前，先确认是否只拆 AI 分析相关逻辑，不同时动搜索和前端主交互。

### 2026-06-24：第二轮优化 - 拆出 ImageAnalysisService

改造目标：

- 降低 `ImageService` 膨胀风险，先拆出最容易继续变重的 AI 分析职责。
- 保持上传、详情、搜索、AI 手动分析和前端响应结构稳定。
- 用架构测试防止分析逻辑后续重新塞回 `ImageService`。

实际改动：

- 新增 `backend/app/services/image_analysis_service.py`。
- 将 analysis run 创建、running/failed 状态流转、AI 分析结果落库、AI 业务标签建议生成、分析后搜索索引同步迁入 `ImageAnalysisService`。
- `ImageService` 移除 `create_analysis_run`、`mark_analysis_running`、`mark_analysis_failed`、`save_ai_analysis` 和 AI 分析结果实体依赖。
- 上传接口通过 `get_image_analysis_service` 创建后台分析任务，原上传响应结构不变。
- 手动 AI 分析接口改由 `ImageAnalysisService.save_ai_analysis` 落库，原响应结构不变。
- 后台任务 `analysis_tasks.py` 改用 `ImageAnalysisService` 处理任务状态和分析结果。
- `serializers.py` 对 analysis run 状态做 API 边界收口，保证响应只输出 queued/running/succeeded/failed。
- 补充架构测试，禁止 `ImageService` 重新持有 `AnalysisRun`、`ContentTag`、`ImageAnalysisResult` 等分析持久化职责。

明确没有改动：

- 没有改动数据库结构和 Alembic migration。
- 没有改动前端页面和交互。
- 没有改动 API 响应字段。
- 没有改动上传文件校验、删除、恢复、永久删除、下载计数和搜索行为。
- 没有引入任务队列、OCR、向量检索或新的模型 Provider。

验证结果：

- 本地后端测试：`50 passed`。
- 容器内后端测试：`50 passed`。
- Ruff：`All checks passed!`
- Pyright：`0 errors, 0 warnings, 0 informations`。
- 前端 typecheck：`npm run typecheck` 通过。
- Docker 重建：`docker compose up --build -d` 成功。
- Docker 状态：backend、web、postgres、meilisearch 均为 `Up` 且 `healthy`。
- 健康检查：`/health/live` 与 `/health/ready` 均返回成功。
- 前端首页：`http://127.0.0.1/` 返回 200。

风险与遗留：

- 本轮只拆 AI 分析持久化职责，`ImageService` 仍保留上传、生命周期、人工标签和 AI 建议审核逻辑。
- AI 建议接受/拒绝逻辑仍在 `ImageService.review_business_label`，后续可在第二轮后半段或第三个小步拆到 `ImageTaggingService`。
- FastAPI BackgroundTasks 仍是当前异步机制，线上可靠任务队列留到第五轮。

下一步：

- 继续第二轮时，优先拆 `ImageLifecycleService` 或 `ImageTaggingService`，一次只拆一个方向。

---

## 13. 关键决策点

后续开发前，需要确认几个产品级规则。

### 13.1 AI 建议是否自动生效？

推荐规则：

- AI content tags 可以自动进入搜索。
- AI business labels 默认是 suggested。
- 高置信度标签可以参与搜索，但前端要显示 AI 建议状态。
- 人工确认后才变为 confirmed。

### 13.2 设计师人工选择与 AI 建议冲突时怎么办？

推荐规则：

- 人工选择永远优先。
- AI 可以补充其他适配标签。
- AI 不允许覆盖人工标签。
- 冲突要记录 reason，给用户判断。

### 13.3 搜索默认使用哪种模式？

推荐规则：

- 普通输入默认智能搜索。
- 后台保留精准搜索开关。
- 搜索失败时自动降级数据库搜索。
- 管理端可看到当前搜索模式和召回来源。

### 13.4 三级标签什么时候引入？

推荐规则：

- 不要过早引入三级标签。
- 先用业务表达词和隐性标签解决搜索问题。
- 当二级标签下图片量明显变大、业务方筛选困难时，再引入三级标签。

---

## 14. 最终建议

这个项目现在不需要推倒重来。最好的策略是：

> 保留现有主架构，先做边界收口，再做搜索评测，再升级 AI 任务可靠性。

短期最重要的不是继续堆更多按钮，而是把几个核心逻辑钉住：

- 六大体系是主锚点。
- 数据库是事实源。
- Meilisearch 是搜索增强索引。
- AI 是建议与理解层。
- 人工标签与 AI 标签必须区分来源。
- 搜索优化必须有评测集。
- ImageService 必须逐步拆小。

只要这几个原则守住，后面无论继续加图片、加标签、加 OCR、加 GPT 模型、加线上部署，都不会走偏。
