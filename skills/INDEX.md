# 项目 Skills 索引

这里的 Skill 是项目内部的独立能力，不是插件，也不需要安装。

每个目录只保留一份 `RULES.md`。规则复杂时可以在同目录增加数据文件，
真正执行逻辑放在 Python 对应模块中。

| Skill | 职责 | 是否给模型读取 |
|---|---|---|
| maintain-piancton-architecture | 项目分层与依赖边界 | 否 |
| manage-image-library | 图片 CRUD 与业务流程 | 否 |
| manage-local-image-storage | 本地文件安全和存储替换边界 | 否 |
| manage-tag-taxonomy | 标签树和三类标签概念 | 可选 |
| analyze-image-content | 图片可见内容结构化识别 | 是 |
| classify-secondary-selling-points | 16 个图片二级卖点标签判断 | 是 |
| understand-image-search-intent | 搜索意图、扩词和大类关系 | 是 |
| score-image-search-results | 确定性搜索评分 | 否，由 Python 执行 |
| match-copy-selling-points | 六大体系、30 个文案卖点匹配 | 是 |
| recall-selling-point-images | 三层图片召回 | 否，由 Python 执行 |
| integrate-model-provider | 模型接口替换约定 | 否 |
| orchestrate-ai-tagging | AI 打标整体编排 | 否，由 Python 执行 |

原则：模型负责理解和结构化判断，Python 负责验证、评分、召回、存储和流程控制。
