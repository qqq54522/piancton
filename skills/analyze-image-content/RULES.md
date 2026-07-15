# 图片内容识别 Skill

用途：让视觉模型输出稳定、可校验的图片语义数据。

## 输出协议

Required output:

```json
{
  "image_summary": "一段简洁、客观的中文画面总结，只描述可见内容",
  "semantic_profile": {
    "schema_version": 2,
    "visual_facts": ["图中真实可见的主体、界面、文字、动作或场景事实"],
    "ocr_text": ["逐条记录图片中真实可见的文字，无文字时为空数组"],
    "subjects": ["人物、设备、界面主体"],
    "scenes": ["真实场景"],
    "actions": ["真实动作或界面操作"],
    "visual_style": ["构图、颜色和视觉风格"],
    "visible_product_features": ["画面中可以直接看见的产品功能"],
    "asset_search_phrases": ["仅对这张素材成立的画面或使用场景搜索表达"],
    "negative_visual_concepts": ["仅基于画面证据可以排除的相邻视觉概念"]
  },
  "content_tags": [
    {
      "tag": "简洁中文标签",
      "confidence": 0.0,
      "dimension": "人物|场景|物体|动作|情绪|文字|视觉风格|颜色|产品功能|业务卖点|其他"
    }
  ],
  "concept_suggestions": [
    {
      "concept_code": "closed_catalog_code",
      "system_name": "六大体系中的相关体系",
      "concept_name": "封闭业务概念目录中的概念",
      "confidence": 0.0,
      "evidence_level": "A | B | C",
      "relation_role": "expresses | supports",
      "reason": "说明为什么适合该业务概念，以及为什么不是相邻易混概念"
    }
  ],
  "recommended_search_words": ["短词", "功能词", "家长/用户真实痛点短语"]
}
```

Rules:

- Content tags describe observable content and may be open vocabulary.
- Content tag 数量由图片实际信息决定，不为凑数量制造近义词。
- 至少覆盖两个客观语义维度；宁可少而准确，也不要堆叠低价值词。
- All summaries, content tags, recommended words, and reasons must use Chinese.
- `image_summary` must be searchable, not decorative. It may mention only visible evidence:
  - visual subject, such as child, parent, teacher, learning page, report page, or question page;
  - interface/function, such as拍题、分步讲解、错题本、学情报告、AI答疑、课程规划;
  - visible text, layout, product controls and scene evidence;
  - do not add inferred selling points, business ownership or marketing conclusions.
- `semantic_profile` is the structured retrieval asset for this image:
  - `visual_facts`: return 3 to 6 factual Chinese phrases based only on visible evidence.
  - `ocr_text`: preserve visible wording separately from visual facts; never invent hidden text.
  - `subjects/scenes/actions/visual_style/visible_product_features`: return only dimensions actually present.
  - `asset_search_phrases`: only image-specific visual, channel, layout or usage expressions; reusable business language belongs to the concept layer.
  - `negative_visual_concepts`: only visual exclusions supported by the image.
  - Do not put decorative copywriting here. Every item should help retrieval, filtering, or designer review.
- `recommended_search_words` is an AI suggestion queue for asset-specific phrases and may be empty; return no more than 12 unique Chinese phrases:
  - include short words, such as拍题、错题、报告;
  - include functional words, such as分步讲解、错因分析、学习规划;
  - include at least one real parent/user pain-point phrase, such as孩子拍题只抄答案考试不会、家长不知道孩子学没学.
- Concept suggestions are filled according to the separate closed business concept catalog.
- Concept suggestions are reviewable relationship suggestions and are stored separately from the objective semantic profile.
- `concept_suggestions.reason` must explain positive evidence and explicitly say why similar concepts do not apply.
