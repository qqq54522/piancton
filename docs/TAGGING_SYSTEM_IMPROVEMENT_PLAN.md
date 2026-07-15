# 标签系统完善与 AI 打标改造方案

> **历史文档说明**：本文记录固定标签体系时期的改造方案，已被“六大体系 + 版本化业务概念 + 素材组多对多关系 + Semantic Profile V2”替代。本文仅供历史追溯，不得用于恢复标签树或旧 AI 二级标签职责；当前方案以 `IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为准。

版本：2026-06-28  
依据：

- `docs/OPTIMIZATION_PLAN.md`
- `docs/SEARCH_BUSINESS_INTENT_MAP.md`
- `taxonomy/catalog.json`
- 2026-06-28 搜索手工测试反馈

目标：让图片上传后的人工标签、AI 业务标签、语义总结、隐性内容标签和搜索意图理解形成闭环。核心不是“标签越多越好”，而是让系统能稳定理解业务话术，并把它归一到正确的业务卖点。

---

## 1. 当前问题判断

现有标签系统已经有正确基础：

- 六大体系和二级标签已经存在。
- `taxonomy/catalog.json` 已经有 `aliases`、`positive_evidence`、`negative_evidence`。
- AI 分析已经能输出 `image_summary`、`content_tags`、`secondary_labels`、`recommended_search_words`、`negative_tags`。
- AI 建议标签已经有 `origin`、`review_status`、`confidence`、`reason` 的治理方向。

但现在暴露出来的关键问题是：

```text
业务原文档里的长话术 / 家长痛点
  没有稳定转成
核心业务标签 / 二级卖点
```

典型表现：

- `错题本` 能搜到，但“整理错题费功夫、容易忘”不能稳定归到 `AI错题本`。
- `拍题` 能搜到，但“孩子拍题只抄答案，考试不会”不能稳定归到 `AI拍题精学`。
- `专家规划` 能搜到，但“出卷人、编教材的人设计课程”仍被泛学习兜底污染。

所以它不是单纯的“图片没打标签”，而是这几个层次没有打通：

```text
业务话术词库
  ↓
意图簇映射
  ↓
AI 图片语义总结
  ↓
封闭业务标签
  ↓
搜索排序和结果收紧
```

---

## 2. 标签系统应该分四层

后续不要把所有词都混成“标签”。建议分成四层治理。

### 2.1 第一层：六大体系

用途：稳定业务坐标系，不频繁变化。

当前保留：

- 同步校内体系
- 同步考点体系
- 同步培养体系
- 同步规划体系
- 同步自学体系
- 同步伴学体系

规则：

- 六大体系只做大方向归属。
- 不承载大量具体话术。
- 不因为一次搜索不准就新增体系。

### 2.2 第二层：二级业务标签

用途：图片最核心的业务卖点归属。

例如：

- `AI错题本`
- `AI拍题精学`
- `专家规划`
- `真人老师督学`
- `学情报告反馈`
- `AI定制学习方案`

规则：

- 二级标签必须是“可归档、可审核、可解释”的业务卖点。
- AI 只能建议 catalog 中已有的二级标签，不能新造。
- 人工主标签优先，AI 建议默认 pending。

### 2.3 第三层：业务话术 / 意图簇

用途：把原文档里的灰色长文案、家长痛点、营销表达映射到二级标签。

例如：

```text
整理错题费功夫、容易忘
  -> AI错题本

拍题只抄答案，考试不会
  -> AI拍题精学

出卷人、编教材的人设计课程
  -> 专家规划
```

规则：

- 这些不一定都要变成数据库标签。
- 它们更适合放在意图簇词库中，用于 AI 搜索理解和搜索扩展。
- 不要把长句全部塞进 `aliases`，否则 catalog 会膨胀且难维护。

### 2.4 第四层：隐性内容标签与语义总结

用途：描述图片画面和概念，帮助搜索理解“这张图到底表达什么”。

包括：

- `image_summary`
- `content_tags`
- `recommended_search_words`
- `negative_tags`
- AI 业务标签理由

规则：

- `image_summary` 必须描述画面主体、界面功能、业务卖点和排除边界。
- `content_tags` 描述可见内容和抽象业务信号。
- `negative_tags` 记录“看起来可能像，但实际不是”的概念，后续用于降权。

---

## 3. catalog 应该怎么改

### 3.1 短期：不改结构，先补强现有字段

当前 `taxonomy/catalog.json` 已支持：

```json
{
  "aliases": [],
  "positive_evidence": [],
  "negative_evidence": []
}
```

短期可以这样使用：

- `aliases`：放短词、同义词、常见叫法。
- `positive_evidence`：放能够判断该标签成立的画面证据和短痛点。
- `negative_evidence`：放容易误判但应该排除的边界。

示例：

```json
{
  "code": "photo_guided_learning",
  "name": "AI拍题精学",
  "aliases": [
    "拍题精学",
    "拍题讲解",
    "拍题分步讲解",
    "不直接给答案"
  ],
  "positive_evidence": [
    "拍题后分步讲解",
    "引导解题思路",
    "不是抄答案",
    "孩子拍题后真正理解",
    "苏格拉底式提问"
  ],
  "negative_evidence": [
    "只给最终答案",
    "只有普通 AI 聊天",
    "没有拍题或题目识别"
  ]
}
```

### 3.2 中期：新增搜索意图字段

等短期验证稳定后，可以给 catalog 增加专门的搜索意图字段，避免把所有内容塞进 `aliases`。

建议字段：

```json
{
  "intent_phrases": [],
  "pain_points": [],
  "must_have_concepts": [],
  "nice_to_have_concepts": [],
  "exclude_concepts": [],
  "search_policy": "strict_when_primary_intent"
}
```

含义：

- `intent_phrases`：业务原文档中的卖点表达。
- `pain_points`：家长痛点、模糊话术。
- `must_have_concepts`：图片摘要中最好必须出现的概念。
- `nice_to_have_concepts`：加分概念。
- `exclude_concepts`：排除或降权概念。
- `search_policy`：当该意图被识别为主意图时，搜索是否允许少结果。

### 3.3 长期：把意图簇独立成配置

如果话术越来越多，不建议无限扩展 `taxonomy/catalog.json`。

可以新增：

```text
taxonomy/business_intents.json
```

结构示例：

```json
{
  "code": "intent_ai_error_book_pain_points",
  "target_label_code": "ai_error_book",
  "target_system_code": "sync_self_study",
  "phrases": [],
  "pain_points": [],
  "summary_signals": [],
  "negative_signals": [],
  "eval_queries": []
}
```

这样 catalog 负责“稳定标签”，business intents 负责“话术理解”。

---

## 4. AI 打标应该怎么改

### 4.1 图片分析要输出两类信息

AI 图片分析不应该只输出“像什么”，还要输出“适合被什么业务话术搜到”。

当前已有：

```json
{
  "image_summary": "",
  "content_tags": [],
  "secondary_labels": [],
  "recommended_search_words": [],
  "negative_tags": []
}
```

建议强化为：

```text
image_summary：
  一句话说明图片画面 + 功能 + 业务卖点。

content_tags：
  覆盖人物、场景、物体、动作、情绪、文字、产品功能、业务卖点。

secondary_labels：
  只能返回 catalog 中的二级标签 code。

recommended_search_words：
  不只写短词，也要包含 5-10 个真实业务搜索短句。

negative_tags：
  记录容易误判但图片不支持的概念。
```

### 4.2 image_summary 要更“业务化”

现在搜索问题说明：语义总结必须能帮助模糊搜索，而不只是客观描述画面。

不够好的 summary：

```text
一张手机展示学习页面的图片。
```

更好的 summary：

```text
画面展示学生用手机拍摄题目后，系统给出分步讲解和解题思路，强调拍题不是直接给答案，而是引导孩子理解题型。
```

原因：

- 能匹配“孩子拍题只抄答案怎么办”。
- 能匹配“拍题后讲思路”。
- 能排除“只给答案”的搜题工具。

### 4.3 AI 二级标签建议必须带证据

每个 `secondary_label` 的 reason 应该说明：

- 画面证据：图片里看到了什么。
- 业务证据：为什么归到这个二级标签。
- 边界判断：为什么不是另一个相近标签。

示例：

```json
{
  "label_code": "photo_guided_learning",
  "system": "同步自学体系",
  "label": "AI拍题精学",
  "confidence": 0.92,
  "evidence_level": "A",
  "role": "primary",
  "reason": "画面包含手机拍题、题目识别和分步讲解界面，重点表达拍题后引导理解，而不是直接展示最终答案。"
}
```

### 4.4 recommended_search_words 要像真实用户会搜的话

现在它应该成为搜索增强资产。

每张图建议包含三类：

- 标签词：`AI错题本`、`拍题精学`
- 功能词：`上传错题`、`分步讲解`
- 痛点句：`孩子拍题只抄答案怎么办`、`整理错题太麻烦`

---

## 5. 搜索意图理解应该怎么改

### 5.1 搜索理解要输出“主意图”

现有 `SearchUnderstanding` 已有：

```json
{
  "normalized_query": "",
  "search_intent": "",
  "expanded_level1_tags": [],
  "matched_level2_categories": [],
  "exclude_tags": [],
  "search_strategy": ""
}
```

建议下一步增加或在 `search_strategy` 中明确表达：

```json
{
  "primary_label_code": "ai_error_book",
  "primary_intent_confidence": 0.9,
  "result_policy": "strict_allow_few_results",
  "must_have_concepts": ["错题上传", "错因分析"],
  "exclude_concepts": ["普通课程", "只给答案"]
}
```

### 5.2 strong intent 要收紧结果

当系统判断 query 的主意图很明确时：

- 不强行补满 15 张。
- 不把 C 级兜底放入主结果。
- 优先返回命中主标签 + summary 概念一致的图片。
- 如果只有 1 张强相关，就告诉用户“找到 1 张精准结果”。

### 5.3 搜索匹配要区分四种命中

后续前端/后端最好展示匹配原因：

```text
命中主标签：同步自学体系 > AI错题本
命中业务话术：整理错题麻烦、容易遗忘
命中语义总结：错题上传、错因分析、同类题复习
排除泛召回：普通课程、新课标、专项培优
```

这能让用户知道系统是不是“真懂了”。

---

## 6. 人工审核与 AI 建议规则

### 6.1 不让 AI 覆盖人工标签

继续遵守优化文档规则：

- 人工主标签永远优先。
- AI 建议默认 `pending`。
- 人工接受后，AI 建议可成为附加标签。
- 人工拒绝后，重新分析不应反复推同一个建议。

### 6.2 需要补一个“AI 建议为什么来”的展示

前端展示 AI 建议时，建议包含：

```text
建议标签：同步自学体系 > AI错题本
置信度：92%
证据等级：A
原因：画面包含错题上传、错因分析和同类题推荐界面。
可被这些话术搜到：整理错题麻烦、错题容易忘、换题型还错。
排除：不是普通单题讲解。
```

这样设计师审核时能判断 AI 有没有理解对。

---

## 7. 评测与验收

标签系统完善后，不只测“有没有标签”，还要测“标签能不能支撑搜索”。

### 7.1 第一批评测意图簇

优先用已经暴露问题的 3 个：

- `AI错题本`
- `AI拍题精学`
- `专家规划`

每个意图簇准备 5 条 query：

- 1 条精准词
- 1 条功能描述
- 2 条家长痛点
- 1 条业务长文案

### 7.2 验收标准

每个意图簇至少满足：

- 精准词能命中正确图片。
- 功能描述能归一到正确二级标签。
- 家长痛点能归一到正确二级标签。
- 长文案能归一到正确二级标签。
- Top 3 不被泛学习素材污染。
- 强相关图片不足时允许少结果。
- 匹配原因能说明命中了标签、话术还是语义总结。

### 7.3 判断问题来源

后续排查可以按这个顺序判断：

```text
明确搜标签名都搜不到
  -> 优先查图片打标 / 索引同步

明确搜标签名能搜到，业务话术搜不到
  -> 优先查业务话术词库 / 搜索意图理解

识别到了标签，但结果仍然很散
  -> 优先查排序 / 兜底策略 / 结果截断

图片被错误打上相近标签
  -> 优先查 AI 图片分析 prompt / negative_tags / normalizer 校验
```

---

## 8. 推荐实施顺序

### 第一步：冻结结构，不急着新增二级标签

当前二级标签基本够用。短期不要因为搜索不准就新增很多二级标签。

先解决：

- 业务话术到现有标签的归一。
- AI summary 的业务化。
- 搜索强意图下的结果收紧。

### 第二步：把 `SEARCH_BUSINESS_INTENT_MAP.md` 转成可用词库

短期可以人工把高频内容补进：

- `aliases`
- `positive_evidence`
- `negative_evidence`
- AI prompt 规则

中期再拆成：

```text
taxonomy/business_intents.json
```

### 第三步：升级 AI 图片分析 prompt

重点要求模型输出：

- 更业务化的 `image_summary`
- 更真实的 `recommended_search_words`
- 更明确的 `negative_tags`
- 带边界判断的 `secondary_labels.reason`

### 第四步：升级搜索意图理解 prompt

让模型优先返回：

- 主意图标签 code
- must-have concepts
- exclude concepts
- result policy

### 第五步：调整搜索排序和兜底策略

当主意图明确时：

- 主标签 + summary 概念一致的结果优先。
- C 级兜底不进入主结果。
- 强相关不足时不强行补满。

### 第六步：建立搜索评测集

先用 15 条：

- AI错题本 5 条
- AI拍题精学 5 条
- 专家规划 5 条

稳定后扩到 30 条，再扩到 50 条。

---

## 9. 本轮结论

标签系统完善的方向不是“多建标签”，而是：

```text
稳定二级标签
  +
丰富业务话术意图簇
  +
强化图片语义总结
  +
让搜索按主意图收紧结果
```

AI 打标系统最终要做到：

- 看图能知道它属于哪个业务卖点。
- 能说明为什么属于这个卖点。
- 能知道哪些相近卖点不应该归。
- 能生成真实用户会搜的话术。
- 能支撑自然语言搜索，而不是只支撑标签名搜索。
