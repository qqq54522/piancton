# 第二层：候选体系内卖点判断

用途：只在第一层已确认的候选体系内判断核心卖点。此层不得判断证明点、证据表达点或图片。

## 判断纪律

1. 先依据用户操作的对象与主动作判断卖点，再用目的、结果、时间尺度和执行主体校准。
2. 只返回输入中提供的当前启用卖点稳定 code，不得跨出候选体系，不得自造卖点。
3. 每个卖点必须有独立原话证据；共享入口词产生探索或待消歧候选，不得伪装成真多卖点。
4. 产品功能细节、教研方法、案例、数据、证书和效果材料属于第三层证明点，本层不得提前判断。
5. 显式否定的卖点写入 `excluded_concepts`，不得同时作为正向卖点。

## 输出协议

返回 `SearchUnderstanding` 结构，但必须遵守：

- `matched_business_concepts` 只包含本层确认的卖点。
- `matched_proof_points` 必须是空数组。
- `matched_evidence_points` 必须是空数组。
- `expanded_terms` 只用于归一化卖点语义，不得写证明点或图片选择词。
- `search_strategy` 只说明卖点层判断，不得声称已经选中证明点或图片。

查询状态只允许项目封闭枚举：

- `business_intent_search`
- `multi_business_intent_search`
- `exploratory_business_intent_search`
- `ambiguous_business_intent_search`
- `visual_scene_search`
- `no_reliable_intent_search`

