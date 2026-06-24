# 卖点图片召回 Skill

用途：根据已识别的文案卖点，分三层召回候选图片。

## 分层召回

- Layer 1, base weight 1.0: matched selling-point keywords and model-expanded
  keywords.
- Layer 2, base weight 0.7: sibling points in each matched system.
- Layer 3, base weight 0.5: every point in each matched system.

Search title and content-tag text. Exclude IDs already recalled by a stronger
layer. The original default candidate limit was 60 and each keyword query was
capped to protect the database.
