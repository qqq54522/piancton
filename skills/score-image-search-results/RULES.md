# 搜索结果评分 Skill

用途：用确定性公式对召回图片排序并输出 S/A/B/C 匹配级别。

## 从原项目恢复的评分公式

Components:

- Manual tag hierarchy exact/contains match: 150.
- Content tag exact match: 100.
- Expanded content tag: relation points exact 100, strong 75, medium 50,
  weak 25; multiply by query weight and image confidence; cap 120.
- Direct secondary category: `60 * query_weight * image_confidence`; cap 100.
- Related/fallback category: apply 0.7/0.35 multiplier; cap 60.
- Summary keyword overlap: 1 hit 10, 2 hits 25, 3+ hits 40.
- Optional vector distance: `<0.2` 30, `<0.35` 15, `<0.45` 5.
- Each excluded concept hit: subtract 80.

Final score is the rounded sum minus penalties.

Levels:

- S: hierarchy or exact tag hit, or strong semantic tag plus category hit.
- A: semantic tag >=50 or direct category >=40.
- B: any direct category or related category >=30.
- C: remaining positive matches.
