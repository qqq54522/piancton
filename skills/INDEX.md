# 项目 Skills 索引

这里的 Skill 是卖点智库的项目内正式能力包，不是外部插件，也不需要单独安装。每个正式 Skill 都包含标准 `SKILL.md` 和 `agents/openai.yaml`；需要被应用运行时模型读取的能力同时提供精简 `RULES.md`。

## 正式 Skills

| Skill | 触发场景 | 运行时 AI |
|---|---|---|
| `understand-image-search-intent` | 维护体系、卖点和边界知识；为火山知识索引提供来源 | 当前自由搜索不直接调用旧模型链路 |
| `manage-image-library` | 上传、素材组版本、人工关系、下载和回收 | 主要由确定性服务执行 |
| `govern-selling-point-knowledge` | 维护六体系、16卖点和业务边界 | AI 可辅助，人工决定 |
| `evaluate-image-search-quality` | 本地/三模型准确性、越界和延迟评测 | 可选；外发前必须授权 |
| `maintain-piancton-architecture` | 新功能、修复、重构和代码审查 | 开发阶段使用 |
| `understand-image-channel-intent` | 用户搜索或上传时识别 PPT、品牌手册、手机端、官网及大图/小图语境 | 暂不默认调用；先由确定性规则和前端测试验证 |

## 应用运行时 AI Search 映射

| AI Search 能力 | Runtime service | 触发入口 |
|---|---|---|
| 搜索 | `VolcAiSearchService` | 素材检索；本地仅保留不外发数据的确定性降级 |
| `chat_search` | `AssetAgentService` | 右侧 Piancton Agent 自由问答；涉及洋葱业务时参考知识数据集与本地稳定目录，也可问图片和自然语言找图 |
| 推荐 | `HomeRecommendationService` / AI Search 推荐接口 | 首页猜你喜欢与详情页相关推荐 |
| 补全、摘要、行为 | `VolcAiSearchClient` 对应能力 | 搜索交互和推荐效果闭环 |

渠道意图识别当前作为卖点意图的并行 Skill：先沉淀 schema、渠道分类和推荐解释规则，再由前端确定性解析器做搜索结果后二次收窄与解释；暂不进入 `MODEL_SKILLS`，避免在真实渠道标注不足时影响卖点主通道和在线模型耗时。

API 中心和本地通用 `ModelProvider` 调度已全部退役。`search_result_recommendation_reason`、`asset_agent_chat`、`search_system_routing`、`search_intent_understanding`、`search_proof_point_understanding`、`search_candidate_review`、`image_content_analysis`、`copy_selling_point_matching` 和 `asset_search_phrase_generation` 都不得进入当前运行时；需要语义能力时使用 Viking AI Search 应用已配置的能力。

模型输出必须经过 normalizer、Pydantic schema、运行时目录和审核状态校验。模型任务返回成功不等于业务判断正确。

## 不再作为 Skill 的底层职责

- 本地图片字节和路径安全由 `StorageProvider` 执行，合并在 `manage-image-library` 的工作流边界中。
- 图片分析队列、事务和索引刷新由 Python Service 编排，合并在 `analyze-image-asset` 的工作流边界中。
- 查询召回、第三层图片准入、确定性评分、素材组去重和响应拼装由现有 Python 搜索服务执行，不包装成生成式 AI Skill。
- 固定二级标签、图片 `content_tags`、旧三层弱召回和旧 S/A/B/C 公式已经下线，不保留对应 Skill。

原则：模型负责需要语义理解的结构化判断；Python 负责校验、审核状态、召回、筛选、评分、存储、事务和降级。
