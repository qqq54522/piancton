# ADR 0001：选择 Meilisearch 作为派生搜索引擎

状态：已选定，等待分阶段实施  
日期：2026-06-23

## 背景

Piancton 需要支持以下搜索方式：

- 六大体系与二级业务标签的精确搜索；
- 单个词、别名、前缀和错别字；
- 一句不完整或口语化的业务需求；
- 图片 OCR、视觉摘要和隐性内容标签；
- 体系、标签、颜色、人物、场景等结构化过滤；
- 第三方 Embedding 和大模型 API；
- 本地开发与线上部署使用相同搜索逻辑。

SQLite 和 PostgreSQL 继续作为主数据库。搜索索引是可重建的派生数据，不是主数据。

## 候选方案

| 方案 | 中文全文/错字 | 语义检索 | 本地与部署 | 运维复杂度 | 结论 |
|---|---|---|---|---|---|
| 仅 SQLite FTS5 + PostgreSQL 全文 | 需要维护两套实现，中文能力需额外处理 | 需另加向量实现 | 逻辑容易漂移 | 中 | 不选作主方案 |
| PostgreSQL + pgvector | 全文与向量可组合 | 强 | 本地 SQLite 无法同构 | 中 | 保留为未来备选 |
| Qdrant | 向量、过滤和混合召回强 | 强 | Python 本地模式方便 | 中 | 中文错字和全文产品体验不是最优先方向 |
| OpenSearch / Elasticsearch | 功能最全面 | 强 | 本地与部署都较重 | 高 | 当前规模过度设计 |
| Typesense | 搜索体验较好 | 支持 | 需独立服务 | 中 | 许可证与当前需求匹配度不如 Meilisearch |
| Meilisearch Community Edition | 中文 jieba 分词、前缀和错字处理开箱可用 | 内置混合搜索 | 单二进制 / Docker 使用相同 API | 低到中 | 选择 |

## 决策

使用 Meilisearch Community Edition 作为统一搜索引擎：

```text
SQLite / PostgreSQL：权威主数据
Meilisearch：可重建的全文、过滤和向量搜索索引
第三方模型 API：图片理解、OCR、查询理解、Embedding、可选精排
```

### 选择原因

1. 中文使用基于 jieba 的字典分词。
2. 错字容忍、前缀匹配和分词边界修正是默认搜索能力。
3. 可同时执行关键词与语义搜索。
4. 支持多种 Embedding Provider、任意 REST API，以及应用自行提供向量。
5. Community Edition 的全文与 AI 搜索使用 MIT 许可证。
6. 单个无外部依赖的二进制可运行于 macOS、Linux 和 Windows，也可使用 Docker。
7. 当前内部图片库不需要企业版独有的分片能力。

## 本地与线上运行方式

### 本地

- SQLite 保存主数据。
- Meilisearch 使用本地单二进制进程。
- 索引数据位于项目忽略的本地目录。
- FastAPI 通过 HTTP 访问 `127.0.0.1:7700`。
- 若搜索服务不可用，后端明确降级到现有数据库模糊搜索，并在响应中标记降级。

不得把平台相关的 Meilisearch 二进制提交进 Git。

项目应提供安装检查、启动和健康检查脚本；版本必须固定，不使用不受控的 `latest`。

### 部署

- PostgreSQL 保存主数据。
- Docker Compose 增加固定版本的 Meilisearch Community Edition 服务。
- Meilisearch 使用独立持久化 volume。
- 只允许 backend 访问搜索服务，不向公网直接暴露端口。
- 使用 Master Key，并通过后端环境变量传入。
- Meilisearch 索引可由 PostgreSQL 和图片分析结果完全重建。

## 第三方 API 边界

应用层继续拥有 Provider：

- `VisionProvider`
- `OcrProvider`
- `QueryUnderstandingProvider`
- `EmbeddingProvider`
- `RerankProvider`

首选由后端调用第三方 API，再将生成的向量写入 Meilisearch。这样：

- 第三方 API Key 只保存在 backend；
- 可以使用任意供应商；
- 切换模型时可记录版本并控制重新索引；
- 搜索服务不直接持有所有模型密钥。

Meilisearch 原生和 REST Embedder 作为可配置备选，不作为唯一接入路径。

## 索引文档

每张图片在 Meilisearch 中只有一个搜索文档：

```json
{
  "id": "image UUID",
  "manualPrimaryLabelCode": "photo_learn",
  "manualLabelCodes": ["photo_learn"],
  "acceptedAiLabelCodes": ["universal_method"],
  "pendingAiLabelCodes": ["ai_tutor"],
  "systems": ["sync_self_study", "sync_cultivation"],
  "ocrText": ["拍题精学", "解题思路"],
  "caption": "学生使用手机拍摄数学题，界面展示分步讲解。",
  "contentTags": ["学生", "手机", "试卷", "拍题", "分步讲解"],
  "searchPhrases": ["拍题后逐步讲明白", "不是直接给答案"],
  "negativeConcepts": ["真人老师督学"],
  "colors": ["蓝色", "紫色"],
  "styles": ["科技感"],
  "status": "active",
  "analysisVersion": "2026.06",
  "_vectors": {
    "image-semantic": [0.0]
  }
}
```

只在搜索索引中保存检索所需字段。完整审核记录、Prompt 版本和模型响应仍保存在主数据库。

## 搜索流程

```text
用户输入
  -> 标准标签和别名直接匹配
  -> 复杂查询可选调用大模型生成查询计划
  -> Meilisearch 关键词 + 语义混合搜索
  -> 结构化过滤和排除项
  -> Top K 可选第三方 Reranker
  -> 从主数据库读取最终图片详情
```

大模型不直接扫描整个图片库。

## 数据一致性

采用主数据库优先、搜索索引最终一致：

1. 图片或标签事务先提交主数据库。
2. 写入 `search_outbox` 事件。
3. worker 将变更同步到 Meilisearch。
4. 同步成功后标记事件完成。
5. 提供全量 `rebuild-search-index` 命令。

不在数据库事务中同步等待 Meilisearch，否则搜索服务故障会阻断上传和编辑。

## 降级策略

- Meilisearch 不可用：使用当前 SQL 模糊搜索。
- Embedding API 不可用：只执行 Meilisearch 关键词搜索。
- 查询理解模型不可用：使用原始查询和目录别名。
- Reranker 不可用：使用 Meilisearch 混合排序。
- 索引落后：返回结果时以主数据库的删除状态和权限做最后校验。

## 不采用的做法

- 不直接复制或修改 Meilisearch 源代码。
- 不把 Meilisearch 当作主数据库。
- 不在现阶段同时部署 Meilisearch 和 Qdrant。
- 不让第三方大模型逐张扫描全库。
- 不把 API Key 放进前端。
- 不依赖图片标题作为主要检索信息。

## 重新评估条件

出现以下情况时重新评估 Qdrant、pgvector 或 OpenSearch：

- 图片量进入百万级并需要搜索分片；
- 需要复杂多向量或大规模以图搜图；
- 需要多节点高可用搜索集群；
- 需要 Meilisearch 无法支持的高级分析器；
- 实际评测证明其中文检索不满足业务指标。

在此之前，以搜索评测结果而不是技术流行度决定是否更换。
