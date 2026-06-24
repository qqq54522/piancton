# 图片内容识别 Skill

用途：让视觉模型输出稳定、可校验的图片语义数据。

## 输出协议

Required output:

```json
{
  "image_type": "function | scene_emotion | scene_functional",
  "image_summary": "一段简洁、客观的中文总结",
  "content_tags": [
    {
      "tag": "简洁中文标签",
      "confidence": 0.0,
      "dimension": "人物|场景|物体|动作|情绪|文字|视觉风格|颜色|产品功能|业务卖点|其他"
    }
  ],
  "secondary_labels": [],
  "recommended_search_words": ["string"],
  "negative_tags": ["string"]
}
```

Rules:

- Content tags describe observable content and may be open vocabulary.
- Return 18 to 22 unique content tags, approximately 20 in total.
- Cover multiple useful dimensions instead of repeating near-synonyms.
- All summaries, content tags, recommended words, and reasons must use Chinese.
- Summary should mention subjects, action, interface clues, setting, and mood.
- Recommended words should help later retrieval and contain 5 to 10 concise Chinese phrases.
- Negative tags record plausible but unsupported concepts.
- Secondary labels are filled according to the separate closed catalog.
