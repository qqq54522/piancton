# Piancton 六大体系卖点意图 SFT 数据集 v3 Compact

生成日期：2026-09-07

## 目标

本版本只训练“查询状态 + 16 个稳定卖点 code + 排除 code”，不再让模型生成体系、名称、解释、权重和搜索策略等可确定性推导字段。

固定输出结构：

```json
{"query_type":"multi_business_intent_search","matched_codes":["photo_guided_learning","transfer_practice"],"excluded_codes":[]}
```

## 文件

- `piancton_six_system_selling_point_intent_v3_compact_train_upload.jsonl`：训练集，不含现有搜索金标准原句。
- `piancton_six_system_selling_point_intent_v3_compact_validation_upload.jsonl`：固定验证集，来自现有搜索评测原句。
- `piancton_six_system_selling_point_intent_v3_compact_smoke_eval.jsonl`：训练后人工烟测集，禁止上传参与训练或验证。
- `backend/scripts/build_selling_point_intent_sft_v3.py`：可重复生成并校验以上文件。

## 关键变化

- 在每条 system prompt 中明确列出 16 个允许的 code 和最小边界。
- 输出只有三个固定字段，减少长解释对标签学习信号的稀释。
- 增加专家姓名/专家图片入口、拍题精学 + 举一反三、万能解法边界、多卖点、显式否定、纯画面和无可靠卖点硬样本。
- 训练集和固定验证集按查询原句严格隔离；烟测集同时与二者隔离。
- 训练产出仍必须经过应用侧 JSON Schema 和 16-code 白名单校验，精调模型不能成为业务事实源。

## 推荐训练参数

- 基础模型：保持 `Doubao-Seed-2.0-lite 260428`，便于和 v2 对照。
- 方法：SFT + LoRA。
- Epoch：4。
- Batch size：8 或 16，优先 8，以增加有效优化步数。
- Learning rate：`1e-5` 起步。
- `freeze_vit`：`true`，本任务是纯文本分类。
- 验证集：使用本目录固定 validation 文件，不使用训练集随机切分。

## 验收

- 输出 JSON 合法率 100%。
- 非法或自造 code 为 0。
- 单卖点 code 完全匹配率不低于 95%。
- 多卖点集合完全匹配率不低于 90%，重点检查 `photo_guided_learning + transfer_practice`。
- 纯画面和无可靠卖点拒识准确率不低于 95%。
- 烟测集 20 条全部通过后，才允许进入项目灰度接入。
