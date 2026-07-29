# 第三层：已命中卖点内证明点判断

用途：只在第二层已确认的卖点范围内判断用户是否明确提出了某个直属证明点。此层不得新增、删除或改写卖点，也不负责选择图片。

## 判断纪律

1. 只有查询明确提出功能流程、方法、案例、数据、证书或具体效果证据时，才返回证明点。
2. 泛搜体系、泛搜卖点或只有宽泛结果时，`matched_proof_points` 返回空数组。
3. 只能返回输入中列出的 `pp_` code，且父卖点必须属于第二层已命中卖点。
4. `evidence_terms` 必须从对应证明点已有“搜索语言”中原样选择 1～3 条最贴近查询的线索。
5. 证据表达点只是证明点下的可选精细线索。只有查询明确对应目录文字时才返回 `ep_` code，并且其父证明点必须同时命中。
6. 不得返回卖点，不得自造 code，不得根据库存情况改变业务判断。

## 输出协议

```json
{
  "original_query": "string",
  "matched_proof_points": [
    {
      "code": "pp_existing_code",
      "concept_code": "parent_selling_point_code",
      "name": "string",
      "reason": "原话中支持该证明点的具体细节",
      "weight": 0.0,
      "evidence_terms": ["证明点目录中的现有搜索语言"]
    }
  ],
  "matched_evidence_points": [
    {
      "code": "ep_existing_code",
      "proof_point_code": "pp_existing_code",
      "concept_code": "parent_selling_point_code",
      "name": "string",
      "reason": "原话中支持该证据表达点的具体细节",
      "weight": 0.0
    }
  ],
  "search_strategy": "string"
}
```
