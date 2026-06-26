# 搜索模式、大模型理解与图片语义补标

状态：已接入“精准搜索 / 智能搜索”手动切换；模型 Provider 已配置时，图片上传后由后端自动排队执行 AI 语义补标；Meilisearch 作为智能搜索增强层，失败时自动回退数据库搜索。

## 两种搜索模式

### 精准搜索

适合业务方已经知道要找什么：

- 完整标题、长标题、文件名；
- 六大体系名称；
- 二级标签；
- 明确业务表达。

底层逻辑：

1. 使用 `taxonomy/catalog.json` 做业务词扩展；
2. 查数据库里的标题、摘要、人工标签、隐性内容标签、二级业务标签和 AI 理由；
3. 标题匹配做双向判断：搜索词包含标题，或标题包含搜索词，都算标题命中。
4. 图片摘要是重要语义匹配字段；搜索词命中摘要，或长搜索句包含整段摘要时，会作为强语义匹配进入排序。

这保证了“复制一长串标题或文案”时，不会因为搜索词比真实标题更长而搜不到。

### 智能搜索

适合业务方输入模糊自然语言：

- “孩子听不懂老师讲课”；
- “家长不会辅导”；
- “有没有考前突击的图”；
- “学习没方向，不知道怎么规划”。

底层逻辑：

1. 如果模型 Provider 已配置，先调用大模型做搜索意图理解；
2. 将模型输出的标准查询、扩展标签、二级分类候选加入搜索计划；
3. 优先尝试 Meilisearch；
4. 如果 Meilisearch 不可用，自动回退到数据库搜索；
5. 前端展示降级提示，不影响业务方继续拿到结果。

## 大模型在这里做什么

大模型只做“理解”和“补标”，不直接决定最终返回哪张图。

### 搜索意图理解

输入：

```json
{
  "keyword": "孩子听不懂老师讲课"
}
```

模型输出会被后端校验并归一化。例如模型返回 `animation_explanation`，系统会展示为：

```text
同步校内体系 > 动画精讲
```

这样保留 code 的稳定性，同时避免业务界面出现难懂的英文 code。

### 图片语义补标

设计师上传图片后，上传接口会在后端判断模型 Provider 是否已配置：

- 如果已配置：自动创建一条 `queued` 分析任务，并在后台执行图片语义分析；
- 如果未配置：图片照常上传，后续可在详情页手动点击“重新分析”；
- 前端不再负责上传后额外调用分析接口，避免页面卡住、状态缓存过期或网络中断导致漏分析。

手动重跑接口仍然保留：

```text
POST /api/ai/images/{image_id}/analyze
```

它会调用视觉模型生成：

- 图片摘要；
- 18 到 22 个隐性内容标签；
- 推荐搜索词；
- 二级业务标签建议；
- 置信度和理由。

模型输出仍然受六大体系目录约束，不能凭空发明二级标签。

详情页会展示最新分析任务状态：

- `queued`：已排队；
- `running`：分析中；
- `succeeded`：已完成；
- `failed`：分析失败。

当最新任务处于 `queued` 或 `running` 时，详情页会自动轮询刷新；设计师不能重复点击“重新分析”，避免同一张图同时跑多次。

### AI 建议的采纳规则

AI 自动匹配的业务标签默认不是最终归档结果，而是 `pending` 状态的建议。

设计师点击“接受”后：

- 原设计师主标签不会被覆盖；
- 该 AI 建议会被追加为设计师附加标签；
- 这个标签会进入最终归档和搜索权重；
- 原 AI 建议仍保留为 `accepted`，用于追踪来源和理由。

设计师点击“拒绝”后：

- 该 AI 建议保留为 `rejected`；
- 不会进入最终人工标签；
- 后续重新分析不会把同一个已拒绝标签反复作为新待审核建议推回来。

重新分析时：

- 图片摘要、隐形内容标签和未审核 AI 建议会刷新；
- 已接受、已拒绝的 AI 判断会保留；
- 已经转成人工标签的 AI 建议不会重复生成一条新的待审核建议。

## Meilisearch 的位置

Meilisearch 不是主数据库，也不是唯一搜索引擎。

它的位置是：

```text
智能搜索增强层
```

如果 Meilisearch 可用，智能搜索优先尝试它；如果不可用，数据库搜索会兜底。这样本地和线上都不会因为搜索容器异常导致业务方搜不到图。

## Embedding 与 Reranker 的位置

Embedding API 用于向量召回：把用户搜索词和图片语义画像转成向量，再从已保存的图片向量中召回语义相近的候选图。图片语义画像由标题、图片摘要、隐性标签、业务标签、人工标签和分类组成。

图片 AI 分析完成、标题/标签更新、AI 业务标签审核变化后，会尽力刷新该图片的 embedding。Embedding API 未配置或调用失败时，搜索会继续使用数据库 / Meilisearch 召回。

Reranker API 是可选精排层：数据库或 Meilisearch 先召回候选结果，Reranker 再根据搜索词与候选图的标题、图片摘要、隐性标签、业务标签和人工标签重新排序。如果 Reranker 未配置、超时或返回异常，搜索会自动保留原排序返回结果。

旧图片可用脚本补齐语义向量：

```bash
cd backend
python -m scripts.rebuild_embeddings
```

## 当前关键配置

```env
MODEL_PROVIDER=openai_compatible
MODEL_NAME=你的模型名
MODEL_BASE_URL=你的 OpenAI-compatible Base URL
MODEL_API_KEY=你的 API Key

MEILISEARCH_URL=http://meilisearch:7700
MEILISEARCH_API_KEY=replace-with-a-search-master-key
MEILISEARCH_INDEX=images

EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=Qwen/Qwen3-VL-Embedding-8B
EMBEDDING_TOP_N=100

RERANKER_BASE_URL=https://api.siliconflow.cn/v1
RERANKER_MODEL_NAME=Qwen/Qwen3-VL-Reranker-8B
RERANKER_TOP_N=50
```

如果模型未配置：

- 精准搜索正常；
- 智能搜索不会做模型意图理解，但仍会尝试 Meilisearch / 数据库兜底；
- 图片上传不会自动生成 AI 补标。

如果 Meilisearch 未启动：

- 精准搜索正常；
- 智能搜索会显示降级提示，并回到数据库搜索。
