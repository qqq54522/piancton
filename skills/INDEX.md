# 项目 Skills 索引

这里的 Skill 是卖点智库的项目内正式能力包，不是外部插件，也不需要单独安装。每个正式 Skill 都包含标准 `SKILL.md` 和 `agents/openai.yaml`；需要被应用运行时模型读取的能力同时提供精简 `RULES.md`。

## 正式 Skills

| Skill | 触发场景 | 运行时 AI |
|---|---|---|
| `understand-image-search-intent` | 维护体系、卖点和边界知识；为火山知识索引提供来源 | 当前自由搜索不直接调用旧模型链路 |
| `analyze-image-asset` | 历史图片分析规则资料；当前主流程不再调用 | 否；接口已退役 |
| `match-copy-selling-points` | 历史文案卖点匹配规则资料；当前主流程不再调用 | 否；接口已退役 |
| `manage-image-library` | 上传、素材组版本、人工关系、下载和回收 | 主要由确定性服务执行 |
| `govern-selling-point-knowledge` | 维护六体系、16卖点和业务边界 | AI 可辅助，人工决定 |
| `evaluate-image-search-quality` | 本地/三模型准确性、越界和延迟评测 | 可选；外发前必须授权 |
| `operate-model-providers` | Provider 接入、降级顺序、超时和遥测 | 管理模型基础设施 |
| `maintain-piancton-architecture` | 新功能、修复、重构和代码审查 | 开发阶段使用 |
| `understand-image-channel-intent` | 用户搜索或上传时识别 PPT、品牌手册、手机端、官网及大图/小图语境 | 暂不默认调用；先由确定性规则和前端测试验证 |

## 应用运行时模型映射

| Model task | Runtime rules | 触发入口 |
|---|---|---|
| `search_result_recommendation_reason` | `build_search_route_explanation_prompt()` + 用户原话 + 火山已命中卖点 | 搜索结果顶部：解释为什么这句话命中这些卖点，不参与召回、排序或候选准入 |
| `asset_agent_chat` | `AssetAgentService` 组装图片、素材组、人工 accepted 卖点关系和当前启用卖点简表 | 素材库右下角 Agent，解释图片卖点和家长沟通话术；不写入业务事实 |

渠道意图识别当前作为卖点意图的并行 Skill：先沉淀 schema、渠道分类和推荐解释规则，再由前端确定性解析器做搜索结果后二次收窄与解释；暂不进入 `MODEL_SKILLS`，避免在真实渠道标注不足时影响卖点主通道和在线模型耗时。

当前 API 中心正式自动调度只保留两个模型用途：`search_result_recommendation_reason` 用于搜索级命中卖点解释，`asset_agent_chat` 用于素材库 Agent。`search_system_routing`、`search_intent_understanding`、`search_proof_point_understanding`、`search_candidate_review`、`image_content_analysis`、`copy_selling_point_matching` 和 `asset_search_phrase_generation` 均为历史退役任务，不再进入当前运行时映射。

模型输出必须经过 normalizer、Pydantic schema、运行时目录和审核状态校验。模型任务返回成功不等于业务判断正确。

## 不再作为 Skill 的底层职责

- 本地图片字节和路径安全由 `StorageProvider` 执行，合并在 `manage-image-library` 的工作流边界中。
- 图片分析队列、事务和索引刷新由 Python Service 编排，合并在 `analyze-image-asset` 的工作流边界中。
- 查询召回、第三层图片准入、确定性评分、素材组去重和响应拼装由现有 Python 搜索服务执行，不包装成生成式 AI Skill。
- 固定二级标签、图片 `content_tags`、旧三层弱召回和旧 S/A/B/C 公式已经下线，不保留对应 Skill。

原则：模型负责需要语义理解的结构化判断；Python 负责校验、审核状态、召回、筛选、评分、存储、事务和降级。
