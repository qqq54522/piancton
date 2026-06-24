# 搜索词扩展与标签词库维护说明

状态：已接入本地数据库搜索与语义搜索接口，未强制依赖大模型或 Meilisearch。

## 目标

业务方不一定会搜索标准标签名。比如图片标签是“动画精讲”，业务方可能搜：

- 孩子听不懂老师讲课
- 老师讲太快
- 抽象知识看不懂
- 卡壳

因此项目先用确定性词库把自然表达扩展成标准业务标签，再进入数据库搜索。这样本地可跑、部署稳定，不会因为第三方模型接口不可用导致基础检索失效。

## 当前链路

```mermaid
flowchart LR
  A["用户搜索词"] --> B["taxonomy/catalog.json"]
  B --> C["扩展标准标签名、code、别名、证据词"]
  C --> D["数据库检索标题、摘要、人工标签、AI 内容标签、AI 业务标签、AI 理由"]
  D --> E["返回图片"]
```

核心代码：

- `backend/app/domain/search_query_expansion.py`
- `backend/app/repositories/image_repository.py`
- `backend/app/services/search_service.py`
- `taxonomy/catalog.json`

## 词库来源

`taxonomy/catalog.json` 是权威来源。每个二级标签至少维护：

- `name`：标准标签名，例如“动画精讲”。
- `code`：稳定业务编码，例如 `animation_explanation`。
- `aliases`：业务方可能搜索的短词、别称、口语表达。
- `positive_evidence`：图片或文案中出现时，可以支持该标签的证据词。
- `negative_evidence`：排除边界，主要给 AI 打标和后续人工审核参考。

## 新增二级或三级标签时怎么做

1. 在 `taxonomy/catalog.json` 中新增节点，必须给稳定 `code`。
2. 补充 5 到 10 个业务方可能搜索的 `aliases`。
3. 补充 5 到 10 个 `positive_evidence`，优先写家长痛点、业务话术、图片可见信息。
4. 如果这个标签来自某个文案卖点，在 `copy_points` 中增加映射。
5. 跑测试：

```bash
docker compose exec -T backend python -m pytest -q
```

6. 如果已启用 Meilisearch，再重建搜索索引：

```bash
docker compose exec -T backend python -m scripts.rebuild_search_index
```

## 当前边界

- 当前扩词是确定性规则，不是每次搜索都调用大模型。
- 大模型仍适合用于更高级的“长句意图理解”和“无词命中”，但不应该成为基础搜索唯一入口。
- Meilisearch 当前是可选增强层；主数据仍在数据库中，索引可以随时重建。
- 被拒绝的 AI 业务标签不会参与搜索。

## 已验证样例

- “课后小测”可以命中 AI 建议标签。
- “教材同步”可以命中内容/业务标签。
- “孩子听不懂老师讲课”可以扩展到“动画精讲”并命中。
- “火锅店菜单”不会误命中教育卖点图片。
