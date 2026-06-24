# 标签体系 Skill

用途：管理手动标签树、内容标签和二级卖点标签之间的边界。

## 标签规则

Three tag concepts must remain separate:

1. Manual hierarchy tags: editable `Tag` rows with parent relationships.
2. Content tags: free structured observations such as person, scene, object,
   emotion, text, style, and color.
3. Secondary selling-point labels: closed education-product label catalog.

Hierarchy invariants:

- a tag cannot parent itself;
- a descendant cannot become an ancestor's parent;
- selecting a parent for filtering may include descendants only when the
  caller explicitly requests subtree behavior;
- display paths use `parent > child`;
- AI suggestions never create arbitrary manual taxonomy nodes automatically.
