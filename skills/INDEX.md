# 项目 Skills 索引

这里的 Skill 是卖点智库的项目内正式能力包，不是外部插件，也不需要单独安装。每个正式 Skill 都包含标准 `SKILL.md` 和 `agents/openai.yaml`；需要被应用运行时模型读取的能力同时提供精简 `RULES.md`。

## 正式 Skills

| Skill | 触发场景 | 运行时 AI |
|---|---|---|
| `understand-image-search-intent` | 用户搜索、体系/卖点判断、第三层图片边界 | 本地强证据不足或真实歧义时调用 |
| `analyze-image-asset` | 主图上传、替换主图、重新分析 | 是；尺寸延展图跳过 |
| `generate-asset-search-phrases` | 用户点击上传前 AI 话术生成 | 是；结果不自动持久化 |
| `match-copy-selling-points` | 兼容的活动/课程文案运营点匹配接口 | 是；不替代图片搜索意图 |
| `manage-image-library` | 上传、素材组版本、人工关系、下载和回收 | 主要由确定性服务执行 |
| `govern-selling-point-knowledge` | 维护六体系、16卖点、公共话术和业务边界 | AI 可辅助，人工决定 |
| `evaluate-image-search-quality` | 本地/三模型准确性、越界和延迟评测 | 可选；外发前必须授权 |
| `operate-model-providers` | Provider 接入、降级顺序、超时和遥测 | 管理模型基础设施 |
| `maintain-piancton-architecture` | 新功能、修复、重构和代码审查 | 开发阶段使用 |

## 应用运行时模型映射

| Model task | Runtime rules | 触发入口 |
|---|---|---|
| `image_content_analysis` | `analyze-image-asset/RULES.md` | 正式主图自动分析或重新分析 |
| `asset_search_phrase_generation` | `generate-asset-search-phrases/RULES.md` | 上传前主动点击生成 |
| `search_system_routing` + `search_intent_understanding` | `understand-image-search-intent/` 分层规则与按需体系知识 | 搜索本地证据不足或歧义 |
| `copy_selling_point_matching` | `match-copy-selling-points/RULES.md` | 兼容文案卖点匹配接口 |

模型输出必须经过 normalizer、Pydantic schema、运行时目录和审核状态校验。模型任务返回成功不等于业务判断正确。

## 不再作为 Skill 的底层职责

- 本地图片字节和路径安全由 `StorageProvider` 执行，合并在 `manage-image-library` 的工作流边界中。
- 图片分析队列、事务和索引刷新由 Python Service 编排，合并在 `analyze-image-asset` 的工作流边界中。
- 查询召回、第三层图片准入、确定性评分、素材组去重和响应拼装由现有 Python 搜索服务执行，不包装成生成式 AI Skill。
- 固定二级标签、图片 `content_tags`、旧三层弱召回和旧 S/A/B/C 公式已经下线，不保留对应 Skill。

原则：模型负责需要语义理解的结构化判断；Python 负责校验、审核状态、召回、筛选、评分、存储、事务和降级。
