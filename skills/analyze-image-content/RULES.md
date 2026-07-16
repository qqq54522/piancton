# 图片内容识别 Skill

用途：让视觉模型输出稳定、可校验的图片语义数据。

## 输出协议

Required output:

```json
{
  "image_summary": "一段简洁、客观的中文画面总结，只描述可见内容",
  "semantic_profile": {
    "schema_version": 3,
    "visual_facts": ["用完整短句总结图中真实可见的关键事实"],
    "scenes": ["用完整短语概括这张素材适用的真实场景"],
    "asset_search_phrases": ["仅对这张素材成立的画面或使用场景搜索表达"]
  },
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
  ]
}
```

Rules:

- 只输出协议中列出的字段，不要输出 OCR、主体、动作、视觉风格、可见功能、排除边界、客观内容标签或推荐搜索词等旧字段。
- All summaries, semantic profile items, and reasons must use Chinese.
- `image_summary` must be searchable, not decorative. It may mention only visible evidence:
  - visual subject, such as child, parent, teacher, learning page, report page, or question page;
  - interface/function, such as拍题、分步讲解、错题本、学情报告、AI答疑、课程规划;
  - visible text, layout, product controls and scene evidence;
  - do not add inferred selling points, business ownership or marketing conclusions.
- `semantic_profile` is the structured retrieval asset for this image:
  - `visual_facts`: return 2 to 6 non-duplicated factual Chinese phrases based only on visible evidence. Combine visible subjects, layout, text and actions into useful facts instead of splitting them into fixed-word tags.
  - `scenes`: return 0 to 4 broad, non-duplicated usage or presentation scenes. Do not invent a scene when the image does not support one.
  - `asset_search_phrases`: return 0 to 8 unique, natural expressions that distinguish this asset's画面、文案、版式或使用场景. Reusable business language belongs to the concept layer.
  - Do not put decorative copywriting or isolated fixed words here. Every item should help retrieval or designer review.
- Concept suggestions are filled according to the separate closed business concept catalog.
- Concept suggestions are reviewable relationship suggestions and are stored separately from the objective semantic profile.
- `concept_suggestions.reason` must explain positive evidence and explicitly say why similar concepts do not apply.
