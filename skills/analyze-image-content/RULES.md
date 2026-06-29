# 图片内容识别 Skill

用途：让视觉模型输出稳定、可校验的图片语义数据。

## 输出协议

Required output:

```json
{
  "image_type": "function | scene_emotion | scene_functional",
  "image_summary": "一段简洁、客观的中文总结，覆盖主体、界面/功能、业务卖点和排除边界",
  "semantic_profile": {
    "visual_facts": ["图中真实可见的主体、界面、文字、动作或场景事实"],
    "business_intent": "最核心的业务语义归属，例如 同步自学体系 > AI拍题精学",
    "search_phrases": ["适合召回这张图的业务话术、痛点表达、功能短语"],
    "exclusion_boundaries": ["不应该用来召回这张图的相邻概念或误判边界"]
  },
  "content_tags": [
    {
      "tag": "简洁中文标签",
      "confidence": 0.0,
      "dimension": "人物|场景|物体|动作|情绪|文字|视觉风格|颜色|产品功能|业务卖点|其他"
    }
  ],
  "secondary_labels": [
    {
      "label_code": "closed_catalog_code",
      "system": "封闭目录中的一级体系",
      "label": "封闭目录中的二级标签",
      "confidence": 0.0,
      "evidence_level": "A | B | C",
      "role": "primary | secondary",
      "reason": "说明为什么适合该标签，以及为什么不是相邻易混标签"
    }
  ],
  "recommended_search_words": ["短词", "功能词", "家长/用户真实痛点短语"],
  "negative_tags": ["容易误判但本图不支持的相邻概念"]
}
```

Rules:

- Content tags describe observable content and may be open vocabulary.
- Return 18 to 22 unique content tags, approximately 20 in total.
- Cover multiple useful dimensions instead of repeating near-synonyms.
- All summaries, content tags, recommended words, and reasons must use Chinese.
- `image_summary` must be searchable, not decorative. It must clearly mention:
  - visual subject, such as child, parent, teacher, learning page, report page, or question page;
  - interface/function, such as拍题、分步讲解、错题本、学情报告、AI答疑、课程规划;
  - business selling point, such as不只给答案、讲清思路、同步校内、减少家长辅导压力;
  - exclusion boundary, such as不是纯答案页、不是普通题库、未出现真人老师、未体现规划服务.
- `semantic_profile` is the structured retrieval asset for this image:
  - `visual_facts`: return 3 to 6 factual Chinese phrases based only on visible evidence.
  - `business_intent`: return the strongest closed-catalog system and label when evidence supports one; otherwise return a concise uncertainty statement.
  - `search_phrases`: return 5 to 10 Chinese phrases that business users may search for, including at least two pain-point or scenario phrases.
  - `exclusion_boundaries`: return 2 to 6 adjacent concepts that should be down-ranked or excluded for this image.
  - Do not put decorative copywriting here. Every item should help retrieval, filtering, or designer review.
- `recommended_search_words` should help later retrieval and contain 5 to 10 unique Chinese phrases:
  - include short words, such as拍题、错题、报告;
  - include functional words, such as分步讲解、错因分析、学习规划;
  - include at least one real parent/user pain-point phrase, such as孩子拍题只抄答案考试不会、家长不知道孩子学没学.
- `negative_tags` must record likely false-positive adjacent concepts that should not be used to recall this image, such as普通答案页、真人督学、纯题库、课程购买页.
- Secondary labels are filled according to the separate closed catalog.
- `secondary_labels.reason` must be useful for designer review: explain positive evidence and explicitly say why similar labels do not apply.
