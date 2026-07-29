# Piancton 六大体系卖点意图 SFT 数据集 v2 Boundary

生成日期：2026-07-24

## 这版解决什么

V1 主要训练「普通搜索话术 → 六大体系/16 个核心卖点/查询状态」。
V2 Boundary 专门训练六大体系文件里的边界：正例、反例、多卖点、探索型、待消歧和显式否定。

这版适合让模型学会：

- 共享词不能硬路由，例如 `家长省心`、`拍一下`、`提分`。
- 相邻卖点要按对象、动作、时间尺度、目的和执行主体区分。
- 显式否定进入 `excluded_concepts`，不能作为正向命中。
- 多卖点必须每个卖点都有独立证据。
- 证明点和绿色证据表达点不能升格为新核心卖点。

## 推荐上传文件

- 只上传一个文件：`piancton_six_system_selling_point_intent_v2_boundary_all_upload.jsonl`
- 平台支持训练/验证分开：
  - 训练：`piancton_six_system_selling_point_intent_v2_boundary_train_upload.jsonl`
  - 验证：`piancton_six_system_selling_point_intent_v2_boundary_validation_upload.jsonl`

不带 `_upload` 的文件保留 `metadata`，方便内部追溯来源，不优先用于平台上传。

## 样本统计

- 全集：92 条
- 训练集：81 条
- 验证集：11 条
- 查询状态分布：
  - ambiguous_business_intent_search: 8
  - business_intent_search: 57
  - exploratory_business_intent_search: 11
  - multi_business_intent_search: 15
  - no_reliable_intent_search: 1

## 数据来源

- `skills/understand-image-search-intent/references/sync-school.md`
- `skills/understand-image-search-intent/references/sync-exam.md`
- `skills/understand-image-search-intent/references/sync-cultivation.md`
- `skills/understand-image-search-intent/references/sync-planning.md`
- `skills/understand-image-search-intent/references/sync-self-study.md`
- `skills/understand-image-search-intent/references/sync-companion.md`

## 和 V1 的关系

- 如果只能上传一个数据集，优先上传 V2 的 `all_upload`，因为它更重边界。
- 如果平台允许多数据集混合，建议 V1 + V2 一起用：V1 补覆盖，V2 修边界。
- 如果后续要做第三版，建议做 `v3_proof_evidence`，专门训练证明点 `pp_` 和证据表达点 `ep_` 的下钻。
