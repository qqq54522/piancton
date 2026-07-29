# Piancton 六大体系卖点意图 SFT 数据集 v1

生成日期：2026-07-24

## 文件

- `piancton_six_system_selling_point_intent_v1_train_upload.jsonl`：训练集，推荐直接上传。
- `piancton_six_system_selling_point_intent_v1_validation_upload.jsonl`：验证集，平台支持 validation 时上传。
- `piancton_six_system_selling_point_intent_v1_all_upload.jsonl`：训练 + 验证全集，平台只允许上传一个文件时使用。
- 不带 `_upload` 的同名文件保留了 `metadata`，方便内部追溯来源，不优先用于平台上传。

## 推荐上传选择

在你截图里的「数据格式」请选择：`文本生成` → `SFT 精调`。

如果平台支持训练/验证分开上传，上传 `train_upload.jsonl` 做训练，上传 `validation_upload.jsonl` 做验证。
如果平台只让上传一个文件，上传 `all_upload.jsonl`。

## 数据来源

- `taxonomy/search_eval_cases.json`：现有 CI/本地评测金标准查询，共 103 条。
- `taxonomy/business_intents.json`：16 个核心卖点的已审核标准表达和典型痛点。
- `skills/understand-image-search-intent/references/selling-point-map.json`：六大体系与 16 个 stable code 映射。
- 手工补充 6 条边界样本，用于避免“提分/省心/拍一下/纯画面”等表达被过度硬路由。

## 样本统计

- 全集：319 条
- 训练集：287 条
- 验证集：32 条
- 查询状态分布：
  - ambiguous_business_intent_search: 9
  - business_intent_search: 286
  - exploratory_business_intent_search: 5
  - multi_business_intent_search: 8
  - no_reliable_intent_search: 5
  - visual_scene_search: 6

## 审计结果

- 已用项目当前 `QueryUnderstandingService` 校验 `taxonomy/search_eval_cases.json` 的 103 条 CI/评测查询：查询状态、期望卖点、排除卖点均一致，mismatch 为 0。
- 已逐行校验三份上传版 JSONL：每行均为合法 `messages` 样本，assistant 内容均为可解析 JSON。
- 已校验所有 `matched_business_concepts` 和 `excluded_concepts` 都属于当前 16 个稳定卖点 code，且体系归属与 `selling-point-map.json` 一致。
- 探索型和待消歧样本中的候选卖点已统一使用 `related` 或 `fallback`，不标记为 `direct`，避免模型把共享入口词训练成强路由。

## 输出字段

assistant 的内容是 JSON 字符串，主要字段包括：

- `original_query`
- `normalized_query`
- `search_intent`
- `query_type`
- `matched_systems`
- `matched_business_concepts`
- `matched_proof_points`
- `matched_evidence_points`
- `excluded_concepts`
- `needs_clarification`
- `search_strategy`

## 注意

这版数据主要训练「搜索话术 → 体系/卖点/查询状态」的文本理解能力，不训练图片视觉识别。
证明点和证据表达点字段先保留为空数组，避免在尚未逐条人工确认所有查询证明点时，把模型训练得过度下钻。
短词共享入口如 `拍一下`、`家长省心` 被放入边界样本，而不是正例硬绑定。
