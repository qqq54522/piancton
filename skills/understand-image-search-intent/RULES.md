# 搜索意图理解 Skill

用途：把自然语言搜索词转成标准查询、扩展检索词、业务概念和排除概念。

## 输出协议

```json
{
  "original_query": "string",
  "normalized_query": "string",
  "search_intent": "string",
  "query_type": "string",
  "expanded_terms": [
    {"term": "string", "relation": "exact|strong|medium|weak", "reason": "string", "weight": 0.7}
  ],
  "matched_business_concepts": [
    {"concept": "string", "relation": "direct|related|fallback", "reason": "string", "weight": 0.7}
  ],
  "excluded_concepts": [],
  "search_strategy": "string"
}
```

Use dynamic relation judgments across the complete business concept catalog.
Do not restore the obsolete fixed label-tree mapping.

Recommended relation multipliers for later scoring:

- direct: 1.0
- related: 0.7
- fallback: 0.35
