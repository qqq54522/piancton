# 搜索意图理解 Skill

用途：把自然语言搜索词转成标准查询、扩展标签、相关大类和排除项。

## 输出协议

```json
{
  "original_query": "string",
  "normalized_query": "string",
  "search_intent": "string",
  "query_type": "string",
  "expanded_level1_tags": [
    {"tag": "string", "relation": "exact|strong|medium|weak", "reason": "string", "weight": 0.7}
  ],
  "matched_level2_categories": [
    {"category": "string", "relation": "direct|related|fallback", "reason": "string", "weight": 0.7}
  ],
  "exclude_tags": [],
  "search_strategy": "string"
}
```

Use dynamic relation judgments across the complete category catalog. Do not
restore the obsolete fixed mapping that covered only 11 categories.

Recommended relation multipliers for later scoring:

- direct: 1.0
- related: 0.7
- fallback: 0.35
