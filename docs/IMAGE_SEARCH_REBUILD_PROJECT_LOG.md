# 图片搜索改造项目日志

更新时间：2026-07-23
当前范围：Phase 0～Phase 6；九个正式 Skill 与四类运行时模型任务完成收口
当前状态：Phase 0～6 工程改造完成；六大体系、16 个核心卖点、三层搜索和人工关系边界保持稳定

> 本文档记录项目实际做过的工作、迁移、验证结果和遗留事项。架构原则、业务决策与后续阶段路线仍以 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为唯一事实来源。后续日志按日期追加，不覆盖历史记录。

---

## 2026-07-23：证明点来源与人工校准关系收口（D118）

### 本轮目标

- 修正人工复核发现的两处语义归属问题，并确保原图绿色路径与业务人工补充判断不会混在一起。

### 完成内容

- `evidence-points.json` 升至 `2026-07-23.4`。
- `ep_cultivation_learning_loop` 从 `pp_cultivation_expert_path_design` 改归 `pp_cultivation_stage_transition_plan`，使“完整教-学-练-评闭环”明确对应“学段衔接”。
- `ep_exam_transfer_logic` 只保留真实原图绿色路径；“AI 拍题讲解后推送相似题可证明举一反三”改为 `reviewNotes` 人工确认关系。
- 业务 facets API 和前端类型只读透传 `reviewNotes`；人工分类组件在默认折叠的来源区域中分开显示“原图推导路径”和“人工确认关系”。
- 普通搜索、模型 Prompt、召回、排序、数据库字段、稳定 code 和现有人工素材关系均未改变；无数据库迁移。

### 验证

- JSON 结构校验通过：58 个证据表达点、59 条真实原图路径、1 条独立人工校准说明；`ep_cultivation_learning_loop` 父证明点已确认为 `pp_cultivation_stage_transition_plan`。
- 后端证据点与业务 facets 接口定向测试 `16 passed`。
- Skill、文档、卖点映射、证明点来源与 taxonomy 对齐测试 `25 passed`。
- 搜索评测和 Phase 0～3 基础链路回归 `11 passed`。
- 前端组件测试 `1 passed`；TypeScript、ESLint、生产构建和 `git diff --check` 通过。
- 本地 `backend/web` 已重新构建，四个长期服务均为 healthy。
- 浏览器实测通过：上传页已显示“卖点 → 证明点 → 证据表达点”；“举一反三 → 变式与同类题迁移训练 → 讲解当前题后推送相似题”展开后，原图路径与“人工确认关系”分开展示；“完整教、学、练、评闭环”只出现在“学段衔接 → 衔接期个性化规划支撑”下。
- `npm run generate:api` 仍固定请求未对宿主机开放的 `127.0.0.1:8000`，本地容器只通过 Web 反向代理提供 API，因此该命令连接失败；本轮已同步维护生成类型中的 `reviewNotes`，并由 TypeScript 与生产构建验证。

### 待继续

- 后续人工复核若发现跨卖点支撑，只补充 `reviewNotes` 或人工素材关系，不再写入原图 `sourcePaths`。

## 2026-07-23：六体系证据表达点来源路径补齐（D117）

### 本轮目标

- 继续按原图补全其他体系，让人工审核时能看到每个绿色证明点从哪个核心卖点和中间证明分支推导出来。

### 完成内容

- `evidence-points.json` 升至 `2026-07-23.3`，六个体系 58 个 `ep_` 绿色证据表达点全部补齐 `sourcePaths`。
- 覆盖数量：同步校内 16 个、同步考点 15 个、同步培养 10 个、同步规划 3 个、同步自学 9 个、同步伴学 5 个。
- 保留不定深度原图链路：`system → selling_point → proof_group... → evidence_expression`；同步考点 `ep_exam_transfer_logic` 保留原图 AI 拍题路径和 2026-07-23 人工校准补充路径。
- 同步更新六体系知识文件与业务目录口径：绿色点是证据表达和人工审查锚点，不自动等于已核验事实、已有素材或新增核心卖点。
- 普通搜索、模型 Prompt、召回、排序、数据库字段、稳定 code 和人工素材关系均未改变。
- D118 后续将人工校准补充路径从 `sourcePaths` 拆为 `reviewNotes`；本节保留当时实施记录。

### 验证

- JSON 结构校验通过；目录统计为 `58` 条，缺失 `sourcePaths` 数量为 `0`。
- `test_evidence_point_runtime.py` 已升级为全量路径护栏：每条路径必须从 `system` 开始、以 `evidence_expression` 结束，并包含 `selling_point`。
- 临时 Docker 后端容器挂载当前源码运行：证据点与业务 facets 接口定向测试 `15 passed`；文档、Skill、卖点和证明点来源对齐测试 `17 passed`。
- `git diff --check` 通过。
- 本地根目录无 `.venv`，系统 Python 缺少 `pytest/ruff`；当前后端 Docker 镜像也未安装 `ruff`，因此本轮 Ruff 未能执行。

### 待继续

- 业务负责人可按上传页/详情页中默认折叠的“查看原图推导路径”逐条核对图片关系；如发现某个绿色点需要支持相邻卖点，继续通过人工素材关系表达，不改原图父子来源。

## 2026-07-23：证据表达点结构化来源路径（D116）

### 本轮目标

- 保留原脑图从体系、核心卖点、多级证明分支到末端绿色点的完整推导关系，同时不增加生产搜索层级。

### 完成内容

- `evidence-points.json` 为同步培养 10 个绿色点增加可变深度、可保存多条的 `sourcePaths`；专家身份绿色点保留两条原图来源路径。
- 后端证据表达点目录增加来源路径节点解析与层级校验，业务 facets API 只读返回 `sourceRef/sourcePaths`。
- 上传页和素材详情复用的人工分类组件新增默认折叠的“查看原图推导路径”，仅在选中带路径的绿色点后出现。
- 普通搜索、模型 Prompt、召回、过滤、排序、数据库结构、稳定 code 和人工素材关系均未改变。
- 后端专项测试 `28 passed`；前端全量 `23 passed`，TypeScript、ESLint、生产构建和 `git diff --check` 通过。
- 后端全量为 `225 passed, 3 failed`；3 条失败均为本轮未修改的 `search_service.py`、`asset_selection_policy_service.py` 既有行数护栏超限，不属于来源路径变更。
- 浏览器确认当前素材库和详情工作台可正常加载；为避免把工作区其他未提交改动一并部署，本轮未重启现有服务，运行页面将在后续正常重建服务后显示新路径入口。

### 待继续

- 其他五个体系来源路径已在 D117 按原图补齐；后续不再以“缺路径”为待办。
- 由业务负责人从同步培养绿色点开始逐项确认路径和对应图片。

---

## 2026-07-23：恢复原图绿色证明点人工审核视图（D115）

### 本轮目标

- 解决规范化证明点脱离原图绿色分支和对应图片后不便人工判断的问题。

### 完成内容

- 同步培养体系新增“核心卖点 → 原图绿色证明点 → 对应图片/素材”人工审核表，保持绿色点原文和原图父子关系。
- 明确现有 9 个 `pp_` 条目是搜索解释层，不再要求业务负责人把它们当作另一套证明点清单审核。
- 复用现有 `ep_cultivation_*` 绿色证据表达点记录，不新增稳定 code、不修改数据库或人工素材关系。
- 共享证明能力在绿色点确认后再判断；保留原图归属，同时允许支持相邻卖点。
- Skill、文档、卖点对齐和来源对齐专项测试 `17 passed`，`git diff --check` 通过。

### 待继续

- 由业务负责人按表中绿色点逐项确认对应图片及最终主要/支持关系。

---

## 2026-07-23：同步考点业务边界人工审核（D114）

### 本轮目标

- 固定举一反三、万能解法、AI 拍题精学、高频错题和个人错题本之间的业务边界。

### 完成内容

- 举一反三固定为当前题讲解后继续做相似题、同类题或变式题。
- 万能解法固定为同一道题使用不同方法或路径求解。
- 保留同步动画课对举一反三的证明关系：动画讲透原理后继续进入同类/变式训练时，同时支撑两个卖点。
- AI 拍题精学保持独立卖点；讲解后自动推送相似题时，同时证明举一反三。
- 高频错题固定为全网题库/群体共性错题功能；AI 错题本只收集这个学生自己做错的题。
- 已上传发布材料视为业务人工确认事实；未有已审核素材承载的候选结论继续待核验。
- 同步更新体系知识、跨体系校准、taxonomy、证据表达点、运行时目录版本和回归测试。

### 修改文件

- `skills/understand-image-search-intent/references/sync-exam.md`
- `skills/understand-image-search-intent/references/sync-cultivation.md`
- `skills/understand-image-search-intent/references/cross-system-calibration.md`
- `skills/understand-image-search-intent/references/public-phrase-governance.json`
- `skills/understand-image-search-intent/references/evidence-points.json`
- `taxonomy/catalog.json`
- `backend/app/services/query_understanding_service.py`
- `backend/tests/test_taxonomy_catalog.py`
- `backend/tests/test_evidence_point_runtime.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无；未修改数据库概念、公共话术、素材关系或已上传材料。

### 测试结果

- taxonomy、证据表达点、三档话术、查询状态、证明点来源、Skill 与文档一致性专项：`50 passed`。
- 变更文件 Ruff 与 `git diff --check` 通过。

### 遗留问题

- 同步培养体系后续逐卖点审核时，继续核对万能解法其余证明点，不重复改变本轮已确认边界。

### 下一步

1. 等待用户指定下一个卖点；未确认前不继续修改。

---

## 2026-07-23：同步校内证明点人工审核（D113）

### 本轮目标

- 按“一个卖点及其直属证明点”的粒度完成第一体系审核，并清理同步校内文件中的过时待确认项。

### 完成内容

- 人工确认同步校内 3 个卖点、10 个证明点及父子关系不变。
- 明确 `school_sync` 对应 2 个证明点、`animation_explanation` 对应 5 个证明点、`instant_quiz` 对应 3 个证明点。
- 删除“极速预习复习是否独立”的旧待确认口径；它已经是同步自学体系的独立核心卖点。
- 固定“学习效果看得见”为学练测结果表达；日报、周报或家长端长期查看继续归学情报告。
- 明确已上传并发布材料视为业务人工确认事实；只有尚无已审核素材承载的知识文件候选样例继续待核验。

### 修改文件

- `skills/understand-image-search-intent/references/sync-school.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `test_project_skills.py`、`test_proof_point_source_alignment.py`、`test_documentation_consistency.py`：`11 passed`。
- `git diff --check` 通过。

### 遗留问题

- 其余五个体系尚未按卖点逐项完成人工审核。

### 下一步

1. 按用户指示进入下一个卖点或体系；未确认前不修改其他体系。

---

## 2026-07-23：回到 GPT-5.5 主判断（D112）

### 本轮目标

- 按用户要求，“还是回到 5.5”，并且刚刚 DeepSeek 相关实验改动不进入当前运行方案。

### 完成内容

- 本地根目录 `.env` 与 `backend/.env` 的 `MODEL_PROVIDER_ORDER` 已改回 `primary`，当前只走原有 `gpt-5.5` 主判断。
- 回滚 D108～D110 的代码级实验改动：
  - 厂商 `thinking` / `reasoning_effort` 请求参数。
  - `SEARCH_SKILL_STABLE_CONTEXT_ENABLED` Skill 稳定前缀。
  - `SEARCH_THREE_LAYER_UNDERSTANDING_ENABLED` 三层理解分支。
  - 三层模式下的第三层证明点拆分调用。
  - 对应 Compose、示例环境变量和实验测试。
- 保留 D107～D111 的评测报告作为历史实验记录，不作为当前生产策略。

### 当前结论

- 当前运行方案回到 GPT-5.5 原始两层业务判断路径。
- DeepSeek 可用性和三层实验结果只作为后续参考，不再影响当前默认判断链路。

---

## 2026-07-23：GPT-5.5 主判断 30 条回归探针（D111）

### 本轮目标

- 按用户要求，将评测进程临时切回原来的 `gpt-5.5` 主判断，重跑 30 条话术，观察 5.5 是否比 DeepSeek 更稳定。

### 执行口径

- 使用 `gpt-5.5` primary-only。
- 临时清空 DeepSeek/Kimi 后备，避免 fallback 污染结果。
- 关闭 `SEARCH_SKILL_STABLE_CONTEXT_ENABLED`。
- 关闭 `SEARCH_THREE_LAYER_UNDERSTANDING_ENABLED`。
- 不发送 `thinking` / `reasoning_effort` 参数。
- 复用 D107 评测集前 30 条。

### 注意事项

- 第一次在沙箱内直跑时，30 条全部进入 `failed` 分支；随后用最小请求验证，原因是当前沙箱无法解析中转域名，不是 5.5 模型或接口本身失败。
- 经外部网络权限验证中转接口返回 `200` 后，重新跑 30 条并生成本轮正式结果。

### 30 条结果

| 方案 | 外部语义成功 | 包含预设卖点 | 产出卖点 | 空卖点 | 错误卖点 | P50 | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.5 primary-only 前 30 条 | `30/30` | `30/30` | `30/30` | `0/30` | `0/30` | `27167ms` | `36729ms` |
| 普通 DeepSeek 前 30 条 | `30/30` | `24/30` | `25/30` | `5/30` | `1/30` | `30435ms` | `47755ms` |
| DeepSeek 三层 + thinking/high 前 30 条 | `29/30` | `25/30` | `25/30` | `5/30` | `0/30` | `42496ms` | `62045ms` |

### 输出文件

- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_30_GPT55_2026-07-23.json`
- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_30_GPT55_2026-07-23.md`

### 结论

- 在前 30 条样本上，GPT-5.5 的卖点判断稳定性明显优于当前 DeepSeek 普通版和三层 + thinking/high 版本。
- 当前 30 条主要覆盖同步校内、动画精讲、课后小测、新课标和专项培优开头；若要重新决定生产主判断，仍建议补跑完整 100 条，尤其覆盖 DeepSeek 在 D107 暴露出的 AI 私教、极速预习、AI 错题本、真人督学等弱项。

---

## 2026-07-23：三层理解 50 条探针（D110）

### 本轮目标

- 按用户要求，先验证“Skill 稳定前缀 + thinking/high”是否值得继续；若不好用，则回到 DeepSeek `thinking/high`，并按“第一层判断体系、第二层判断卖点、第三层判断证明点/证据表达点”的三层方法优化后重跑 50 条。

### 完成内容

- 保持 `SEARCH_SKILL_STABLE_CONTEXT_ENABLED=false`，不采用 D109 中准确率未提升的 Skill 稳定前缀。
- 新增 `SEARCH_THREE_LAYER_UNDERSTANDING_ENABLED` 实验开关，默认关闭。
- 开启三层理解后：
  - 第一层仍只判断六大体系。
  - 第二层卖点 Prompt 不再携带证明点/证据表达点目录，并明确要求 `matched_proof_points`、`matched_evidence_points` 返回空数组。
  - 第二层成功后，第三层才在已命中卖点范围内补证明点/证据表达点；第三层不得改写第二层卖点。
- 运行 50 条 DeepSeek-only 外部语义评测，临时开启 `thinking=enabled`、`reasoning_effort=high` 和三层理解开关。

### 50 条对比结果

| 方案 | 外部语义成功 | 包含预设卖点 | 产出卖点 | 空卖点 | 错误卖点 | P50 | P95 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 普通 DeepSeek 前 50 条 | `50/50` | `34/50` | `40/50` | `10/50` | `6/50` | `28159ms` | `50053ms` |
| 三层 + thinking/high 前 50 条 | `49/50` | `37/50` | `41/50` | `9/50` | `4/50` | `37790ms` | `62040ms` |

### 关键变化

- 改善样本：`SPX011`、`SPX014` 动画精讲由空变命中；`SPX028` 新课标新考法预测由空变命中；`SPX039` 举一反三由万能解法改为正确；`SPX048` 学段衔接由空变命中。
- 回归样本：`SPX009`、`SPX012` 动画精讲由命中变空；`SPX031` 专项培优错到 AI 定制学习方案；`SPX046` 专家规划由新课标命中变空。
- 另有 `SPX008` 一条外部语义失败，归入 failed 分支，不代表本地语义或公共话术命中。

### 输出文件

- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_50_DEEPSEEK_THREE_LAYER_THINKING_2026-07-23.json`
- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_50_DEEPSEEK_THREE_LAYER_THINKING_2026-07-23.md`

### 测试结果

- `backend/.venv/bin/ruff check app/ai app/core/config.py app/services/ai_service.py app/services/search_external_branches.py tests/test_project_skills.py tests/test_ai_provider.py`：通过。
- `STORAGE_DIR=../storage/images backend/.venv/bin/pytest tests/test_ai_provider.py tests/test_project_skills.py tests/test_proof_point_runtime.py tests/test_documentation_consistency.py`：`26 passed`。
- `git diff --check`：通过。

### 遗留问题

- 三层拆分相对普通 DeepSeek 有小幅收益，但延迟明显更高，且仍存在动画精讲、专项培优、专家规划、学段衔接等弱项波动；当前不足以默认生产开启。
- 后续更值得做的是在三层框架下加强第二层卖点自检与弱项体系定向上下文，而不是继续扩大通用稳定前缀。

---

## 2026-07-23：Skill 稳定上下文 20 条探针（D109）

### 本轮目标

- 验证“DeepSeek + thinking/high + 项目 Skill 稳定业务上下文”是否比单纯 thinking/high 更适合卖点识别。

### 完成内容

- 新增 `SEARCH_SKILL_STABLE_CONTEXT_ENABLED` 实验开关，默认关闭。
- 开启后，第一层体系路由 Prompt 前置六大体系稳定地图，但仍禁止输出卖点 code。
- 开启后，第二层卖点 Prompt 前置六大体系与 16 个核心卖点 stable code 目录和关键纪律；候选体系全文、数据库当前启用卖点目录、证明点和证据表达点仍按原有规则按需加载。
- 未改变默认生产请求体、数据库、素材关系、公共话术或搜索仲裁逻辑。

### 20 条对比结果

| 方案 | 包含预设卖点 | 产出卖点 | 空卖点 | 错误卖点 | P50 | P95 |
|---|---:|---:|---:|---:|---:|---:|
| 普通 DeepSeek | `15/20` | `16/20` | `4/20` | `1/20` | `30687ms` | `47754ms` |
| DeepSeek thinking/high | `17/20` | `17/20` | `3/20` | `0/20` | `40720ms` | `55813ms` |
| Skill 稳定上下文 + thinking/high | `15/20` | `16/20` | `4/20` | `1/20` | `26198ms` | `38792ms` |

### 关键变化

- 相比 thinking/high，Skill 稳定上下文救回 `SPX007`（同步校内）。
- 同时 `SPX010`、`SPX012`、`SPX013` 从动画精讲命中变为空卖点，`SPX003` 仍错到动画精讲。
- 速度明显变快，可能来自稳定前缀带来的请求组织或 DeepSeek 上下文缓存收益；当前脚本尚未记录 `prompt_cache_hit_tokens`，不能把原因定死。

### 输出文件

- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_20_DEEPSEEK_SKILL_THINKING_2026-07-23.json`
- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_20_DEEPSEEK_SKILL_THINKING_2026-07-23.md`

### 测试结果

- `backend/.venv/bin/ruff check app/ai app/core/config.py tests/test_ai_provider.py tests/test_project_skills.py scripts/run_external_selling_point_review.py`：通过。
- `STORAGE_DIR=../storage/images backend/.venv/bin/pytest tests/test_ai_provider.py tests/test_project_skills.py`：`13 passed`。

### 遗留问题

- 当前 Skill 稳定前缀没有提升准确率，不能默认生产开启。
- 下一步若继续探索，应优先记录 DeepSeek `prompt_cache_hit_tokens` / `prompt_cache_miss_tokens`，并对 D107 弱项卖点做定向上下文，而不是扩大通用前缀。

---

## 2026-07-23：DeepSeek 推理参数 20 条探针（D108）

### 本轮目标

- 参考 DeepSeek 示例请求，在不丢失项目两层业务判断角色的前提下，增加可配置 `thinking` / `reasoning_effort`，并用 20 条话术快速观察是否提升卖点识别。

### 完成内容

- `OpenAICompatibleModelProvider` 新增可选 `thinking_type` 与 `reasoning_effort`，默认空值不写入请求体。
- Provider 工厂按 `primary/fallback1/fallback2` 槽位读取对应配置，DeepSeek 可单独开启，GPT-5.5/Kimi 可保持空值。
- Docker 和 `.env.docker.example` 增加对应环境变量。
- 单元测试覆盖请求体里正确发送 `{"thinking":{"type":"enabled"}}` 与 `reasoning_effort=high`，并确认 fallback1 配置能传入 Provider。

### 20 条探针结果

- 口径：复用 D107 DeepSeek-only 100 条评测的前 20 条；临时设置 `FALLBACK1_THINKING_TYPE=enabled`、`FALLBACK1_REASONING_EFFORT=high`；临时禁用 GPT-5.5/Kimi 后备。
- 外部语义成功：`20/20`。
- 包含预设卖点：不开推理 `15/20`，开启后 `17/20`。
- 空卖点：不开推理 `4/20`，开启后 `3/20`。
- 错误卖点：不开推理 `1/20`，开启后 `0/20`。
- 延迟 P50/P95：不开推理 `30687ms/47754ms`，开启后 `40720ms/55813ms`。
- 改善：`SPX008`、`SPX011`、`SPX013`、`SPX014` 从空卖点变为动画精讲。
- 回归：`SPX007`、`SPX009` 从正确命中变为空卖点；`SPX003` 从错分动画精讲变为空卖点。

### 输出文件

- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_20_DEEPSEEK_THINKING_2026-07-23.json`
- `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_20_DEEPSEEK_THINKING_2026-07-23.md`

### 测试结果

- `backend/.venv/bin/ruff check app/ai app/core/config.py tests/test_ai_provider.py scripts/run_external_selling_point_review.py`：通过。
- `STORAGE_DIR=../storage/images backend/.venv/bin/pytest tests/test_ai_provider.py`：`8 passed`。

### 遗留问题

- 推理参数有小幅准确率收益，但延迟变高且出现个别正确样本变空；当前只作为实验开关，不默认生产开启。
- 下一步如果继续评估，应优先对 D107 全 100 条或后半段弱项卖点重跑，而不是只凭前 20 条改生产策略。

---

## 2026-07-23：DeepSeek-only 100 条卖点话术评测（D107）

### 本轮目标

- 按用户要求再跑一轮 100 条话术测试，继续使用大模型辅助语义，重点验证“卖点准不准”，并专项测试 DeepSeek。

### 执行口径

- 用户明确同意把本项目卖点目录、评测话术和相关 Prompt 发送给 DeepSeek。
- 本轮临时使用根目录 `.env` 中有效 DeepSeek key，并清空 GPT-5.5/Kimi 后备 key，只测 `deepseek-v4-pro`；不采用最初被后备模型污染的 6 条中断结果。
- 评测只读，不写回公共话术、素材关系、证明点、证据表达点或业务知识库。

### 完成内容

- 复用 `backend/scripts/run_external_selling_point_review.py` 生成 100 条需要外部语义理解的卖点话术，并串行运行线上同款搜索依赖。
- 修正评测脚本 Provider 标签逻辑：报告只列出当前进程中名称、URL 和 key 都实际配置的 Provider，避免临时禁用后备时仍显示 GPT-5.5。
- 新增 DeepSeek 专项评测原始 JSON 与 Markdown 审批表：
  - `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_100_DEEPSEEK_2026-07-23.json`
  - `docs/SELLING_POINT_EXTERNAL_SEMANTIC_EVAL_100_DEEPSEEK_2026-07-23.md`

### 结果摘要

- 已完成：`100/100`
- 外部语义成功：`100/100`
- 产出至少一个卖点：`60/100`
- 实际卖点包含预设卖点：`52/100`
- 未产出卖点：`40/100`
- 产出错误卖点且不含预设：`8/100`
- 搜索结果层降级：`25/100`
- 延迟 P50/P95：`29170ms / 54831ms`
- 表现稳定卖点：课后小测 `7/7`，学情报告反馈 `6/6`。
- 明显弱项：AI 私教答疑、极速预习复习、AI 错题本、真人老师督学均 `0/6`；学段衔接 `2/6`，专家规划 `2/6`。

### 测试结果

- `backend/.venv/bin/ruff check scripts/run_external_selling_point_review.py`：通过。
- 报告 JSON 汇总校验：Provider `deepseek-v4-pro`，完成 `100` 条，包含预设卖点 `52` 条，空卖点 `40` 条。

### 遗留问题

- DeepSeek 接口可用，但当前 DeepSeek-only 业务语义准确性不足，不能作为唯一或无仲裁主判断。
- `backend/.env` 中的 DeepSeek key 已失效；根目录 `.env` 的 key 有效。后续本地直跑若要继续测试 DeepSeek，需要同步修正 Git 忽略环境文件中的密钥，但不得写入文档或版本库。
- 下一步应优先保留 D085 本地强证据优先、D106 GPT-5.5 后备，并用这份表逐条业务审批，区分“合理多卖点”“模型保守空结果”和“真实错分”。

---

## 2026-07-21：证明点受限语义补全与证据线索隔离（D103）

### 本轮目标

- 解决“卖点已经识别准确，但换一种证明点说法就退回同卖点泛图”的结构性问题，不再依靠逐句补公共话术或查询触发词。

### 完成内容

- 高置信卖点不再无条件阻断证明点理解：查询含有卖点之外的实质细节、且本地证明点未命中时，直接在已确认卖点所属体系内调用第二层模型，跳过重复体系路由。
- 仲裁时始终保留本地已确认卖点；模型只能补该父卖点下已有证明点，不能改卖点、跨父卖点或自造 `pp_` code。
- `SearchProofPointMatch` 新增 `evidence_terms`。模型必须从证明点已有搜索语言中原样选择具体证据线索，Normalizer 与证明点服务再次按目录校验并最多保留三条。
- 第三层不再把包含父卖点名称的通用素材话术分计入证明点素材分；证明点素材只使用具体证据线索、用户原话和版本化证据门槛。修复“零证明点匹配候选未携带 proof code、从而绕过过滤”的边界。
- 普通卖点搜索不触发证明点补全；不支持分层调用的兼容 Provider 保持原有调用行为。
- 同步更新运行时 Skill 输出协议、模型提示词、OpenAPI 契约和前端类型；未新增数据库表、卖点、证明点 code、公共话术或素材关系。

### 测试结果

- 后端全量：`215 passed`；Ruff 通过。
- 前端：OpenAPI 类型重新生成，TypeScript typecheck 与 ESLint 通过。
- 真实页面：两条未登记口语“要动画讲解的，别拖太久，每回只消化一个小点”“想要动画讲解，每次聚焦一个小问题，很快让孩子弄懂”均只返回“5-8分钟讲透知识点，学完就练”1 张，并显示“官方产品定位与教研方法论”证明点。
- 边界页面：“帮我找动画精讲图片”保持 7 张卖点素材且不显示证明点，确认普通泛搜未被错误收窄。

### 遗留问题

- 受限补全仍依赖当前配置的第二层模型；Provider 超时或不可用时保留本地结果，不承诺对从未登记过的证明点口语做无模型语义猜测。
- `evidence_terms` 当前来自治理层 Markdown 搜索语言，不新增数据库证明点表；后续如需业务人员直接维护证明点，必须另做版本化关系和审核方案。

---

## 2026-07-21：六体系证明点结构化与素材缺口门槛补齐（D098）

### 完成内容

- 完成同步考点、同步培养、同步规划、同步自学、同步伴学的证明点结构化；六个体系共 56 条治理层 `pp_` 条目，统一包含论断、搜索语言、可增删证据样例、落点边界和当前素材线索。
- 反查运行库 40 个素材组、427 条已采纳素材话术，记录已有直接素材线索，不把素材独有话术升格为公共卖点语言，也不修改 16 个稳定卖点、数据库概念或人工关系。
- `taxonomy/search_policy.json` 升至 `2026-07-21.1`，新增五条精确 `asset_evidence_requirements`：新中考学校案例、底层方法学校效果、AI 规划数据基础、极速预习/复习效果数据、微信/小程序周报入口。它们只限制明确点名证据的查询，补齐标题或已采纳话术后自动恢复命中。
- 新增证明点结构完整性测试与门槛回归；不新增迁移，不重建索引，不重启容器。

### 验证结果

- `tests/test_asset_selection_policy_service.py tests/test_project_skills.py`：`10 passed`。
- `tests/test_phase4_search_orchestration.py`：`34 passed`。
- 后端全量：`199 passed`。
- `taxonomy/search_policy.json` 通过 JSON 解析，`git diff --check` 通过。

### 遗留事项

- 学校、数据、效果、微信入口和服务套餐等具体证明材料仍需补齐来源、时间、口径和核验状态；未核验内容不能进入对外解释。
- 当前标为素材缺口的证明点在二期图片上线并挂好已采纳话术后会自动放行；不需要再改搜索代码。
- 证明点入库、`卖点 + 证明点` 查询理解输出和管理端关系审核仍需单独决策，不在本轮提前改数据库模型。

---

## 2026-07-20：证明点素材缺口空结果门槛与匹配验证（D097）

### 完成内容

- 用运行库真实数据验证 D096 证明点结构：同步校内三卖点 14 个素材组、71 条已采纳话术与 10 个证明点高度对应（“官方数据规模”素材组与证明点同名；“权威背书”“理科/文科（抽象知识可视化）”“学完即练”“学练测闭环”“题库支撑”“配套功能学情报告/错题本”“教材同步/课程同步”逐一对应）。
- 确认三个素材缺口：学校课堂落地实证无素材（用户确认属二期制作计划）、教材版本覆盖广度无专门素材、教研方法论仅覆盖多专业协同打磨角度。
- 新增 `taxonomy/search_policy.json`（版本 `2026-07-20.5`）可版本化 `asset_evidence_requirements`：查询点名证据主题而素材文本缺少对应证据词时，该素材退出第三层候选；首条规则 `animation_classroom_effect_evidence` 让动画精讲的学校实证类查询在素材制作前返回空，不再倒出同卖点全部图。
- 第三层选图纯函数（查询上下文构造、卖点内排序键）下沉到 `app/domain/asset_text_relevance.py`，`asset_selection_policy_service.py` 回到 140 行架构约束内。
- `sync-school.md` 补充“证明点先于素材存在”原则，并在学校实证证明点标注二期素材状态与门槛 code。

### 验证结果

- 新增回归：证据级查询在素材缺口时返回空、补齐带话术素材后自动恢复命中，`1 passed`。
- 后端全量 `192 passed`（含此前失败的选图服务架构约束），Ruff 通过。
- 103 条评测用例经检索无新增触发词命中，本地基线不受影响。

### 遗留事项

- 二期图片（学校案例、成绩数据等）制作上线并挂好话术后，该门槛自动放行，无需回改配置。
- 其余五个体系结构化证明点时，按同一机制登记各自的二期素材缺口。

---

## 2026-07-20：同步校内证明点第一版结构化（D096）

### 完成内容

- 按业务原版脑图（`docs/source/six-systems/01-sync-school.png`）把同步校内体系的证明点从散文短句升级为结构化条目：3 个卖点下共 10 个证明点，每个包含论断、搜索语言、可增删证据样例和落点边界。
- 固定治理口径：证明点是可复用的“凭什么成立”论断，具体课例、数字、学校和案例只是证据样例；`pp_` 前缀 code 为治理层草拟标识，不进入数据库运行时，第二层意图输出仍只允许 16 个卖点 code。
- 数字、学校、奖项和媒体结论一律标注待核验口径；绿色待制作图片建议继续排除在事实之外。
- 更新 `docs/BUSINESS_SYSTEM_SELLING_POINT_CATALOG.md` 的层级说明与体系状态表。

### 验证结果

- 仅治理层知识文件变更，无数据库迁移、无搜索代码修改。
- 后端文档一致性、Skill 结构与目录相关测试通过（见当日测试记录）。

### 遗留事项

- 其余五个体系的证明点按同一口径梳理。
- 证明点进入数据库概念层（`concept_type` 试点）与查询理解“卖点 + 证明点”输出需要新决策，先在素材最多的卖点小范围验证。

---

## 2026-07-20：卖点内精确图片排序收紧

### 完成内容

- 将已采纳素材独有话术命中提升为已识别卖点内的首要排序键；画面辅助证据和多路召回分仅在其后参与排序。
- 规则仅运行在已审核 `expresses/supports` 素材候选内，继续排除 AI pending 关系与话术；不更改体系或卖点识别。
- 新增回归：即使同卖点泛图拥有更高外部来源分，命中已采纳素材独有话术的精确图仍必须排在前面。

### 验证结果

- 素材独有话术相关搜索编排专项：`3 passed`。
- 真实 GPT-5.5 全链路查询 `做错的题自动收集归类`：图“配套功能，线上错题自动归纳到错题本”位列 Top 1，理由包含已采纳素材独有话术命中，无降级。

---

## 2026-07-20：AI 错题本代表素材关系校准

### 完成内容

- 用户确认“配套功能，线上错题自动归纳到错题本”直接表达“做错的题自动收集归类到错题本”。
- 保留该素材原有的“课后小测”人工关系，并新增“AI 错题本”人工 accepted `expresses` 关系；原 AI pending 建议随人工确认退出待审核状态。
- 新增已采纳素材独有话术：`做错的题自动收集归类到错题本`。没有把这条单图表达误写为概念公共话术或 Skill 全局规则。
- 全量重建 Meilisearch 图片索引。

### 验证结果

- 查询 `做错的题自动收集归类` 的索引 Top 1 为该素材；后续结果为错题同类题强化、错题本定位练习和拍照上传错题。
- 本地可信选图回归同样将该素材排在首位。

---

## 2026-07-20：查询理解长等待与临时失败重试

### 完成内容

- 当前验证环境仅保留 GPT-5.5 时，将查询理解改为长等待模式：体系路由模型预算 60 秒、卖点识别模型预算 90 秒；外层额外保留 5 秒接收和解析余量，避免模型在临界返回时被调度器提前判超时。
- 查询理解分支对临时调用失败在同一总预算内间隔 1 秒重试 1 次；不把该重试扩散到索引、Embedding、Reranker 或本地可信路由。
- 前端语义搜索 HTTP 等待从 120 秒增加至 180 秒。

### 验证结果

- Docker 后端和网页容器已重建，运行配置确认：`gpt-5.5`、仅 `primary`、60 秒体系路由、90 秒卖点识别、5 秒余量、1 次重试。
- 页面真实搜索“AI生成薄弱点报告+学习建议，进步和问题一目了然，孩子更有目标，家长也省心”在 `29.843s` 完成：体系路由 `13.356s`、卖点识别 `15.608s`，返回“学情报告反馈”主表达素材 1 张，无降级、无超时。
- 后端专项：`tests/test_phase4_search_orchestration.py`，`32 passed`；前端生产构建通过。

### 边界

- 延长预算和有限重试能够覆盖慢响应和短暂网络/网关故障，但无法对第三方 Provider 的持续故障、限流或断网承诺绝对成功；这些情况仍必须有限失败并向用户显示降级，而不能无限卡住页面。

---

## 2026-07-20：旧 SQLite 素材库直接恢复

### 完成内容

- 按用户明确授权，以旧 SQLite 素材库覆盖当前 Docker 的图片资产数据；恢复范围为素材组、图片版本、素材概念关系、素材搜索话术、分析记录和 Embedding。
- 新增 `backend/scripts/restore_assets_from_sqlite.py`：导入前校验原图与缩略图，按稳定业务概念 code 重映射关系，不覆盖用户、会话、六大体系、业务概念、公共话术或搜索日志。
- 为 Docker 挂载图片卷采用目录内替换，避免整体重命名挂载点失败；`rebuild_search_index.py` 增加 `--replace`，用于全量替换派生 Meilisearch 索引。
- 覆盖前的 PostgreSQL 与图片卷已备份到 `backups/2026-07-20-pre-legacy-asset-import/`。

### 验证结果

- 当前运行库为 40 个素材组、40 张图片、109 条概念关系、427 条素材搜索话术、40 条分析记录和 40 条 Embedding。
- Docker 图片卷共 80 个文件，对应 40 张原图与 40 张缩略图。
- Meilisearch 健康，主索引已全量替换为 40 个文档；直接检索 `ai私教` 命中已恢复素材。
- 项目端到端索引验证脚本在 SearchService 路由层显示 `fuzzy`，这是当前搜索编排选择的降级模式，不影响索引中 40 个文档已写入；后续业务搜索准确性仍须另行复测。

---

## 2026-07-20：模型理解 Provider 收口为 GPT-5.5

### 完成内容

- 按用户要求将当前运行配置明确限制为 `MODEL_PROVIDER_ORDER=primary`，仅保留主模型 GPT-5.5。
- 清空 Kimi 与 DeepSeek 对应的两个 fallback 槽位；保留中立 Provider 适配器和后备链实现，未改动业务 Skill、Prompt、卖点目录或素材关系。

### 验证结果

- 后端镜像已重建，健康检查通过。
- 脱敏运行实例为 `OpenAICompatibleModelProvider(gpt-5.5)`，Provider 顺序为 `primary`，两个 fallback 均未配置。
- 未发起业务文本模型请求；不以 Provider 配置核验替代业务搜索准确性验收。

---

## 2026-07-17：六大体系首轮跨体系校准与第 5 批评测

### 完成内容

- 新增跨体系校准 reference，统一按对象、动作、时间尺度、目的和执行主体五个维度判别 16 个卖点。
- 校准 AI 拍照/拍题、预习复习、理解原理、规划、反馈/正确率、错题/同类题、跟不上和家长省心等共享入口与相邻边界。
- 静态兜底目录新增 `exact_only_phrases`：共享词只在整句入口时产生探索候选，不再污染带有明确目的的长句。
- 修复显式多需求在包含“监督”等歧义词时被错误降级的问题；否定识别不再使用弱辅助词推断整个卖点被排除。
- 新增第 5 批 28 条跨体系评测，覆盖 16 个卖点正例、共享入口、相邻歧义、真多卖点和显式否定，评测集累计 103 条。
- 校正旧用例：“一道题会一类题”归举一反三；“错题归纳后同类复练”可保持 AI 错题本单卖点；无对象的“考前快速复习”保持待消歧。
- 总纲新增 D063；没有批量改写数据库人工话术、概念定义或素材关系。

### 验证结果

- 第 4、5 批查询状态及跨体系评测专项测试通过。
- Skill 规范校验通过。
- 后端 Ruff 通过。
- 后端全量 Pytest：`131 passed`。
- 相关文件 `git diff --check` 通过。

---

## 2026-07-17：同步伴学体系落盘，六体系第一版全部完成

### 完成内容

- 固定同步伴学两个核心卖点：真人老师督学、学情报告反馈，并复用 `human_teacher_supervision`、`learning_report`。
- 以“真人持续管理学习过程”和“结构化报告展示学习结果”区分两者；老师发送报告可能同时支撑，宽泛“省心/反馈”保持待消歧。
- 保存服务证明、报告字段、家长实操材料、搜索语言、跨体系边界、16 条意图识别用例和待确认事项。
- 套餐服务、90 天周期、推送节奏、用户引语和示例数字全部标记为待核验；绿色内容继续排除。
- 增加同步伴学运行时意图摘要，至此六个体系摘要全部由查询理解 Prompt 自动加载。
- 六体系第一版合计 16 个核心卖点，与当前 16 个稳定业务概念逐一对应，没有新增重复概念。
- 总纲新增 D062，后续入口切换为跨体系一致性复核、自动化意图评测集与可回滚数据库同步方案。

### 验证结果

- Skill 规范校验通过。
- 后端 Ruff 通过。
- 后端全量 Pytest：`129 passed`；专项测试确认六个体系运行时摘要均已加载，套餐和示例数据全文未进入查询理解 Prompt。
- 本轮文档与新增知识文件完成空白字符检查。

---

## 2026-07-17：同步自学体系第一版知识落盘

### 完成内容

- 固定四个核心卖点：AI 私教随时答疑、AI 拍题精学、极速预习复习、AI 错题本，并复用现有四个稳定 code。
- 保存体系原文、拍题精学三组痛点逻辑、证明材料、搜索语言、四个卖点之间及跨体系边界、18 条意图识别用例和待确认事项。
- 将“AI 拍照/拍题”固定为共享入口：根据即时问答、分步解当前题、课前课后快速梳理、个人错题长期归档等目的分流；缺少目的时保持探索或待消歧。
- 第三方测评、效率/正确率数据、跨端同步和同类题数量等产品细节全部标记为待核验；绿色图片建议继续排除。
- 增加同步自学运行时意图摘要，后端查询理解 Prompt 自动加载；同步伴学仍无运行时摘要。
- 总纲新增 D061，下一体系入口切换为最后一个同步伴学。

### 验证结果

- Skill 规范校验通过。
- 后端 Ruff 通过。
- 后端全量 Pytest：`129 passed`；专项测试确认同步自学摘要已进入查询理解 Prompt，效果数据全文未进入 Prompt，同步伴学仍未进入运行时知识。
- 本轮文档与新增知识文件完成空白字符检查。

---

## 2026-07-17：同步规划体系第一版知识落盘

### 完成内容

- 确认同步规划当前只有一个业务原版核心卖点 `ai_learning_plan`，不把八个输入维度和每日课表拆成新卖点。
- 保存体系原文、六组家长/孩子痛点逻辑、三类证明材料、扩展搜索语言、六组跨体系边界、14 条意图识别用例和待确认事项。
- 强识别条件收口为“结合孩子个人情况，生成接下来学什么、先后顺序或什么时候学”；只出现教材版本、专项考点、学段衔接、专家设计、真人督学或学情报告时仍归相邻卖点。
- 用户规模、交互/行为数据、课程量、媒体内容及创始人引语全部标记为待核验材料；绿色页面与宣传图继续排除。
- 增加同步规划运行时意图摘要，后端查询理解 Prompt 自动加载；同步自学和同步伴学仍无运行时摘要。
- 总纲新增 D060，下一体系入口切换为同步自学。

### 验证结果

- Skill 规范校验通过。
- 后端 Ruff 通过。
- 后端全量 Pytest：`129 passed`；专项测试确认同步规划摘要已进入查询理解 Prompt，规模数据全文未进入 Prompt，同步自学仍未进入运行时知识。
- 本轮文档与新增知识文件完成空白字符检查。

---

## 2026-07-17：同步培养体系第一版知识落盘

### 完成内容

- 按业务原版固定三个核心卖点：命题专家与教材编者设计、小初高一体化与学段衔接、底层方法与思维培养。
- 复用现有稳定 code：`expert_planning`、`stage_transition`、`universal_method`，没有因新截图创建重复概念。
- 保存体系原文、证明点类型、扩展搜索语言、跨体系边界、13 条首批意图识别用例和待确认事项。
- 原图绿色文字继续排除；专家身份、课程覆盖、学校落地及成绩效果数据全部标记为待核验材料。
- 明确 `universal_method` 与同步考点 `transfer_practice` 的分流：长期底层思维和摆脱死记对考试题型与变式迁移，共享表达缺少语境时进入待消歧。
- 增加同步培养运行时意图摘要，后端查询理解 Prompt 自动加载；同步规划、同步自学、同步伴学仍无运行时摘要。
- 总纲新增 D059，下一体系入口切换为同步规划。

### 验证结果

- Skill 规范校验通过。
- 后端 Ruff 通过。
- 后端全量 Pytest：`129 passed`；查询理解 Prompt 专项测试确认同步培养摘要已加载、证明数据全文未进入 Prompt、同步规划仍未进入运行时知识。
- 本轮文档与新增知识文件完成空白字符检查。

---

## 2026-07-17：六大体系知识升级为可复用意图识别 Skill

### 本轮目标

- 让六大体系知识既能跨任务复用，也能直接服务当前项目的业务话术意图识别。
- 将六个体系拆成独立知识文件，避免单个巨型目录文档和聊天上下文成为事实来源。
- 继续保持“本地高置信优先、模型处理歧义、人工素材关系决定最终图片”的搜索边界。

### 完成内容

- 将 `skills/understand-image-search-intent/` 升级为双用途 Skill：新增标准 `SKILL.md` 和 `agents/openai.yaml`，保留项目运行时 `RULES.md`。
- 在 `references/` 建立六个独立体系文件和输出协议；同步校内、同步考点迁入完整第一版，其余四个体系建立不参与运行时判断的空骨架。
- 每个已梳理体系在完整知识文件内保存精简“运行时意图摘要”；后端只抽取摘要，不把证明材料全文塞入每次模型 Prompt。
- `skill_loader.py` 在查询理解任务中追加已审核摘要，再追加数据库当前启用概念目录；其他模型任务不加载这些摘要。
- `BUSINESS_SYSTEM_SELLING_POINT_CATALOG.md` 收口为治理、进度和六个文件入口，不再复制体系全文。
- 总纲新增 D058；根目录接力规则要求修改体系知识时完整阅读 Skill 和对应 reference。

### 验证结果

- Skill 规范校验：`quick_validate.py` 通过，`SKILL.md` frontmatter、命名和目录结构有效。
- 后端 Ruff：本轮修改的 Python 文件通过。
- 后端 Pytest：全量 `129 passed`；包含 Skill 摘要只进入查询理解 Prompt、未梳理体系不进入 Prompt、其他模型任务不加载摘要的专项测试。
- `git diff --check`：本轮文件通过。

### 保持不变的边界

- 数据库当前启用卖点、名称、定义及采纳/拒绝话术仍是项目运行时权威。
- 未梳理的体系没有运行时摘要，不根据现有静态标签猜测正式业务事实。
- 在线查询继续先走本地确定性识别；模型只处理歧义或未识别话术。
- 意图识别完成后只按 accepted `expresses`/`supports` 关系匹配图片，没有可信关联图时返回空。

---

## 2026-07-17：启动六大体系业务知识逐体系治理

### 本轮目标

- 避免体系、卖点和证明点只存在于聊天上下文，建立可跨窗口继续的业务知识工作目录。
- 按业务原版固定“体系 → 核心卖点 → 证明点”层级，同时保持证明点可版本化和跨体系复用，不恢复固定二级标签树。
- 围绕原始卖点扩展搜索语言、混淆边界和意图识别用例，为后续精准识别用户真正需要的卖点提供事实底稿。

### 已确认边界

- 绿色文字只表示未来待制作、待补充或待寻找的图片，不作为已有卖点、证明事实、搜索标签或现有素材。
- 允许扩展管理简称、痛点、结果、场景、口语和排除边界，但不能替换原始核心卖点。
- 用户数据、学校案例、效果数据、证书、媒体和奖项在核验前只记录为证明材料类型，不自动形成对外事实。

### 当前完成

- 新增 `docs/BUSINESS_SYSTEM_SELLING_POINT_CATALOG.md`。
- 完成同步校内体系第一版：3 个原版核心卖点、证明点分组、搜索语言扩展、相邻卖点边界和首批 11 条意图识别用例。
- 完成同步考点体系第一版：3 个原版核心卖点、证明点分组、搜索语言扩展、跨体系混淆边界和首批 12 条意图识别用例。
- 总纲新增 D057，并把其余四个体系逐个梳理设为下一步入口。
- 本轮只修改业务文档，无数据库迁移、正式业务数据或运行代码变更。

---

## 2026-07-15：完成 Phase 0～Phase 3 工程改造

### 一、本轮目标

- 将原有“单张图片 + 固定标签”结构逐步改造成“业务概念 + 素材组 + 多对多关系”。
- 保证六大体系稳定，但下层业务内容可以修改、合并、拆分和跨体系复用。
- 主图可以先发布，延展尺寸、备选版本和修订版本可以后续追加。
- 将 AI 识别出的客观画面内容与业务负责人确认的业务关系彻底分离。
- 控制模块体积和单点压力，继续保持 Model、Repository、Service、API 分层。
- 本轮不提前实现 Phase 4 在线搜索编排和 Phase 5 完整端侧改版。

### 二、Phase 0：搜索评测基线

完成内容：

- 扩展搜索评测用例结构，支持：
  - 强相关素材组；
  - 可接受素材组；
  - 禁止出现素材组；
  - 期望业务概念；
  - 查询歧义说明；
  - 是否允许少结果；
  - 数据集完整状态。
- 搜索评测脚本增加执行耗时、Top 素材组、缺失素材、禁止素材和 P95 统计。
- 建立首批 15 条查询的基线数据集。
- 将 `SE004` 绑定到当前唯一有效的真实素材组。
- 生成基线报告：`docs/PHASE0_BASELINE_REPORT_2026-07-15.json`。

当前结果：

- 数据集状态：`partial`。
- 查询数量：15 条。
- 真实素材绑定：1 条。
- `SE004`：Top 1 命中。
- 本地精准搜索 P95：`37.26ms`。
- 当前总体命中率不能作为搜索质量结论，因为正式搜索库只有 1 张可搜索代表图。

主要文件：

- `backend/app/domain/search_eval.py`
- `backend/scripts/run_search_eval.py`
- `taxonomy/search_eval_cases.json`
- `docs/PHASE0_BASELINE_REPORT_2026-07-15.json`

### 三、Phase 1：业务概念层

完成内容：

- 新增可版本化业务概念模型。
- 支持一个概念关联多个业务体系。
- 支持概念之间的相似、替代、合并等关系。
- 将通用搜索表达挂在业务概念层，避免每张图片重复保存相同搜索语言。
- 新增业务概念 Repository、Service、Schema、Serializer 和管理 API。
- 新增幂等概念种子脚本，从现有 taxonomy 和业务意图配置初始化概念数据。
- 种子脚本连续执行两次验证通过，第二次新增和更新均为 0。

当前数据：

- 业务概念：16 个。
- 概念与体系关系：21 条。
- 概念搜索表达：433 条。
- 概念关系：14 条。

主要文件：

- `backend/app/models/business_concept.py`
- `backend/app/repositories/business_concept_repository.py`
- `backend/app/services/business_concept_service.py`
- `backend/app/services/business_concept_serializers.py`
- `backend/app/schemas/business_concept.py`
- `backend/app/api/v1/business_concepts.py`
- `backend/scripts/seed_business_concepts.py`

### 四、Phase 2：素材组、主图和延展图

完成内容：

- 新增素材组模型，将同一套画面的主图、延展图、备选图和修订版归入同一组。
- 首次上传自动建立素材组，不再强制首次上传必须填写业务标签。
- 支持后续追加：
  - 延展尺寸 `derivative`；
  - 备选版本 `alternative`；
  - 修订版本 `revision`。
- 图片新增素材角色、尺寸、宽高比、渠道、版本号和当前版本等字段。
- 上传暂存阶段记录图片宽度和高度。
- 搜索响应按 `asset_group_id` 去重，同一套图只占一个搜索位置，并优先展示主图。
- 保留原图片响应结构，降低旧页面和旧接口的迁移压力。
- 新增素材 Repository、Service、Schema、Serializer 和 API。

当前数据：

- 素材组：2 个。
- 旧图片已完成一图一组回填。

主要文件：

- `backend/app/models/asset.py`
- `backend/app/repositories/asset_repository.py`
- `backend/app/services/asset_service.py`
- `backend/app/services/asset_serializers.py`
- `backend/app/schemas/asset.py`
- `backend/app/api/v1/assets.py`
- `backend/app/services/search_response_builder.py`
- `backend/app/services/storage_service.py`

### 五、Phase 3：图片理解和负责人确认

完成内容：

- 将图片语义升级为 Semantic Profile V2。
- AI 客观识别结果拆分为：
  - 画面事实；
  - OCR 文字；
  - 主体；
  - 场景；
  - 动作；
  - 视觉风格；
  - 画面中可见的产品功能；
  - 素材独有搜索表达；
  - 负向画面概念。
- 取消为了凑数量强制生成 18～22 个标签的规则，改为要求内容真实和维度覆盖。
- AI 只提出业务概念关系建议，默认状态为 `pending`。
- 业务负责人可以确认图片与业务概念的：
  - 主要表达 `expresses`；
  - 可以支持 `supports`；
  - 不适用/排除。
- 人工确认结果作为金标准，与 AI 建议分开保存。
- AI 重新分析时保留已接受、已拒绝和人工确认的关系，不允许覆盖人工结果。
- 图片独有搜索短语进入独立素材搜索短语表，不再混入通用内容标签。
- 保留旧 `ImageBusinessLabel` 兼容读取，计划在 Phase 6 下线。
- 前端现有 AI 详情面板切换为 V2 客观字段展示，并重新生成 OpenAPI 类型。

当前数据：

- 素材概念关系：1 条。
- Semantic Profile 已完成 V1 → V2 数据回填。

主要文件：

- `backend/app/schemas/ai.py`
- `backend/app/ai/normalizer.py`
- `backend/app/services/image_analysis_service.py`
- `backend/app/services/image_semantic_profile_service.py`
- `backend/app/services/asset_relation_service.py`
- `skills/analyze-image-content/RULES.md`
- `client/src/pages/ImageDetail/ImageAiAnalysisPanel.tsx`
- `client/src/types/openapi.d.ts`

### 六、数据库迁移

本轮新增三段独立迁移：

1. `20260715_0009_business_concepts.py`
   - 新建业务概念、概念体系关系、概念关系和概念搜索表达表。
2. `20260715_0010_asset_groups.py`
   - 新建素材组并补充图片版本字段；旧图片回填为素材组。
3. `20260715_0011_asset_semantics_v2.py`
   - 新建素材概念关系和素材搜索短语表；旧关系及 Semantic Profile V1 数据迁移到新结构。

迁移结果：

- 实际本地数据库已升级到 `20260715_0011 (head)`。
- 在数据库副本上完成 `0005 → 0011` 升级验证。
- 完成 `0011 → 0010 → 0011` 降级和重新升级验证。
- Phase 3 降级时会先把 Semantic Profile V2 回写为旧版本可读取的兼容结构。
- `/tmp` 中的数据库只用于迁移验证，不作为长期备份。

### 七、模块分层与维护性处理

本轮按照以下边界拆分代码：

```text
API：鉴权、请求参数和响应输出
  ↓
Service：单一业务工作流
  ↓
Repository：数据库查询和写入
  ↓
Model：数据结构和关系
```

具体处理：

- 业务概念、素材组、素材关系使用三个独立模块承载。
- API 不直接写数据库。
- Repository 不处理 HTTP 和业务编排。
- `ImageAnalysisService` 不直接承担素材关系表的持久化细节，交由 `AssetRelationService` 处理。
- 搜索结果素材组去重放在响应构建层，不塞进图片上传服务。
- 新增架构测试，阻止 API、Service、Repository 重新混成大文件。
- Phase 4 的多路召回、总超时、缓存、降级和 Reranker 未提前塞入本轮模块。

### 八、验证结果

后端：

- Ruff：通过。
- Pyright：0 error。
- Pytest：`96 passed`。
- 数据库迁移升降级：通过。
- `git diff --check`：通过。

前端：

- TypeScript typecheck：通过。
- ESLint：通过。
- Vitest：通过。
- Vite production build：通过。

新增重点测试：

- Phase 0 评测结构和真实素材绑定。
- 业务概念多体系关系及幂等种子。
- 首次上传自动建素材组。
- 延展图后续追加。
- 搜索结果素材组级去重。
- Semantic Profile V1 → V2 兼容。
- AI 建议与人工确认隔离。
- AI 重跑不覆盖人工结果。
- P0～P3 模块架构边界。

测试文件：

- `backend/tests/test_phase_0_3_rebuild.py`
- `backend/tests/test_architecture.py`
- `backend/tests/test_ai_analysis_rules.py`
- `backend/tests/test_search_service.py`
- `backend/tests/test_security_and_images.py`

### 九、未完成事项

- Phase 0 仍缺少 2～5 张已审核代表主图。
- 需要业务负责人确认代表图的“主要表达/可以支持/不适用”关系。
- 需要将 10～20 条查询绑定到真实素材组后重新运行基线。
- 搜索 P95 `2.5s` 目标仍待用户最终确认。
- 当前概念初始类型统一为 `business_term`，后续可由负责人逐步细化。
- （当时状态）Phase 4 在线并行召回、总超时、缓存、降级和 Reranker 尚未开始；现已完成工程改造。
- （当时状态）Phase 5 设计师端和业务搜索端完整交互尚未开始；现已完成工程改造。
- Phase 6 双读迁移、旧标签职责下线和正式切换尚未开始。

### 十、下一步

1. 补充 2～5 张已审核代表主图。
2. 完成负责人业务概念关系确认。
3. 扩充真实查询绑定并重新运行 Phase 0 基线。
4. 更新改造总纲的跨窗口接力区。
5. 开始 Phase 4 搜索核心改造。

---

## 2026-07-15：完成 Phase 4 在线搜索编排改造

### 本轮目标

- 将串行搜索改造成并行、限时、可缓存、可监控和可降级的在线链路。
- 任一外部模型或索引不可用时，数据库概念/短语搜索仍能返回结果。
- 候选融合后只执行一次 Reranker，移除默认链路中的第二次生成式图片摘要裁判。
- 搜索以素材组为排序和展示单位。

### 完成内容

- 新增 `AsyncSearchOrchestrator`，`SearchService` 缩为薄门面和依赖装配入口。
- 将外部分支启动、缓存和主会话水合拆到 `SearchExternalBranches`，将总截止内唯一一次重排拆到 `SearchRerankCoordinator`；总编排器由 455 行收口到 256 行。
- 搜索 API 改为异步 `await search_async(...)`，同步脚本保留兼容入口。
- Meilisearch、Embedding、复杂查询理解在独立线程分支同时启动。
- 外部分支只返回候选 ID/向量，ORM 图片在请求主会话统一装载，避免线程共享 Session。
- 新增版本化概念名称、概念搜索表达和负责人确认素材关系召回。
- 新增多路候选融合和一致性加分。
- 同一素材组在 Reranker 之前合并，最多对 Top 20 素材组调用一次 Reranker。
- Reranker、Embedding、Meilisearch 或生成式查询理解失败时自动降级。
- 查询理解和 Embedding 查询向量增加进程内 TTL/LRU 缓存。
- 增加总截止和分支预算：总计 `2.5s`、Meilisearch `0.2s`、Embedding `0.65s`、复杂查询理解 `0.9s`、Reranker `0.7s`。
- 每次搜索返回并持久化分支状态、耗时、候选数、缓存命中、降级来源和 Reranker 使用信息。
- Meilisearch 派生文档增加素材组和业务概念字段。
- 两到三个字的泛化词只允许完整查询精确匹配，避免“课程/教材”等词在长句中造成跨概念误召回。
- 搜索运营页增加 P95、超时、缓存命中和 Reranker 使用指标。

### 主要文件

- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_rerank_coordinator.py`
- `backend/app/services/search_branch_runner.py`
- `backend/app/services/search_diagnostics_service.py`
- `backend/app/services/search_cache.py`
- `backend/app/services/concept_search_recall.py`
- `backend/app/services/query_profile_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/search_ranking_service.py`
- `backend/app/services/meilisearch_recall_service.py`
- `backend/app/services/embedding_recall_service.py`
- `backend/app/repositories/image_repository.py`
- `backend/app/services/search_index.py`
- `backend/app/models/search_log.py`
- `backend/tests/test_phase4_search_orchestration.py`
- `client/src/pages/AdminSearchOps/components/SearchOpsSections.tsx`

### 数据迁移

- 新增 `20260715_0012_search_orchestration_metrics.py`。
- `search_logs` 增加素材组结果、总耗时、超时、缓存、Reranker、降级来源和各分支状态字段。
- 数据库副本完成 `0011 → 0012 → 0011 → 0012` 往返验证。
- 实际本地数据库已升级至 `20260715_0012 (head)`。

### 测试结果

- 后端 Ruff：通过。
- 后端 Pyright：0 error。
- 后端 Pytest：`106 passed`（含编排分层与文件体量护栏）。
- 前端 OpenAPI 类型：已重新生成。
- 前端 TypeScript、ESLint、Vitest、production build：全部通过。
- Meilisearch 文档重建：dry-run 通过；本机服务未运行，未正式提交索引重建。
- 当前本地精准评测：15 条查询，P95 `49.7ms`，无超时、无降级、无禁止素材。

### 遗留问题

- 当前只有 1 条查询绑定真实素材，无法完成跨概念误判率业务验收。
- 尚未在真实 Meilisearch、Embedding、查询理解模型和 Reranker 全部开启时执行端到端 P95 压测。
- Phase 4 工程完成，但真实数据验收继续标记为 `partial`。

### 下一步

1. 补充 2～5 张代表素材与负责人关系。
2. 将 10～20 条真实查询绑定到素材组。
3. 启动 Meilisearch 后执行正式全量索引重建。
4. 开启真实外部 Provider，完成并发、故障和 P95 压测。
5. 验收通过后再进入 Phase 5。

---

## 2026-07-15：完成 Phase 5 两个使用端改造

### 本轮目标

- 设计师可以先上传一张主图，再在素材详情中维护业务关系、延展尺寸和主图版本。
- 普通业务人员只面对一个搜索框，可选六大体系筛选，并按素材组选择合适尺寸下载。
- 保持页面、hooks、API、Service、Repository 分层，避免上传页或搜索入口成为新的大模块。

### 完成内容

设计师端：

- 上传弹窗改为只强制选择图片，标题由文件名兜底；渠道、主要表达概念和搜索话术均可选。
- 素材详情新增版本工作区，可追加延展图、备选图和修订版，也可替换正式主图。
- 素材详情新增业务概念关系审核，支持逐条或批量接受 AI 建议，并保持人工关系不被 AI 重跑覆盖。
- 素材详情新增素材级搜索话术审核，继续复用素材组继承关系。
- 追加延展图后同步派生索引；替换主图时旧主图退为历史版本并删除旧索引，新主图写入索引。

业务端：

- 删除普通用户可见的“精准/智能”切换，统一为一个业务搜索框。
- 增加六大体系快捷筛选；只有显式选择时才执行硬过滤，默认允许跨体系结果。
- 搜索结果卡改为素材组级展示，提供正式主图、当前延展尺寸、渠道和版本选择。
- 卡片展示可解释的匹配原因、主要表达概念和可以支持概念，不暴露内部搜索模式和等级分组。
- 增加单卡“不相关”反馈，反馈能追溯到具体图片和素材组，但不会修改审批与人工关系。
- 外部 Provider 未配置或超时时仍展示数据库可用结果和简洁降级提示。

分层处理：

- 前端请求集中到 `client/src/api/asset.ts`，查询和 mutation 集中到 `client/src/features/assets/` hooks。
- 版本维护、概念审核、话术审核和搜索结果卡保持独立组件；页面文件只做编排。
- 后端用 `SearchSystemFilter` 管显式体系过滤，用 `SearchAssetPresenter` 组装业务展示字段；搜索编排器只调用它们，不吸收具体展示逻辑。
- 素材组业务继续由 `AssetService` 和 `AssetRelationService` 分工，API 不直接写数据库。

### 主要修改文件

- `backend/app/api/v1/assets.py`
- `backend/app/services/asset_service.py`
- `backend/app/services/asset_relation_service.py`
- `backend/app/services/search_system_filter.py`
- `backend/app/services/search_asset_presenter.py`
- `backend/app/services/search_orchestrator.py`
- `backend/app/schemas/asset.py`
- `backend/app/schemas/image.py`
- `backend/app/models/search_feedback.py`
- `backend/tests/test_phase5_endpoints.py`
- `client/src/api/asset.ts`
- `client/src/features/assets/`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/pages/ImageHome/GlobalImageSearch.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/`
- `client/src/pages/ImageDetail/asset/`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`

### 数据迁移

- 新增 `20260715_0013_result_feedback_targets.py`。
- `search_feedback_events` 增加可空的 `result_image_id` 与 `asset_group_id` 外键和索引。
- 数据库副本完成 `0012 → 0013 → 0012 → 0013` 往返验证。
- 实际本地数据库已升级到 `20260715_0013 (head)`。

### 测试结果

- 后端 Ruff：`app/tests/scripts` 与本轮迁移通过。
- 后端 Pyright：0 error。
- 后端 Pytest：`109 passed`。
- 前端 TypeScript、ESLint：通过。
- 前端 Vitest：2 个测试文件、3 个测试通过。
- 前端 production build：通过。
- OpenAPI 类型：已从当前后端重新生成。
- `git diff --check`：通过。
- 隔离临时数据库页面走查：登录、单搜索框、六体系可选筛选、无外部 Provider 降级和简化上传弹窗正常；浏览器控制台无错误。

### 遗留问题

- Phase 0 仍缺 2～5 张已审核代表图、负责人关系确认和 10～20 条真实查询绑定。
- Phase 4 仍需在真实 Meilisearch、Embedding、查询理解和 Reranker 全部开启后完成 P95 压测。
- 当前真实数据不足，Phase 5 完成表示工作流和工程验收通过，不表示搜索质量业务验收已经通过。
- 后端兼容搜索模式参数和旧标签读取仍保留，统一放到 Phase 6 双读核查后下线。

### 下一步

1. 补齐代表素材、负责人确认关系和真实查询绑定。
2. 启动真实搜索增强服务并重建派生索引，完成端到端压测。
3. 开始 Phase 6 前更新总纲接力区，明确双读范围、迁移校验和回滚开关。
4. 对比新旧搜索结果、修复迁移遗漏，再逐步下线旧字段职责。

---

## 2026-07-15：清空旧图片数据，从空素材库重新录入

### 本轮决定

- 用户明确舍弃全部旧图片及其业务数据，不再迁移旧素材。
- 保留账号、六大体系标签、版本化业务概念和概念搜索表达，作为新素材录入基础。
- Phase 6 取消旧图片数据迁移和基于旧素材的新旧搜索双读；保留新链路验证、配置回滚和旧代码职责下线。

### 清理前数据

- 图片：2。
- 素材组：2。
- 素材概念关系：1。
- 图片标签关系：2。
- 图片分类：2。
- AI 内容标签：29。
- 旧二级分类结果：4。
- 旧图片业务标签：1。
- 本地原图：2 个，缩略图：2 个。

### 已清理内容

- `images`、`asset_groups`。
- 素材概念关系和素材搜索话术。
- 图片标签、分类、内容标签、旧二级分类和旧业务标签。
- 图片分析记录和 Embedding。
- 搜索日志及搜索反馈，避免旧数据影响新素材运营指标。
- `storage/images` 中的原图、缩略图、暂存文件和回收站文件；目录结构及 `.gitkeep` 保留。

### 保留内容

- 用户账号：3。
- 标签体系节点：22。
- 业务概念：16。
- 概念搜索表达：433。
- 概念体系关系和概念间关系。
- 数据库结构、迁移版本和 Phase 0～5 工程代码。

### 验证结果

- 图片及所有图片关联业务表：均为 0。
- 素材组及素材关系表：均为 0。
- 搜索日志和反馈：均为 0。
- 本地图片文件：0。
- SQLite `foreign_key_check`：无异常。
- 数据库迁移版本仍为 `20260715_0013 (head)`。
- 当前 `SEARCH_BACKEND=database`，Meilisearch 未配置，因此不存在需要清理的外部派生索引。

### 后续录入方式

1. 从 1 张已审核主图开始上传，不要求一次补齐全部素材。
2. 在素材详情确认“主要表达/可以支持/不适用”关系。
3. 延展尺寸和替换主图后续按需追加。
4. 累积 3～6 张代表素材后重新建立 Phase 0 基线；累积 10～20 条真实查询后再评价搜索质量。

---

## 2026-07-15：Phase 6 空库旧代码职责下线

### 本轮目标

- 在用户明确舍弃全部旧图片、从空库重新录入的前提下，删除旧图片标签与分类职责。
- 保持模块分层：体系地图、业务概念、素材关系、客观画面语义、搜索编排分别归属独立模块。
- 删除端侧兼容入口和旧搜索模式，保证后续维护不需要同时理解两套业务模型。

### 完成内容

- 删除 `ImageTag`、`ImageCategory`、`ImageLevel2Category`、`ImageBusinessLabel` Model 及对应 Repository、Service、API 写入/读取逻辑。
- 删除旧标签管理、图片标签编辑、旧业务标签审核、旧分类筛选、标签树浏览和 `/tag/:tagId` 页面。
- `tags` 运行数据由 22 个旧树节点收口为 6 个稳定体系节点；16 个业务概念、21 条体系关系、433 条概念表达继续独立存在。
- 图片 AI 分析契约删除 `image_type`、旧 `secondary_labels` 和重复负向字段，统一为 Semantic Profile V2、客观内容标签和 `concept_suggestions`。
- 搜索理解契约删除一级标签/二级分类命名，统一为 `expanded_terms`、`matched_business_concepts`、`excluded_concepts`。
- 删除 `precise/smart/configured` 请求模式、`search_logs.requested_mode` 和相关运营统计；保留的 `search_mode` 只描述实际搜索来源。
- 删除不再使用的生成式图片摘要裁判 Service、模型任务和项目 Skill；在线候选仍最多执行一次 Reranker。
- 搜索运营页切换为 AI 概念关系审核池、业务概念健康度和命中概念统计。
- OpenAPI 前端类型从当前后端重新生成。

### 主要修改文件

- 数据与模型：`backend/app/models/image.py`、`tag.py`、`search_log.py`、`models/__init__.py`。
- 数据访问：`image_repository.py`、`tag_repository.py`、`search_ops_repository.py`。
- 工作流：`image_service.py`、`image_analysis_service.py`、`image_semantic_profile_service.py`、`asset_relation_service.py`、`search_*` 系列服务。
- API 与契约：`api/v1/images.py`、`api/v1/tags.py`、`schemas/image.py`、`schemas/ai.py`、`schemas/search_ops.py`。
- 前端：首页、图片详情、搜索结果、搜索运营页、`features/images` hooks、`api/image.ts` 和类型文件。
- 删除文件：旧标签工作流、旧强标签过滤器、旧图片摘要裁判，以及前端标签面板、筛选弹窗、标签树与标签浏览页。

### 数据迁移

- 新增 `20260715_0014_remove_legacy_image_semantics.py`。
- 删除 `image_tags`、`image_categories`、`image_level2_categories`、`image_business_labels`。
- 删除 `search_logs.requested_mode`，将 `matched_category` 重命名为 `matched_concept`。
- 删除 `tags` 中非体系节点；业务概念数据不删除。
- 在数据库副本完成 `0013 → 0014 → 0013 → 0014`，旧空结构可降级恢复，再升级结果一致。
- 正式本地数据库已升级到 `0014`；迁移前备份：`data/piancton.db.before-phase6-cleanup-20260715`。
- 升级后数据：账号 3、图片 0、体系节点 6、业务概念 16、概念表达 433；SQLite 外键检查无异常。

### 测试结果

- 后端 Ruff：通过。
- 后端 Pyright：0 error、0 warning。
- 后端 Pytest：`82 passed`。
- 前端 TypeScript：通过。
- 前端 ESLint：通过。
- 前端 Vitest：1 个测试文件、`2 passed`。
- 前端 production build：通过。
- 空库首图上传、预览、下载、回收站、统一搜索日志、AI 内容分析及概念建议均有接口回归测试。
- `git diff --check`：通过。

### 遗留问题

- 当前正式素材仍为 0；Phase 0/4 的真实搜索质量验收仍是 `partial`，不能用纯工程测试宣称搜索质量完成。
- Meilisearch、Embedding、查询理解 Provider 和 Reranker 全开启后的真实 P95 仍待新代表素材建立后压测。
- 数据库降级只恢复空旧兼容结构，不恢复已舍弃的旧图片或旧标签树数据。

### 下一步

1. 从 1 张已审核主图开始重新录入，在素材详情确认主要表达/可以支持/不适用关系。
2. 累积 3～6 张代表图后重建 Phase 0 基线。
3. 累积 10～20 条真实查询并启用实际外部 Provider 后，完成 Phase 4 全链路质量与时延验收。

---

## 2026-07-15：建立 Phase 0～6 回滚点并治理文档漂移

### 本轮目标

- 在继续录入真实素材前，把当前 Phase 0～6 工程成果保存为独立、可推送、可回滚的 Git 版本。
- 使用全新 PostgreSQL 环境验证迁移和全量检查，不只依赖本地 SQLite。
- 统一当前执行文档口径，明确历史文档边界，并用自动化测试阻止旧口径回流。

### 回滚点与 PostgreSQL CI

- 创建分支：`codex/image-search-phase6-checkpoint`。
- 创建回滚提交：`7529cee Checkpoint image search rebuild phases 0-6`。
- 推送到 GitHub 后触发 CI run `29425274877`。
- 后端任务使用 PostgreSQL 17，从空数据库执行 Alembic `upgrade head` 到 `20260715_0014`，随后 Ruff、Pyright 和 Pytest 全部通过。
- 前端任务执行 `npm ci`、ESLint、TypeScript、Vitest 和 production build，全部通过。

### 文档治理

- 重写根 README 的当前能力、阶段状态、真实素材入口、统一搜索和服务器验收口径。
- 更新 `backend/README.md`、`ARCHITECTURE.md`、`SEARCH_MODES_AND_AI.md`、`SERVER_DEPLOYMENT_CHECKLIST.md` 和 Meilisearch ADR，使其与 Phase 6 代码一致。
- 为旧前端施工文档、旧优化总表、旧改造总控、旧业务意图地图和旧标签改造方案增加“历史文档说明”。
- `IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 增加发布回滚点、文档治理记录、D026 文档状态决策和 D027 静态概念种子/AI Prompt 偏差记录。
- `DEVELOPMENT_GUARDRAILS.md` 增加当前执行文档、历史文档和自动检查规则。

### 自动防漂移

- 新增 `backend/tests/test_documentation_consistency.py`：
  - 阻止首次上传标签必选、18～22 个标签硬指标、普通用户搜索模式切换等旧契约回到当前执行文档；
  - 要求当前执行文档引用改造总纲；
  - 要求历史施工资料保留明确状态标记；
  - 要求总纲和项目日志发布同一个当前 Phase。
- `make check` 增加前端 ESLint，使本地统一检查与 GitHub CI 口径一致。

### 数据迁移

- 本轮没有新增或修改数据库迁移。
- 本地数据库仍为 `20260715_0014`，正式素材仍为 0。

### 测试结果

- 本地后端 Pytest：`86 passed`，其中新增文档一致性测试 `4 passed`。
- Ruff：通过。
- Pyright：0 error、0 warning。
- 前端 TypeScript、ESLint、Vitest（`2 passed`）和 production build：通过。
- `git diff --check`：通过。
- 首个 Phase 0～6 回滚提交的 GitHub PostgreSQL/前端 CI：通过。

### 遗留问题

- 真实素材、负责人关系和真实查询绑定仍为空，Phase 0/4 业务验收继续是 `partial`。
- D027 尚未落实：概念种子和 AI Prompt 仍以静态 taxonomy 为输入，开放概念长期维护前需要改为不覆盖数据库人工事实并读取当前启用概念。
- 目标服务器的 HTTPS、持久化、权限、备份和恢复演练仍未执行。

### 下一步

1. 后续文档或契约变化继续运行 `make check`，并保留回滚提交与文档治理提交的独立边界。
2. 从空库录入首批 3～6 张代表素材并完成负责人关系确认。
3. 绑定 10～20 条真实查询，重建 Phase 0/4 基线。

---

## 2026-07-15：真实录入前的概念与搜索话术交互收口

### 本轮目标

- 澄清首次上传的“主要表达概念”与六大体系不是固定一级/二级树关系。
- 避免把体系错误理解成普通查询必须先经过的路由层。
- 把素材搜索话术从多行文本框改为更适合业务录入的逐条添加交互。

### 完成内容

- 上传页文案改为“主要表达卖点（业务概念）”，并提示它不是六大体系；体系关系由概念配置复用。
- 首次上传继续只选择一个主要表达概念，提交后确认 `expresses` 关系；不会把图片锁定到唯一体系。
- 明确普通搜索同时使用概念、概念话术、素材独有话术、画面语义和可降级外部分支；只有用户显式选择六大体系筛选时才进行体系硬过滤。
- “业务人员可能怎么搜索”多行文本框改为编号输入项，可通过“添加一条”追加，最多 5 条，支持单条删除。
- 上传页明确通用业务话术维护在概念层，当前素材只补充独有画面、文案或使用场景表达。

### 修改文件

- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/pages/ImageHome/uploadSearchPhrases.test.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`
- `backend/tests/test_documentation_consistency.py`

### 数据迁移

- 无。接口仍接收字符串数组，数据库继续使用 `asset_search_phrases`，仅调整录入交互和说明。

### 测试结果

- 前端 TypeScript、ESLint：通过。
- 前端 Vitest：2 个测试文件、`3 passed`。
- 总纲文档一致性测试增加 D028 和逐条话术交互断言。

### 遗留问题

- 真实素材仍需按新的录入交互上传并观察业务人员是否能区分概念通用话术与素材独有话术。
- 概念体系关系的长期维护仍受 D027 约束，开放业务概念编辑前需要把静态种子和 AI Prompt 收口到数据库事实源。

### 下一步

1. 使用 3～6 张代表图片录入主要表达概念和少量素材独有话术。
2. 在素材详情补充“可以支持/不适用”关系，不在首次上传堆叠全部业务判断。
3. 使用真实模糊句和明确卖点词验证跨概念召回、概念直达和显式体系筛选差异。

---

## 2026-07-15：全项目 UX/UI 第一轮重设计

### 本轮目标

- 修正“最多 5 条”容易被理解为素材永久限制的问题。
- 以资深 UX/UI 视角统一全项目的信息架构、视觉层级、文字和主流程交互。
- 优先解决上传弹窗失衡、说明堆叠、首页双搜索入口、后台表单缺少层级和浏览器原生 `prompt` 等体验问题。

### 完成内容

- 新增 `UX_UI_DESIGN_SYSTEM.md`，定义角色主任务、单页单主任务、渐进披露、布局、上传、搜索、文案、响应式和防漂移规则。
- 更新全局视觉令牌：冷静蓝靛主色、低饱和背景、统一圆角、阴影、焦点和表单状态。
- 全局导航统一为“业务素材中心”，重排主导航和账号菜单，减少头部工具条噪音。
- 首页删除第二个本地搜索框，只保留统一业务搜索；六大体系继续作为可选筛选，素材浏览只保留排序和明确空状态。
- 上传窗口重构为双栏布局：左侧选图与预览，右侧可选信息，底部固定发布；首次话术采用编号逐条添加，明确“首次 5 条、发布后可持续补充”。
- 素材详情统一图片舞台、信息卡、版本、卖点关系和话术维护层级；话术面板支持回车添加并显示已确认数量。
- 用户管理改为带标签的创建表单、中文角色和可扫描列表；密码重置从浏览器 `prompt` 改为专用弹窗。
- 登录、回收站、审计日志、搜索运营和 404 页面统一页面标题、卡片和空状态。

### 修改文件

- 设计系统与公共组件：`tailwind-theme.css`、`button.tsx`、`input.tsx`、`dialog.tsx`、`select.tsx`、`PageHeader.tsx`、`EmptyState.tsx`、`Layout.tsx`。
- 首页与上传：`ImageHome/*`、`UploadAssetPicker.tsx`、`UploadSearchPhraseFields.tsx`、`uploadSearchPhrases.ts`。
- 素材详情：`ImageDetail/*`、`ImageDetail/asset/*`。
- 后台与辅助页面：`AdminUsers`、`AdminAudit`、`AdminSearchOps`、`Trash`、`Login`、`NotFound`。
- 文档与防漂移：改造总纲、项目日志、开发护栏、UX/UI 设计规范和文档一致性测试。

### 数据迁移

- 无。首次上传仍最多发送 5 条初始素材话术；详情页继续通过已有 `asset_search_phrases` 接口持续添加，不存在 5 条数据库总限制。

### 测试结果

- 前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build：通过。
- 浏览器走查：首页、空素材状态、新上传窗口和用户管理页面正常；上传窗口可访问名称和首次/后续话术说明正确。
- 本地 `make check` 全部通过：后端 Pytest `86 passed`、Ruff、Pyright，以及前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 均通过。

### 遗留问题

- 当前素材库仍为空，详情页的真实长内容、不同尺寸版本和 AI 审核密度需要在首批 3～6 张代表素材录入后继续视觉调优。
- 永久删除仍使用现有确认方式，后续可统一为项目内危险操作弹窗，但不阻塞真实素材录入。
- D027 数据库概念事实源偏差仍待落实。

### 下一步

1. 用真实代表图片走一遍上传、分析、卖点确认、话术补充、搜索和下载闭环。
2. 收集业务用户的真实搜索句和失败反馈，确认“概念通用话术/素材独有话术”的文字是否足够易懂。
3. 根据真实图片比例与后台数据密度完成第二轮细节调优，不再凭空增加装饰。

---

## 2026-07-16：产品名称统一为“卖点智库”

### 本轮目标

- 将用户确认的正式产品名称写入界面与当前执行文档，防止品牌文案漂移。

### 完成内容

- 全局导航、登录页和浏览器标题统一显示“卖点智库”。
- 用户进一步指出首页仍保留旧标题“业务素材库”；首页主标题已按 D031 统一为“卖点智库”，英文眉题同步改为 `Selling Point Library`。
- README 与 UX/UI 设计规范同步正式名称；总纲新增 D030。
- `piancton` 保留为仓库、数据库、Cookie 和部署服务等内部技术标识，不做无业务收益的底层改名。

### 修改文件

- 前端：`branding.ts`、`Layout.tsx`、`Login.tsx`、`index.html`。
- 文档：README、改造总纲、项目日志、UX/UI 设计规范和文档一致性测试。

### 数据迁移

- 无。

### 测试结果

- 前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build：通过。
- 文档一致性测试：`4 passed`。
- 浏览器走查：全局导航显示“卖点智库 / 素材搜索与运营”，首页一级标题和浏览器标题均显示“卖点智库”；旧首页标题不再出现，本地 Web、后端和 PostgreSQL 容器均健康。

### 遗留问题

- 无命名遗留；“搜索运营”等后台功能名称可以保留，但首页不再使用“业务素材库”。

### 下一步

1. 使用真实代表素材继续验证上传、搜索和卖点关系维护闭环。

---

## 2026-07-16：首张真实素材搜索修正

### 本轮目标

- 修复“课程同步”素材已经人工确认“同步校内”，但查询“和学校课程一致”仍返回 0 张的问题。
- 保证外部搜索服务失败时，人工确认概念及常见表达仍能由本地链路召回。

### 完成内容

- 新增“学校课程一致/同步/对齐”等 5 条概念级表达，查询不再误判为“动画精讲”。
- 高置信本地概念查询跳过查询 Embedding 和模型查询理解；模糊查询继续并行使用外部分支。
- 实测当前 Provider 延迟后，把查询 Embedding/Reranker 预算调整为 `1.8s/1.4s`，总截止保持 `2.5s`；Docker Compose 显式传递全部搜索预算配置。
- 恢复 Meilisearch 容器，重建 1 张正式素材的派生索引，并完成健康、临时索引写入、真实查询和清理验证；本地 `.env` 启用 `COMPOSE_PROFILES=search`。
- 业务端降级文案改为“智能语义搜索响应较慢，已使用基础搜索”，技术分支名称和超时诊断继续只在管理员搜索运营页展示。

### 修改文件

- 搜索：`business_intents.json`、`search_external_branches.py`、`search_orchestrator.py`、`config.py`、`docker-compose.yml` 和环境示例。
- 前端：`SemanticSearchResult/index.tsx`。
- 测试：`test_business_intents.py`、`test_phase4_search_orchestration.py`、`test_documentation_consistency.py`。
- 文档：改造总纲、项目日志、开发护栏、搜索说明、UX/UI 规范和 README。

### 数据迁移

- 无结构迁移。后端启动时幂等同步 5 条新增概念表达，当前 `concept_search_phrases=454`；Meilisearch 正式派生索引已重建 1 张素材。

### 测试结果

- 失败优先回归：修改前两个专项测试均失败，错误归一为“动画精讲”；修改后通过。
- 专项回归：业务意图、Phase 4 编排和文档一致性共 `21 passed`。
- `make check`：后端 `87 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Provider 单次实测：Embedding `1.648s`、模型查询理解 `9.589s`、单候选 Reranker `1.269s`。
- 真实数据库完整链路：`134ms`、1 张、无降级；关闭全部外部分支：`76ms`、仍返回同一张。
- 浏览器走查：查询“和学校课程一致”显示 1 张“课程同步”，匹配原因包含“学校课程一致”和“同步校内”，无降级警告。

### 遗留问题

- 当前只有 1 张真实素材和 1 条已复验查询，Phase 0/4 搜索质量仍为 `partial`，不能据此宣称整体搜索质量验收完成。
- 当前模型查询理解约 `9.6s`，不适合作为 2.5 秒在线主链路依赖；模糊查询优先依靠本地概念、Meilisearch 和 Embedding，模型结果允许超时丢弃。

### 下一步

1. 继续录入 2～5 张代表素材，并为每张建立明确查询、口语改写和禁止素材。
2. 累计 10～20 条真实查询后重跑 Phase 0/4 基线，观察零结果率、Top 3 命中率和 P95。
3. 根据更多真实延迟样本决定是否更换更快的查询理解模型，不在样本不足时放宽 2.5 秒总截止。

---

## 2026-07-16：公共话术、素材话术与搜索反馈分层优化

### 本轮目标

- 让“卖点公共话术”和“当前素材独有话术”拥有清晰、可进入、可维护的独立入口。
- 明确公共话术、素材话术、客观标签在真实搜索中的作用与优先级。
- 补齐“就是这张”正向标记，为后续真实话术归档建立数据入口。

### 完成内容

- 新增管理员“卖点管理”二级页，按卖点集中查看、添加、修改、停用和恢复公共话术，并展示话术来源与类型。
- 公共话术按标准化文本去重展示，短词单独归入默认折叠的“辅助关键词”；同文本的多来源记录停用或恢复时同步，避免页面重复和状态漂移。
- 公共话术更新使用概念版本号；初始词库话术允许停用但不能直接改名，避免种子再次添加原词造成重复。
- 上传时选择主要表达卖点后自动显示继承公共话术的数量与前 5 条示例；公共话术为空时管理员可以就地添加。
- 上传和素材详情统一使用“当前素材独有话术”，并在素材详情单独展示从关联卖点继承的公共话术及管理入口。
- 素材详情进一步区分已确认话术与 AI 待确认候选；两类内容进入固定最大高度、支持鼠标和键盘纵向滚动的列表，添加入口保持在列表外，避免候选过多拉长整页。
- “手动补充确认关系”调整为默认关闭的按需开关；开启后才显示业务概念、关系类型和确认按钮，已确认关系与 AI 建议不受影响。
- 搜索结果卡新增“就是这张/不相关”双向反馈；正向反馈进入搜索运营数据，但不生成搜索问题，也不自动修改人工业务事实。
- Meilisearch 搜索字段顺序改为已确认卖点公共语言优先于素材独有语言、素材独有语言优先于客观内容标签；数据库权重用自动化测试固定为 `0.95/0.90/0.80`。
- FastAPI OpenAPI TypeScript 类型已重新生成；本地 Docker 后端、Web、PostgreSQL 和 Meilisearch 已重建运行。

### 修改文件

- 后端：业务概念 schema/service/API、搜索反馈 schema、搜索运营归因、Meilisearch 字段设置。
- 前端：卖点管理页、公共话术 API/hooks、上传继承面板、素材详情话术面板、导航与搜索结果正向反馈。
- 测试：Phase 1 概念话术生命周期、Phase 5 正向反馈、数据库/Meilisearch 搜索优先级、文档一致性。
- 文档：README、改造总纲、项目日志、架构、搜索说明和 UX/UI 规范。

### 数据迁移

- 无数据库结构迁移。公共话术继续使用 `concept_search_phrases` 与业务概念版本字段；正向反馈继续使用现有 `search_feedback_events.feedback_type` 字符串字段。

### 测试结果

- 失败优先回归：新增公共话术 PATCH 测试在接口实现前稳定返回 `404`，实现后通过。
- 专项回归：概念话术、正向反馈、搜索索引和搜索服务共 `15 passed`。
- `make check`：后端 `89 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build全部通过。
- Docker production build：后端和前端镜像构建通过，PostgreSQL、Meilisearch、后端和 Web 容器健康。
- 浏览器验收：上传“同步校内”显示 `20` 条去重公共话术和 `11` 个辅助关键词；素材详情正确拆分继承话术与单图独有话术；搜索“和学校课程一致”命中“课程同步”且显示“就是这张/不相关”。验收过程中未提交反馈，未污染真实运营数据。

### 遗留问题

- 当前只有 1 张真实素材，新的字段优先级已有工程测试，但多图片之间的 Reranker 顺序仍需再补充 2～5 张代表图后验收。
- 搜索运营页已能看到正向反馈，自动聚类相似查询并生成“待归档公共话术”的审批队列仍属于后续优化，不在本轮自动改写词库。
- D027 数据库概念事实源偏差仍待落实；本轮只开放公共话术维护，没有开放业务概念长期新增、改名或合并。

### 下一步

1. 上传教材版本图，与现有章节对应图共同验证“同步校内”公共话术继承和素材独有话术区分。
2. 使用“内容跟课本进度一致”“支持人教版教材”等真实查询确认两张素材的召回和排序。
3. 累积正向/负向反馈后设计待归档话术队列，不把每次搜索自动写入正式词库。

---

## 2026-07-16：延展版本删除与回收闭环

### 本轮目标

- 允许设计师在素材详情删除误传或不再使用的延展尺寸，同时保护正式主图和素材组业务关系。
- 沿用现有回收站生命周期，让误操作可恢复并避免前后端状态、素材组展示和搜索索引漂移。

### 完成内容

- 新增素材组范围的非主图版本删除接口；后端校验图片必须属于当前素材组，并拒绝直接删除正式主图。
- 删除只设置图片 `deleted_at` 并移入回收站，不影响素材组、主图、业务概念关系、公共/素材话术或其他尺寸。
- 素材组序列化统一排除已删除版本，搜索索引同时移除对应图片；回收站仍可按既有流程恢复。
- 素材详情为每个非主图版本增加常驻删除按钮；正式主图不显示删除按钮，并保留“替换主图”作为唯一身份变更入口。
- 删除前弹窗明确说明影响范围、可恢复性和主图保护，成功后即时刷新版本列表。

### 修改文件

- 后端：素材组 API、素材服务、素材组序列化和 Phase 5 端点回归测试。
- 前端：素材 API、素材操作 hooks、版本面板、独立删除确认弹窗和 OpenAPI TypeScript 类型。
- 文档：README、改造总纲、项目日志、架构和 UX/UI 规范；文档一致性测试同步锁定 D036 与关键交互。

### 数据迁移

- 无数据库结构迁移。继续复用图片现有 `deleted_at`、回收站恢复和永久删除生命周期。

### 测试结果

- 失败优先回归：新增非主图删除测试在接口实现前稳定返回 `404`，实现后通过。
- 后端专项检查：Ruff、Pyright 通过；Phase 5 与图片安全生命周期测试共 `14 passed`。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重新构建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实详情页只为非主图版本显示 1 个删除按钮，正式主图无删除入口；确认弹窗正确说明影响范围与可恢复性。验收点击“取消”，真实延展版本仍保留，页面无控制台错误。

### 遗留问题

- 当前真实素材只有一个非主图版本；浏览器验收只打开并取消确认弹窗，不实际删除用户真实数据，删除与恢复由隔离测试数据库覆盖。

### 下一步

1. 继续按需上传正确的延展尺寸；误传版本可在版本卡移入回收站。
2. 后续若需要永久清理，统一从回收站执行并继续保留二次确认。

---

## 2026-07-16：修复删除版本后仍显示为相关素材

### 本轮目标

- 修复延展版本移入回收站后，“版本与尺寸”已移除但“相关素材”仍显示旧卡片的问题。
- 收口信息架构：同一素材组的版本不是独立相关素材，只能在版本面板中出现。

### 完成内容

- 相关素材服务在评分前排除当前图片和同一素材组的全部版本，延展、备选和历史版本不再进入“相关素材”。
- 素材版本新增、替换和删除成功后，前端同时刷新图片详情缓存；相关素材与版本面板使用最新服务端状态。
- 回归测试加入同组延展版本候选，先稳定复现错误，再验证只返回其他素材组的相关图片。
- 文档新增 D037，明确“相关素材”和“版本与尺寸”的对象边界并加入一致性自动测试。

### 修改文件

- 后端：相关素材服务及搜索服务回归测试。
- 前端：素材操作缓存同步。
- 文档：README、改造总纲、项目日志、架构、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或接口迁移。

### 测试结果

- 失败优先回归：加入同组延展版本后，旧实现错误返回 2 张相关图片，测试失败；修正后只返回另一个素材组，专项 `2 passed`。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（2 个文件、`3 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：刷新真实素材详情后，“相关素材”标题与已删除版本链接均为 0，“版本与尺寸”保留且只显示正式主图；页面无控制台错误。

### 遗留问题

- 当前正式库只有一个素材组；修复后该详情页没有真正的其他相关素材，因此“相关素材”区域应整体隐藏。

### 下一步

1. 补充第二个真实素材组后，再验证跨素材组的相关素材质量和排序。

---

## 2026-07-16：明确素材需求入口并统一结果卡下拉箭头

### 本轮目标

- 保留整次搜索的“结果不相关”反馈，同时让素材需求入口明确说明提交原因。
- 修正搜索结果卡尺寸/渠道下拉箭头过于靠边且与项目其他下拉不一致的问题。

### 完成内容

- “提交素材需求”改为“没有合适素材提交需求”；“结果不相关”“结果太少”“想要别的风格”保持不变。
- 结果卡尺寸/渠道选择从浏览器原生下拉改为项目标准 `Select` 组件，箭头固定距右边框 `16px`，输入文字同步预留右侧空间。
- 新增前端反馈文案回归测试，并用 D038 与文档一致性测试锁定文案和标准下拉组件。

### 修改文件

- 前端：搜索反馈常量、结果卡和文案回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或接口迁移。

### 测试结果

- 失败优先回归：旧文案未包含“没有合适素材提交需求”，新增测试先失败，修改后通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（3 个文件、`4 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实搜索结果同时显示“结果不相关”和“没有合适素材提交需求”；尺寸/渠道下拉箭头距右边框实测 `16px`，文字右侧预留 `44px`，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 继续从真实业务搜索中观察四个整次反馈选项的使用率，避免继续增加含义重叠的按钮。

---

## 2026-07-16：修复继承公共话术重复展示

### 本轮目标

- 修复同一个“同步校内”公共话术卡在素材详情重复出现两次的问题。
- 保留人工确认和 AI 建议的审计来源，不用删除业务记录掩盖展示层问题。

### 完成内容

- 只读核查真实 PostgreSQL：当前素材同时存在一条 `manual/accepted/expresses` 和一条 `ai/accepted/expresses`，二者指向同一个“同步校内”卖点。
- 新增 `selectInheritedConcepts`，先筛选已接受且非排除关系，再按卖点 ID 集合从概念列表选取，每个卖点只返回一次。
- 素材详情继承公共话术区域改用去重后的卖点列表；人工事实和 AI 审计记录均保持不变。
- 新增前端回归测试，并以 D039 和文档一致性测试锁定展示规则。

### 修改文件

- 前端：卖点话术展示工具、素材详情话术面板和回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构或数据迁移；不删除现有人工或 AI 来源关系。

### 测试结果

- 失败优先回归：人工和 AI 两条已接受关系指向同一卖点时，旧实现没有去重函数，新增测试先失败；实现后专项测试通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情中的“同步校内 · 20 条公共话术”标题和对应管理入口均只出现 1 次，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续新增任何按关系渲染的摘要面板时，同样先明确是展示“来源记录”还是展示“唯一卖点”。

---

## 2026-07-16：继承公共话术严格跟随人工已确认关系

### 本轮目标

- 让“从卖点继承的公共话术”与上方“已确认关系”保持完全一致。
- 当前只有“同步校内”一个人工已确认卖点时，只展示这一张公共话术卡；AI 审计记录不能额外生成继承卡。

### 完成内容

- 将继承条件收紧为 `origin=manual`、`reviewStatus=accepted` 且关系不是 `excludes`，与已确认关系面板采用同一业务事实口径。
- 继续按卖点 ID 去重，保留人工和 AI 来源记录用于审计，不删除或改写现有数据。
- 新增 AI-only 已接受卖点的回归场景，固定它不能在缺少人工确认关系时触发继承。
- 新增 D040、UX/UI 防漂移规则和文档一致性断言；后续新增人工确认卖点后才自动增加对应继承卡。

### 修改文件

- 前端：卖点话术展示工具及回归测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构、接口或数据迁移；AI 审计记录继续保留。

### 测试结果

- 失败优先回归：加入一条只有 AI accepted 关系的卖点后，旧规则错误返回 `sync-school` 和 `ai-only`；增加人工来源约束后专项测试、TypeScript 和 ESLint 通过。
- `make check`：后端 `90 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情中“同步校内 · 主要表达”已确认关系、对应公共话术卡和管理入口均各出现 1 次，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续补充并人工确认新的业务卖点关系时，核对详情页只新增该卖点的一张公共话术卡。

---

## 2026-07-16：延展版本改为纯上传并保护主图话术

### 本轮目标

- 尺寸/渠道延展只作为同一主视觉的附加尺寸上传，不再执行完整 AI 分析。
- 阻止非主图分析替换素材组已有 AI 关系或话术，避免延展图污染主图语义。

### 完成内容

- 延展上传接口无论客户端是否传入 `autoAnalyze=true` 都不创建分析任务；前端也明确发送关闭分析。
- AI 分析接口拒绝对 `derivative` 手动发起完整分析，并返回明确业务错误。
- 素材组级 AI 建议与候选话术只允许正式主图分析刷新；备选等非主图的客观分析只保存在图片自身。
- 延展弹窗明确说明“只上传并识别尺寸、不运行 AI 分析、继承主图关系和话术”，成功提示删除“正在后台分析”。
- 新增 D041，并同步 README、架构、AI 说明、UX/UI 规范和文档一致性防漂移测试。

### 修改文件

- 后端：素材版本接口、AI 分析接口、图片分析持久化边界和 Phase 5 回归测试。
- 前端：素材 API、版本弹窗与成功反馈。
- 文档：改造总纲、项目日志、README、架构、AI 说明、UX/UI 规范及文档一致性测试。

### 数据迁移

- 无数据库结构迁移。
- 真实素材中由已删除延展图遗留的 5 条错误 AI 待确认话术已通过现有审核状态改为拒绝；5 条人工已确认话术和业务关系保持不变。

### 测试结果

- 失败优先回归：旧实现会排队分析延展图，并把 `正确主图候选` 替换成 `错误延展候选`；两项测试修改前均失败，修正后 Phase 5 专项 `6 passed`。
- `make check`：后端 `92 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（4 个文件、`5 passed`）和 production build 全部通过。
- Docker production build：后端和前端镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：延展弹窗明确显示“只上传文件并识别尺寸，不运行 AI 分析”；真实素材中的 5 条错误 AI 候选均已拒绝并从待确认区域消失，5 条人工话术保持可见，页面无控制台错误。

### 遗留问题

- 无。

### 下一步

1. 后续真实上传一个正确尺寸延展，确认只增加版本卡和尺寸，不新增分析状态或 AI 候选。

---

## 2026-07-16：素材独有话术改为统一逐行滚动清单

### 本轮目标

- 把人工新增话术和审核通过的 AI 话术统一展示在同一份已确认清单中。
- 每条话术独占一行，内容增多后在列表内部上下滚动，不再使用横向换行的标签云。

### 完成内容

- 新增素材话术展示分组工具：人工 accepted 与 AI accepted 统一进入已确认清单；AI pending 保留在待确认分组；rejected 不展示。
- 已确认话术改为全宽逐行卡片并增加序号，滚动容器使用纵向滚动和逐条对齐；“添加新说法”继续留在容器之外。
- 同文本按去除首尾空格并忽略大小写去重，避免已确认项和待确认 AI 候选重复占行。
- 现有 mutation 成功后继续以服务端返回的素材组刷新缓存，因此人工新增会直接出现在清单，AI 候选采纳后会从待确认区移动到清单。
- 新增 D042、UX/UI 规则和文档一致性断言，防止交互退回标签云或分裂为两套已确认列表。

### 修改文件

- 前端：素材话术展示工具及测试、素材详情话术审核面板。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构、接口或真实素材数据迁移。

### 测试结果

- 失败优先回归：新增测试最初因展示分组工具不存在而失败；实现后专项测试通过，并覆盖人工新增、AI 已采纳、AI 待确认、拒绝和同文本去重。
- `make check`：后端 `92 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（5 个文件、`6 passed`）和 production build 全部通过。
- Docker production build：后端和 Web 镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材的 5 条已确认话术显示为 5 行等宽卡片，实测每行宽 `708px`、高 `50px`；容器为 `overflow-y: auto` 且启用纵向逐条对齐，页面无控制台错误。

### 遗留问题

- 当前真实素材只有 5 条已确认话术，尚未超过列表最大高度；第 6 条及后续数据会触发内部滚动，分组与溢出规则已由代码和自动化测试锁定。

### 下一步

1. 后续从真实搜索反馈补充第 6 条话术时，顺手确认鼠标、触控板和键盘在列表内的滚动手感。

---

## 2026-07-16：待审核 AI 话术退出高优先级搜索

### 本轮目标

- 人工新增和负责人采纳后的 AI 话术进入高优先级图片话术。
- AI 待审核话术只保留为低优先级语义辅助；客观标签继续辅助画面召回，不能压过人工业务事实。

### 完成内容

- Meilisearch 的 `assetSearchPhrases` 和数据库素材话术直接召回改为只读取 `reviewStatus=accepted`。
- AI pending 话术不再以素材话术 `0.90` 命中；分析产生的原始语义表达继续位于 Semantic Profile、Embedding 和 Reranker 文档，用于模糊语义候选和 Top 20 重排。
- AI rejected 话术会从 Semantic Profile 搜索表达投影中排除，不再继续进入模糊索引、Embedding 或重排文档。
- 人工新增、AI 话术审核及卖点关系确认后按主图刷新 Meilisearch 和 Embedding；派生服务失败仍不影响数据库事实保存。
- 新增 D043，并同步搜索说明、架构、开发护栏、UX/UI 规范和文档一致性测试。

### 修改文件

- 后端：数据库素材召回、图片 Repository、搜索文档、语义档案投影、素材关系服务及依赖装配。
- 测试：搜索服务、搜索索引和文档一致性回归。
- 文档：改造总纲、项目日志、搜索说明、架构、开发护栏和 UX/UI 规范。

### 数据迁移

- 无数据库结构或真实素材数据迁移。
- 当前 PostgreSQL 确认为 0 张图片；Meilisearch 和 Embedding 按新规则执行重建，结果均为 0 条，符合当前空素材库状态。

### 测试结果

- 失败优先回归：旧实现会把 AI pending 素材话术写入高优先级 `assetSearchPhrases` 并给出 `0.90` 数据库分数，两项新增断言修改前均失败；修正后搜索/索引/端点专项 `25 passed`。
- 派生同步回归：AI 话术从 pending 变为 accepted 后，确认主图的 Meilisearch 与 Embedding 均收到刷新调用。
- `make check`：后端 `94 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（5 个文件、`6 passed`）和 production build 全部通过。
- Docker production build：后端和 Web 镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：首页正确显示“素材库还是空的”和上传入口，页面无控制台错误；未向正式库写入测试图片。

### 遗留问题

- 当前没有真实图片，无法进行多素材排序体验验收；优先级规则已由分层单元测试和索引文档测试锁定。

### 下一步

1. 上传首批 3～6 张真实主图后，用“公共话术命中 / 图片独有话术命中 / 仅客观标签命中 / 待审核 AI 话术命中”四类查询做一次真实排序对照。

---

## 2026-07-16：已确认素材话术增加删除闭环

### 本轮目标

- 让素材详情中的已确认话术可以逐条移除，不再只有新增和采纳能力。
- 删除后立即退出搜索，同时保留来源与审核历史，避免误操作造成不可恢复的数据丢失。

### 完成内容

- 已确认话术每行增加常驻删除按钮、可访问名称、处理中禁用状态和成功/失败提示。
- 新增素材组话术删除接口；后端将目标话术软删除为 `rejected`，并刷新主图 Meilisearch 与 Embedding 派生索引。
- 删除后相同人工话术再次添加时恢复原记录为 `accepted`，不新增重复记录。
- 新增服务与 HTTP 端点回归测试，覆盖软删除、数据库直接召回退出、重新添加恢复和两类派生索引刷新。
- 新增 D044，并同步搜索说明、UX/UI 规范和文档一致性护栏。

### 修改文件

- 后端：素材关系服务、素材组 API、搜索服务回归测试和文档一致性测试。
- 前端：素材 API、素材操作 hook 和素材详情话术面板。
- 文档：改造总纲、项目日志、搜索说明和 UX/UI 规范。

### 数据迁移

- 无数据库结构迁移；继续使用现有 `review_status` 保存可恢复的停用状态。

### 测试结果

- 失败优先回归：新增测试最初因 `AssetRelationService.remove_phrase` 不存在而失败；实现后专项 `11 passed`。
- `make check`：后端 `96 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（5 个文件、`6 passed`）和 production build 全部通过。
- Docker production build：后端和 Web 镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情的 6 条已确认话术对应 6 个常驻删除按钮，全部可见并具有包含话术原文的可访问名称；未点击真实删除，页面无控制台警告或错误。

### 遗留问题

- 无。

### 下一步

1. 随真实搜索反馈维护话术时观察误删频率；如频率明显，再增加短时撤销提示，不默认引入阻塞式确认弹窗。

---

## 2026-07-16：素材详情 AI 信息只保留三组

### 本轮目标

- 收口素材详情中过长的 AI 标签区，只展示设计师真正需要判断的三组信息。
- 保持后台搜索信号完整，不把界面精简误做成数据删除或搜索降级。

### 完成内容

- AI 分析区保留语义总结，以及“画面事实、场景、素材独有搜索表达”三组逐项信息。
- 页面移除 OCR、主体、动作、视觉风格、画面可见产品功能、画面排除边界和客观内容标签展示。
- 新增独立展示分组工具和前端测试，输入完整 Semantic Profile 时只返回允许展示的三组，空分组不占页面空间。
- Semantic Profile V2、`content_tags`、搜索索引和模型分析协议保持不变，隐藏字段继续作为后台搜索辅助。
- 新增 D045、UX/UI 规范和文档一致性防漂移断言。

### 修改文件

- 前端：素材详情 AI 分析面板、语义展示分组工具及测试。
- 文档：改造总纲、项目日志、UX/UI 规范和文档一致性测试。

### 数据迁移

- 无数据库结构、接口或真实素材数据迁移。

### 测试结果

- 失败优先回归：新增展示测试最初因分组工具不存在而失败；实现后专项 `2 passed`。
- `make check`：后端 `96 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（6 个文件、`8 passed`）和 production build 全部通过。
- Docker production build：后端和 Web 镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情中“画面事实、场景、素材独有搜索表达”各出现 1 次；OCR、主体、动作、视觉风格、可见产品功能、排除边界和客观内容标签均为 0，语义总结保留，页面无控制台警告或错误。

### 遗留问题

- 无。

### 下一步

1. 后续真实图片分析完成后继续观察三组内容是否仍存在近义重复，再按数据质量而不是新增展示分类进行治理。

---

## 2026-07-16：图片分析与搜索信号收口为 Semantic Profile V3

### 本轮目标

- 按用户进一步确认，把详情页隐藏升级为真正的分析契约收口。
- 停止生成、写入和搜索使用 OCR、主体、动作、视觉风格、可见功能、排除边界和客观内容标签，减少固定词堆积、模型输出和搜索压力。

### 完成内容

- 图片分析契约升级为 Semantic Profile V3，只保留语义总结、画面事实、场景、素材独有搜索表达及独立的业务概念关系建议。
- 单次分析上限收口为 6 条画面事实、4 条场景和 8 条素材独有搜索表达；模型误返回的 V2 旧字段、`content_tags` 或 `recommended_search_words` 会由 normalizer 丢弃。
- 新分析不再写入 `content_tags`；主图再次分析时清空该图旧标签。详情 API 与 OpenAPI 类型删除客观标签和 V2 旧字段。
- Meilisearch、数据库兜底召回、Embedding/Reranker 文档、结果匹配解释和相关素材排序全部退出旧标签；V2 存量 JSON 只兼容读取画面事实、场景和素材独有表达。
- 数据库旧表和旧 JSON 不做物理删除，作为代码回滚存量保留，但运行时不读取、不返回、不写入新数据。
- 新增 D046，明确取代 D045 中“旧字段继续作为后台搜索辅助”的过渡口径，并同步 README、架构、AI 说明、开发护栏、UX/UI 规范和模型 Skill。

### 修改文件

- 后端：AI schema/normalizer/校验、分析持久化、详情序列化、Semantic Profile 服务、数据库召回、搜索文档、Meilisearch 配置、Embedding/Reranker 文档、结果评分和相关素材服务。
- 前端：OpenAPI 类型、应用类型别名和 V3 展示测试。
- 测试与规则：AI 分析、搜索索引、数据库召回、端点、文档一致性测试及 `analyze-image-content` Skill。
- 文档：改造总纲、项目日志、README、架构、开发护栏、搜索与 AI 说明和 UX/UI 规范。

### 数据迁移

- 无数据库结构迁移，也未物理删除正式库旧分析数据。
- 当前 1 张正式主图的 Meilisearch 文档和 Embedding 已按 V3 投影重建，旧字段不再影响在线搜索。

### 测试结果

- `make check`：后端 Pytest `96 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（6 个文件、`8 passed`）和 production build 全部通过。
- Docker：后端和 Web 镜像构建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康。
- 派生索引：Meilisearch `submitted 1 image search documents`；Embedding `rebuilt 1 image embeddings`。
- 浏览器验收：真实素材详情保留语义总结、画面事实、场景、素材独有搜索表达；OCR、主体、动作、视觉风格、可见功能、排除边界和客观内容标签均未出现，控制台无 warning/error。

### 遗留问题

- 数据库仍保留休眠的 `content_tags` 表及旧 V2 JSON，供当前代码版本回滚；确认不再需要回滚后，可另建可降级迁移物理删除。
- 当前只有 1 张正式素材，无法据此评估多素材排序质量；分析和索引压力已从字段数量层面收口，仍需在 3～6 张代表主图后重新跑真实查询评测。

### 下一步

1. 新上传或重新分析下一张正式主图，确认 Provider 实际只返回 V3 字段，并观察 6/4/8 上限下的内容质量。
2. 累积 3～6 张代表主图后，使用公共话术、已确认素材话术、画面事实/场景和模糊表达四类查询做一次排序对照。

---

## 2026-07-16：人工已确认卖点自动消解重复 AI 建议

### 本轮目标

- 已人工确认的卖点不再同时出现在 AI 待确认建议中，避免用户被迫对同一卖点再次选择“接受”或“不适用”。
- 规则落在后端事实层，重新分析也不能让重复建议复活；前端只承担防御性兜底。

### 完成内容

- 手动确认卖点关系时，同素材组、同卖点的 AI pending 建议自动软拒绝为 `rejected`。
- 主图分析持久化前读取人工 accepted 卖点 ID，排除对应 AI 建议，并软拒绝已有历史重复 pending。
- 接受 AI 新卖点后仍保留该条 AI accepted 审计记录并建立人工事实；同卖点其他 pending 自动软拒绝，保持 D039 审计边界。
- 素材组序列化和前端待审核建议选择器增加防御性去重，旧数据或短暂缓存也不会重复展示。
- 当前 PostgreSQL 中“同步校内”人工 accepted 与 AI pending 并存的 1 条历史重复记录已软拒绝，人工关系不变。
- 新增 D047，并同步架构、搜索与 AI 说明、开发护栏、UX/UI 规范和文档一致性测试。

### 修改文件

- 后端：素材关系服务、素材组序列化器和专项服务测试。
- 前端：卖点关系面板、概念建议展示选择器及测试。
- 文档：改造总纲、项目日志、架构、搜索与 AI 说明、开发护栏和 UX/UI 规范。

### 数据迁移

- 无数据库结构迁移。
- 对现有正式 PostgreSQL 执行一次按“同素材组 + 同卖点 + 人工 accepted”条件限定的软清理，共更新 1 条 AI pending 为 rejected；未物理删除审计记录。

### 测试结果

- 失败优先回归：后端最初仍返回同卖点 AI pending，前端选择器不存在，两项新增测试均先失败；修复后专项 `13 passed`，架构测试 `20 passed`。
- `make check`：后端 Pytest `98 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（6 个文件、`9 passed`）和 production build 全部通过。
- Docker：后端与 Web 镜像重建通过，PostgreSQL、Meilisearch、后端和 Web 容器均健康，`/health` 返回 `ready`。
- 浏览器验收：真实素材详情只显示 1 条“同步校内 · 主要表达”；业务卖点区域“AI 待确认建议”为 0、单独“接受”按钮为 0，控制台无 warning/error。

### 遗留问题

- 无。同一卖点未来重新产生 AI pending 已由分析重跑测试锁定。

### 下一步

1. 继续上传下一张代表主图；只审核与人工已确认关系不同的新卖点建议。

---

## 2026-07-16：多卖点意图主导召回与结果卡解释

### 本轮目标

- 允许一句业务需求同时识别多个卖点，不再只保留第一个意图。
- 让高置信卖点和人工确认素材关系真正主导排序，同时在结果页解释每张图因哪个卖点出现。

### 完成内容

- 本地查询理解最多保留 4 个明确候选卖点；当时“AI拍照后即可为你点拨思路，不会立即出答案”被识别为三个卖点。D063 后确认这是共享入口污染长句造成的误多卖点，当前只识别为 AI 拍题精学；本条保留历史实现口径。
- 本地和模型理解中的每个卖点都分别映射数据库业务概念并执行概念 ID 召回，不再只使用单个标准化查询。
- 新增高置信卖点排序保护：人工 `expresses/supports` 候选在候选截断前和 Reranker 后保持高于纯标题、素材话术或弱语义候选；人工 accepted `excludes` 继续硬排除。
- Meilisearch 搜索字段改为已确认卖点名称/公共话术和素材独有话术优先于标题。
- 搜索响应新增每张卡片的 `matchedQueryConcepts`，只返回本次查询卖点与素材 accepted 关系的动态交集；不新增固定图片标签。
- 结果顶部展示“本次识别到的卖点”，支持“全部/单个卖点”在当前结果内缩小；卡片右下角显示“匹配：卖点”，多命中显示 `+N`。无查询级命中时使用“主要：卖点”兜底，避免把素材全部关系误称为本次命中。
- 查询理解 Skill、业务意图种子和三个卖点的公共表达材料同步更新；OpenAPI 前端类型已重新生成。

### 修改文件

- 后端：查询理解、概念上下文、搜索编排、排序、结果评分/拼装、Search schema 和 Meilisearch 配置。
- 前端：搜索结果编排、卡片、卖点展示/筛选工具、应用类型和 OpenAPI 类型。
- 词库与 Skill：`business_intents.json`、`catalog.json` 和搜索意图理解规则。
- 测试与文档：多卖点理解/召回/排序、卡片筛选、索引字段顺序、文档一致性，以及总纲、搜索说明、护栏、UX/UI 和 README。

### 数据迁移

- 无数据库结构迁移。
- 概念公共表达通过既有幂等种子追加；Meilisearch 继续作为可重建派生索引。

### 测试结果

- `make check`：后端 Pytest `100 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（7 个文件、`11 passed`）和 production build 全部通过。
- 专项测试固定：多卖点顺序、三个概念素材同时召回、纯标题候选排在人工关系候选之后、每卡动态匹配卖点和 Meilisearch 人工卖点字段优先于标题。

### 遗留问题

- 当前正式素材数量仍不足，三个卖点的跨素材真实 Top 结果需要在对应代表图上传并完成人工关系确认后继续验收。
- 本地结果筛选只作用于本次已返回候选；素材规模扩大后如需完整分页筛选，再把选中卖点作为显式查询参数交给后端。

### 下一步

1. 为“AI拍题精学、极速预习复习、AI私教答疑”分别补充或确认代表素材关系，用用户原句做一次真实页面验收。
2. 累积 3～6 张代表图后重新运行 Phase 0/4 真实查询评测，观察多卖点候选是否需要按反馈调整置信度。

---

## 2026-07-16：卖点主通道与卖点内图片话术选图

### 本轮目标

- 把“先理解需求并匹配卖点，再在卖点内匹配图片话术”的业务逻辑落实到在线搜索编排。
- 保留多路召回防漏能力，但不再允许所有来源平铺竞争。

### 完成内容

- 高置信单卖点和明确真多卖点进入卖点主通道，只保留 accepted `expresses/supports` 关系素材；卖点外仅标题或图片话术巧合命中的候选不再混入。
- 主通道内新增素材独有话术相似度排序，先根据具体图片表达选图，再由关系角色、原召回分和一次 Reranker 补充排序。
- 主通道无已确认素材时才启用全局数据库、Meilisearch、Embedding、标题、图片话术和画面语义候选；无法确认卖点的画面查询仍可正常命中。
- 查询理解新增 `ambiguous_business_intent_search`：多个未消歧候选降低置信度，不执行卖点硬路由，前端也不将它们展示成“同时识别到的多个卖点”。
- 动态卡片卖点继续只使用本次可信路由卖点与素材 accepted 关系的交集。

### 修改文件

- 后端：查询理解、搜索模型、独立卖点路由服务、排序编排和搜索总编排。
- 前端：卖点结果展示工具及对应测试。
- 测试与文档：业务意图、Phase 4 分层搜索、文档一致性、总纲、搜索说明、开发护栏和 README。

### 数据迁移

- 无数据库结构迁移、无业务数据写入。

### 测试结果

- `make check`：后端 Pytest `106 passed`、Ruff、Pyright；前端 TypeScript、ESLint、Vitest（7 个文件、`12 passed`）和 production build 全部通过。
- Docker：PostgreSQL、Meilisearch、后端和 Web 均健康；正式 PostgreSQL 查询“和学校课程一致”只返回已确认“同步校内”的“课程同步”，原因包含“进入卖点主通道：主要表达”。
- 当时回归把“AI拍照后即可为你点拨思路，不会立即出答案”识别为三个明确卖点；D063 已将其校准为 AI 拍题精学单卖点，原记录只说明当时主通道不会混入“同步校内”素材。

### 遗留问题

- 当前只有 1 张正式素材，卖点内多图排序仍主要由自动化样本验证；需要补充同卖点的第二张代表图进行真实对比。
- 每个卖点的定义、正反例、相邻边界和允许共同出现规则仍需随真实业务样本深化。

### 下一步

1. 在“同步校内”下补充第二张不同画面的素材，用公共话术相同、图片话术不同的查询验收卖点内选图。
2. 为 16 个卖点逐步建立定义、正例、反例、相邻边界和真多卖点共现规则。

---

## 2026-07-17：人工素材属性与结果后二次筛选

### 本轮目标

- 删除搜索框下方重复的完整查询结果标题，保留必要的数量和清除入口。
- 让设计师在首次主图上传时人工补充使用渠道、画面风格和是否为场景图。
- 让业务用户在 AI/卖点推荐完成后按三项人工属性继续缩小，不改变原推荐顺序。

### 完成内容

- 首次上传新增“业务筛选信息”分区：渠道、自由输入且带建议的画面风格，以及“是/否/未标注”三态场景图选择；全部可选，并明确不触发 AI 分析。
- 修正上传弹窗的名称可发现性：尚未选图或单张上传时始终显示“素材名称”，允许先填写或选图后修改；只有多图上传才改为分别使用各文件名。
- 渠道继续保存在具体图片版本；新增素材组级 `style_label`、`is_scene_image`，同组延展尺寸通过素材组引用共享。
- 图片、素材组、详情和搜索响应同步返回人工属性；详情页展示已填写的风格与图片类型。
- 统一搜索下增加折叠式“精细筛选”，搜索前展示但禁用；搜索后从已排序结果动态提取渠道/风格选项，按精确值稳定过滤。未标注素材不会落入“非场景图”。
- 结果区删除“「查询」的素材结果”大标题；未筛选时显示结果数量，筛选后显示当前数量和已用条件数。
- 搜索筛选规则拆到独立 `searchResultFilters.ts`，状态由 `features/images` hook 管理；没有修改查询理解、召回、卖点路由或 Reranker。

### 修改文件

- 后端：素材组 Model/Schema/Serializer、图片 Schema/Serializer、首次上传 API/Service、OpenAPI 类型。
- 前端：上传弹窗、统一搜索、搜索结果、图片详情、搜索状态 hook、独立筛选工具及测试。
- 文档：总纲 D050、项目日志、开发护栏、搜索说明、架构说明、UX/UI 规范和 README。

### 数据迁移

- 新增 `20260717_0015_asset_filter_metadata.py`：`asset_groups.style_label`、`asset_groups.is_scene_image`，其中风格字段建立索引。
- 正式 PostgreSQL 已升级到 `20260717_0015 (head)`；一次性 PostgreSQL 测试库完成从空库升级到 head、降级到 `0014`、再升级到 `0015`，随后删除。

### 测试结果

- 后端：Ruff 通过、Pyright 0 error、Pytest `106 passed`。
- 前端：TypeScript、ESLint、Vitest（8 个文件、`15 passed`）和 production build 通过。
- 专项接口测试覆盖上传字段入库、素材组共享、搜索响应属性和渠道版本集合；前端测试覆盖选项收集、稳定顺序过滤和未标注边界。
- Docker 中 PostgreSQL、Meilisearch、后端和 Web 均健康；浏览器走查通过首页、上传弹窗、已知查询结果、折叠筛选和重复标题删除，控制台无错误。

### 遗留问题

- 当前正式素材在 0015 上尚未填写新属性，因此搜索后的三个精细筛选会保持禁用；上传带属性的新素材后会按返回结果自动启用。
- 当前精细筛选只作用于本次返回的 Top 候选；素材量和分页增长后，如业务需要跨页完整筛选，再将相同规则下沉到后端候选截断前。
- 画面风格当前允许人工自由输入并提供常用建议；积累真实数据后再根据重复值决定是否收口为管理员维护的词表。

### 下一步

1. 下一张代表主图上传时填写一个渠道、一个真实风格并选择是否为场景图，使用同卖点查询验证筛选启用和顺序稳定。
2. 累积 3～6 张带人工属性的素材后检查风格命名重复，再决定是否需要词表治理。

---

## 2026-07-17：D053 数据库知识链路审计修复

### 本轮目标

- 修复代码审查发现的数据库卖点到自动图片分析、AI code 归一化、建议持久化和查询缓存的断点。
- 保留设计师新增的 4 字以下人工话术，但只允许完整查询精确命中，避免长句子串误召回。

### 完成内容

- 后台图片分析使用任务自身的新数据库 Session 构建当前 `AiKnowledge`，不再绕过数据库目录。
- 图片分析建议按数据库 active 概念解析和保存；数据库新增 code 不再被静态 taxonomy 丢弃。
- AI normalizer 增加数据库 code 到当前展示名称的映射，同时覆盖图片建议与查询理解。
- 运行时意图目录新增短人工话术精确集合；精确查询高置信命中，长句子串不匹配。
- 查询理解缓存键加入运行时目录与 AI knowledge 指纹，并把本地高置信判断放在缓存读取之前。
- rejected 话术会从 AI 常见表达与静态正反证据投影排除；否定作用域补齐“的”重置。
- 上传弹窗删除 Semantic Profile V3 已下线的 OCR 分析提示。

### 修改文件

- 后端：`ai/knowledge.py`、`ai/normalizer.py`、`domain/runtime_intents.py`、`domain/query_negation.py`、`analysis_tasks.py`、`ai_knowledge_service.py`、`ai_service.py`、`image_analysis_service.py`、`intent_catalog_service.py`、`query_understanding_service.py`、`search_external_branches.py`。
- 测试：`test_ai_knowledge.py`、`test_query_states_and_negation.py`、`test_phase4_search_orchestration.py`。
- 前端：`UploadDialog.tsx` 文案修正。
- 文档：总纲新增 0.31 和 D055，本项目日志追加本记录。

### 数据迁移

- 无新增数据库迁移，无正式业务数据写入。
- 既有 `20260717_0015` 完成 SQLite `0014 → 0015 → 0014 → 0015` 往返复核。

### 测试结果

- 后端：Pytest `126 passed`、Ruff 全通过、Pyright `0 errors`。
- 前端：TypeScript、ESLint、Vitest（8 个文件、`16 passed`）和 production build 全部通过。
- 新增回归覆盖后台任务知识注入、数据库新增卖点 code 归一化/持久化、rejected Prompt 过滤、短话术精确但不做长句子串、目录变更后旧查询缓存不复用，以及“的”否定重置。

### 遗留问题

- 静态 taxonomy 仍保留为数据库空缺或不可用时的应急兜底，这是 D053 的既定降级边界，不作为正常运行事实源。
- 真实素材仍不足，搜索质量验收继续保持 `partial`，不能由本轮结构回归替代真实图片评测。

### 下一步

1. 用下一张真实主图验证“数据库新增/改名卖点 → 自动后台分析 → AI 建议 → 负责人确认”的完整页面闭环。
2. 在卖点管理页补一条真实 2～3 字人工话术，验证整句可命中、长句不误触发。

---

## 2026-07-17：可信卖点缺图返回空结果

### 本轮目标

- 修复真实页面查询“想要拍题讲解，还要学情报告”错误返回唯一“同步校内”素材的问题。
- 明确外部搜索降级不得突破人工确认的卖点关系边界。

### 完成内容

- 从正式搜索日志确认：查询理解与 Embedding 超时后，本地状态停留在待消歧，Meilisearch 的弱文本候选“课程同步”被直接放行。
- 显式多需求连接词加两个以上高置信数据库概念表达可把待消歧提升为真多卖点；本次查询只保留“AI拍题精学、学情报告反馈”两个强概念。
- 可信卖点路由不再在零相关素材时返回全局候选；数据库、Meilisearch、Embedding、标题或图片话术命中的无关素材统一被过滤，最终返回空结果。
- 待消歧、纯画面和无可靠卖点查询继续保留全局召回，避免把业务关系门槛错误用于画面搜索。
- 新增 D056，并同步搜索说明和开发护栏；D056 覆盖 D049 中“主通道无素材时全局兜底”的旧边界。

### 修改文件

- 后端：`query_understanding_service.py`、`search_concept_routing_service.py`。
- 测试：`test_phase4_search_orchestration.py`。
- 文档：总纲、搜索说明、开发护栏和本项目日志。

### 数据迁移

- 无数据库结构迁移、无业务数据改写。

### 测试结果

- 后端：Pytest `127 passed`、Ruff 全通过、Pyright `0 errors`。
- 专项回归覆盖可信单卖点缺图为空、显式真多卖点缺图为空、无可靠卖点仍可全局召回。

### 遗留问题

- 当前正式库仍只有一张“同步校内”素材；正确空结果可以验证边界，但多卖点有图时的真实合并排序仍需补充代表素材后验收。

### 下一步

1. 用当前正式查询重新走查，确认页面显示 0 张且不再出现“课程同步”。
2. 分别补充“AI拍题精学”和“学情报告反馈”代表素材，验证同一查询可合并返回两个卖点方向。

---

## 2026-07-17：Skill、静态兜底与数据库三方只读对比

### 本轮目标

- 对比六体系 Skill 第一版、静态意图目录与当前数据库的卖点名称、定义、体系关系和公共话术。
- 先形成可回滚差异清单，不自动覆盖数据库。

### 完成内容

- 只读导出当前数据库 16 个卖点、21 条体系关系和 433 条概念搜索表达；全部话术均为 `source_document + accepted`，没有人工新增或拒绝差异。
- 确认六体系、16 个稳定 code 及数据库/静态展示名完全一致；Skill 中 11 个更完整标题继续作为业务工作名，不自动改数据库名称。
- 定位 4 个跨体系卖点的运行时主体系展示错误：关系数据正确，但代码没有优先 `core`。
- 定位 14 条静态 `exact_only` 共享入口被数据库普通 tier 重新放大的问题；明确不能用 rejected 直接替代匹配模式。
- 定位 `universal_method` 两条旧“一题会一类题”表达与 D063 边界冲突，列为业务确认后的小范围数据动作。
- 对 103 条评测分别运行静态目录与数据库运行态：目标卖点命中从 93/95 降到 92/95，查询状态命中从 49/54 降到 46/54，共 9 条结果差异。
- 新增三方对比文档和机器可读同步提案，按“应同步、共享入口、需业务确认、禁止同步”分级，并写明每项回滚方式。

### 修改文件

- `docs/BUSINESS_INTENT_DATABASE_COMPARISON_2026-07-17.md`
- `docs/BUSINESS_INTENT_DATABASE_SYNC_PROPOSAL_2026-07-17.json`
- `docs/BUSINESS_SYSTEM_SELLING_POINT_CATALOG.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库结构迁移、无数据库业务数据写入。
- 数据库只读快照对应运行时目录指纹 `2026.07.2+db-3e6d49a2bf0f7773`。

### 测试结果

- 读取数据库后逐条比对 16 个卖点和 433 条话术。
- 103 条本地意图评测完成静态/数据库双跑，并保存聚合结果到三方对比文档。
- 配套 JSON 提案通过解析校验。

### 遗留问题

- P1 `core` 体系优先与 P2 静态 exact 模式优先尚未实施。
- P3 两条旧 `universal_method` 话术需要业务确认后才能写库。
- “考前快速复习”和单独“复习”的候选/评测口径仍需继续校准。
- 真实代表素材不足，当前只能验证意图层，不能据此宣称图片搜索质量验收通过。

### 下一步

1. 实施 P1/P2 并运行完整后端回归。
2. 业务确认 P3 后，以事务、before/after 快照和自然键执行两行数据更新。
3. 用真实搜索日志逐词评审其余跨卖点泛词，不进行整库覆盖。

---

## 2026-07-17：六体系 Skill 校准接入实际搜索

### 本轮目标

- 让六体系 Skill 不只停留在知识文档，而是实际提升项目内业务话术搜索准确率。
- 修复旧数据库 seed 对 Skill 共享入口边界的覆盖，同时保留数据库的名称、启停和审核权威。

### 完成内容

- 运行时体系展示改为 active `core` 优先，修复 4 个跨体系卖点显示到 support 体系的问题；support 关系继续保留。
- 运行时目录合并增加静态 `exact_only` 模式优先，14 条共享入口不再被数据库旧 official/alias 提升成长句强匹配。
- 待消歧状态下保留置信度相同的弱候选；单独输入“复习”会同时保留极速预习复习和 AI 错题本，不再按目录顺序选唯一候选。
- `universal_method` 的“一道题会一类题”“一道题学会一类题”两条旧 seed 从 accepted 改为 rejected，concept version 升为 2；`taxonomy/catalog.json` 同步移除错误别名，`transfer_practice` 正确表达保持不变。
- 数据更新严格按 `concept_code + phrase + origin` 两个自然键执行，before/after 和恢复为 accepted 的回滚方式保存在机器提案中。
- 数据库运行时目录指纹由 `2026.07.2+db-3e6d49a2bf0f7773` 更新为 `2026.07.2+db-46d6e4d365fb8d8c`，查询缓存会自动隔离旧知识。

### 修改文件

- 后端：`runtime_intents.py`、`intent_catalog_service.py`、`query_understanding_service.py`。
- 测试：`test_query_states_and_negation.py`。
- 词库：`taxonomy/catalog.json`。
- 治理：三方对比文档、机器同步提案、六体系目录、总纲和项目日志。

### 数据迁移

- 无 schema 迁移。
- 当前数据库只更新 2 条旧 `source_document` 话术的 `review_status`：accepted → rejected；没有删除记录，支持按同一自然键恢复。

### 测试结果

- 103 条本地意图评测：带目标业务卖点的用例从数据库运行态 92/95 提升到 95/95；目标查询状态从 46/54 提升到 49/54。
- 其余 5 条状态用例均为纯颜色、版式或场景搜索，本地业务意图返回空并交给画面分支，不硬绑六体系卖点。
- 后端全量 Pytest `135 passed`；Pyright `0 errors`；本轮变更文件 Ruff 通过；Skill `quick_validate.py` 通过。
- 仓库全目录 Ruff 仍会报告历史 Alembic 文件的既有 41 项格式问题，本轮未修改这些迁移文件。

### 遗留问题

- 95/95 只证明业务意图层保留了正确卖点，不等于图片 Top 排序验收完成。
- 正式素材仍不足；有正确卖点但没有 accepted `expresses/supports` 图片关系时，系统会按既定规则返回空结果。
- 数据库当前没有独立 `match_mode` 字段，exact 模式暂由 Skill/静态目录提供；如以后要求后台完全管理匹配模式，再单独设计迁移。

### 下一步

1. 用 5～10 条真实业务输入在页面走查识别卖点、主体系、理由和缺图空结果。
2. 补充已审核代表图和 accepted 关系后，验证“业务话术 → Skill 意图 → 卖点 code → 图片”的完整链路。

---

## 2026-07-17：精简卖点目录与 Skill 一一映射固化

### 本轮目标

- 确认卖点管理页使用的精简目录与六体系 Skill 完整业务卖点逐项对应。
- 防止后续改名、旧备份恢复或重复种子再次造成目录、Skill 和运行库漂移。

### 完成内容

- 新增机器映射 `selling-point-map.json`，以稳定 code 连接 6 个体系、16 个页面/数据库精简名、16 个 Skill 完整业务名及对应体系文件。
- 新增自动化校验，阻止卖点漏项、重复 code、展示名漂移、错主体系或 Skill 文件缺少稳定 code/完整业务名。
- 复核运行库发现 `universal_method` 两条旧“一题会一类题”表达再次处于 accepted；新增迁移及种子同步末端保护，将其稳定维持为 rejected 并保留审计记录。
- 当前运行库逐项校验结果为 `expected=16`、`active=16`、`mismatches={}`；页面继续显示精简名称，搜索与 Skill 依靠稳定 code 对接。

### 修改文件

- Skill：`skills/understand-image-search-intent/SKILL.md`、`references/selling-point-map.json`。
- 后端：`backend/scripts/seed_business_concepts.py`。
- 测试：`backend/tests/test_skill_selling_point_alignment.py`。
- 文档：六体系目录、三方对比、总纲和项目日志。

### 数据迁移

- 新增并已应用 `20260717_0016_align_skill_selling_points.py`。
- 当前运行库迁移版本为 `20260717_0016`；公共话术共 513 条，其中 511 条 accepted、2 条 rejected。

### 测试结果

- 后端全量 Pytest：`138 passed`。
- 新增映射、种子和意图专项测试：`18 passed`。
- 本轮 Python 文件 Ruff 通过，JSON 解析通过，`git diff --check` 通过，Skill `quick_validate.py` 通过。
- 本地 Docker 服务重新构建后健康；运行库 16 项逐条比对无差异。

### 遗留问题

- 本轮保证“目录 → Skill → 卖点 code”准确，不等于真实图片关系和搜索排序已经验收；代表图片与 accepted `expresses/supports` 关系仍需逐步补齐。
- Skill 完整业务名用于解释与识别，页面精简名用于浏览；如需修改展示名，应同步更新数据库/静态目录和机器映射并通过校验。

### 下一步

1. 继续以稳定卖点 code 绑定公共话术和单图独有话术，不用名称字符串猜测关系。
2. 补充代表图片后验证“业务输入 → 意图识别 → 卖点 code → 已审核图片”的完整闭环。

---

## 2026-07-17：公共话术受控优化与三档自然语言覆盖

### 本轮目标

- 在不改变六大体系、16 个核心卖点、稳定 code、主体系和已确认语义边界的前提下，提高业务搜索话术覆盖。
- 同时覆盖熟悉业务、了解一点业务和业务小白三种输入方式，避免为覆盖自然语言而无限堆公共话术。

### 完成内容

- 新增 `public-phrase-governance.json`，把固定卖点映射、公共入口、共享入口、非路由宽泛词、Skill 理解信号和评测样例分层治理。
- 每个卖点只新增 1 条高信息公共话术，共 16 条；新增话术全部使用既有稳定 code，未新增卖点、未改名称、未改定义、未改主体系关系。
- 新增 48 条三档评测：每档覆盖全部 16 个卖点。评测长句不进入数据库，不在卖点管理页增加条目。
- 新增 13 个 Skill 自然语言归一化信号，用于理解“会没会、换个数字、出过卷、自己分析、先学什么、学了多久”等口语；信号只参与本地意图理解，不物化为公共话术。
- Skill 明确公共话术优化顺序、单轮上限、共享短词和宽泛结果规则；运行时规则明确小白长句可以语义归一，不要求逐句落库。
- 本地 Docker 后端重建后自动幂等同步新增话术；当前运行库为 16 个 active 卖点、529 条话术，其中 527 accepted、2 rejected。
- 测试夹具强制隔离常驻 Meilisearch 配置，统一使用数据库搜索；文档一致性测试在生产后端镜像中明确跳过，在完整源码工作区继续强制执行，避免把镜像打包边界误报为产品失败。
- 最终后端常驻容器已重建，后端、Web、PostgreSQL 和 Meilisearch 四个服务全部 healthy；`/health/ready` 返回 production ready。

### 修改文件

- Skill：`skills/understand-image-search-intent/SKILL.md`、`RULES.md`、`references/public-phrase-governance.json`。
- 词库：`taxonomy/business_intents.json`，版本升级为 `2026.07.3`。
- 后端：`backend/app/domain/runtime_intents.py`、`backend/app/services/query_understanding_service.py`。
- 测试：`backend/tests/test_skill_selling_point_alignment.py`、`conftest.py`、`test_documentation_consistency.py`。
- 文档：总纲和项目日志。

### 数据迁移

- 无 schema 迁移；既有启动流程会在迁移后执行幂等 `seed_taxonomy`，按稳定 code 补入 16 条 `source_document + official + accepted` 公共话术。
- Skill 的 13 个自然语言归一化信号不写数据库，不影响卖点管理页计数和人工审核记录。

### 测试结果

- 固定映射、公共话术治理和三档覆盖专项测试：`6 passed`。
- 48 条三档样例全部保留预期卖点；每档 16 条、覆盖全部 16 个稳定 code。
- 常驻后端全量测试：`137 passed, 4 skipped`，0 failed；4 项是生产镜像不包含项目文档时按设计跳过的文档一致性检查。
- 完整项目只读挂载、无网络、数据库搜索模式下全量测试：`141 passed`，0 failed、0 warning；常驻容器之前的 5 个环境失败已全部消除。
- JSON 解析、`git diff --check` 和 Skill `quick_validate.py` 通过。

### 遗留问题

- 48 条样例验证的是“语言 → 卖点 code”，不等于图片排序验收；图片仍必须存在 accepted `expresses/supports` 关系才能返回。
- 新公共话术上线后需要结合真实搜索日志观察误召回和未识别表达；不得仅凭少数搜索失败继续堆词。

### 下一步

1. 让业务人员分别用直接卖点、功能描述和小白痛点各输入 5～10 条真实话术，记录识别卖点、查询状态和是否命中图片。
2. 只把多次出现、边界唯一的缺口升级为公共话术；其余变体优先补充 Skill 理解信号或保持待消歧。
3. 补充已审核代表图片和 accepted 关系后，验收“业务输入 → 卖点 code → 对应图片”的完整链路。

---

## 2026-07-18：上传前 AI 素材独有话术生成

### 本轮目标

- 降低设计师首次上传时人工构思素材独有话术的负担，同时保留可见、可编辑和人工确认边界。
- 复用现有模型供应商能力，不改变六大体系、16 个卖点、公共话术或发布后后台分析。

### 完成内容

- 新增上传前单图分析接口，设计师可选择精确生成 2、3、4 或 5 条素材独有话术。
- 新增专用模型任务与最小规则文件，只生成当前图片独有的画面、文案或使用场景搜索说法；输出数量、重复、空值和长度由服务端强校验。
- 上传界面新增数量选择和“生成并填充”按钮；结果替换当前输入并可继续修改。界面明确提示上传即视为确认。
- 已选卖点只按稳定 code 提供上下文，不改变卖点目录和边界；未配置 AI、未选图或批量上传时安全禁用。
- 图片只暂存于既有安全上传校验流程，模型调用完成或失败后都删除；生成动作不建立图片记录、关系或搜索索引。
- 发布后原有后台画面分析、卖点建议和索引更新继续执行，与本次手动触发的草稿生成相互独立。

### 修改文件

- 后端：AI contract、normalizer、provider、schema、依赖、API、AI service 和新增临时分析 service。
- 前端：上传对话框、话术生成组件与 hook、图片 API、OpenAPI 生成类型和组件测试。
- Skill：`skills/generate-asset-search-phrases/RULES.md` 与 Skill 索引。
- 文档：总纲 D068 与本项目日志。

### 数据迁移

- 无数据库迁移；生成草稿在上传前不持久化。

### 测试结果

- 完整源码、无网络、数据库搜索模式后端全量测试：`145 passed`。
- 前端 Vitest：`18 passed`；TypeScript typecheck 与 ESLint 通过。
- 重建后端常驻容器健康，实际 OpenAPI 已包含 `/api/ai/asset-search-phrases` 并重新生成前端类型。

### 遗留问题

- 实际生成质量仍需要使用代表图片和真实业务表达验收；模型未配置时只能手动填写。
- 当前只允许单图生成，批量上传保持手动填写，避免一组话术错误套用到多张素材。

### 下一步

1. 重建 Web 并在真实上传弹窗验证 2～5 条选择、加载态、回填、编辑和重新生成。
2. 使用 3～6 张代表图记录生成结果、人工修改量和搜索命中情况，再调整专用规则，不扩张六体系卖点边界。

---

## 2026-07-18：AI 素材话术业务搜索意图校准

### 本轮目标

- 修正首次真实生成结果过度复述手机界面、教材目录、OCR 和章节名称的问题。
- 让结果回答“业务人员为了找到这张图会怎么搜”，并继续受已选卖点边界约束。

### 完成内容

- 生成顺序调整为“素材名称定主题 → 已选卖点定业务边界 → 图片提供证据 → 改写为自然搜索需求”。
- 模型现在接收已选卖点的当前数据库名称、定义、采纳表达、正向证据和排除边界，不再只接收 code 与展示名。
- 规则要求优先使用“找一张……的图”“有没有能体现……的图”等完整需求；生成 3 条以上时至少两条采用业务小白的口语或结果导向表达。
- 新增同步校内正反例：保留“找一张能体现和学校教材进度一致的图”等搜索表达，明确拒绝“手机章节切换界面对照八年级数学课本目录”等画面说明。
- 上传表单说明、AI 区标题和输入框示例同步调整，避免设计师误以为需要填写图片客观描述。
- 六大体系、16 个卖点、公共话术、卖点关系和上传确认边界均未改变。

### 修改文件

- 运行时规则：`skills/generate-asset-search-phrases/RULES.md`。
- 后端：AI knowledge、knowledge service、AI service 及对应测试。
- 前端：上传话术区域、AI 生成组件及组件测试。
- 文档：总纲 D069 与本项目日志。

### 数据迁移

- 无数据库迁移；只增强模型上下文和生成规则。

### 测试结果

- AI 话术、数据库知识和上传接口专项：`29 passed`。
- 完整源码后端回归：`145 passed`。
- 前端 Vitest：`18 passed`；TypeScript、ESLint 和生产构建通过。
- 自动化测试确认 `school_sync` 请求含完整业务定义，并包含用户确认的自然搜索正例与画面说明反例。
- 使用项目同步校内代表图、素材名“课程同步”和 `school_sync` 实际调用当前模型，返回 5 条均为业务搜索需求：教材版本一致、学校学到哪回来复习到哪、课本章节与线上目录同步、避免教材版本对不上、课程跟校内进度走；未再输出 OCR 章节罗列或界面说明。

### 遗留问题

- 项目代表图已通过真实模型验收；用户当前上传的具体成品图仍需刷新页面后重新选择并点击一次，确认结果同样符合业务口径。

### 下一步

1. 用户用当前“课程同步”成品图重新生成 5 条，确认与代表图验收结果一致。
2. 再选 2～3 个不同体系的代表图复测，确认规则不是只对同步校内样例有效。

---

## 2026-07-18：素材自由命名与全局重名自动编号

### 本轮目标

- 保持设计师自由命名，不增加风格、卖点或画面内容拼接规则。
- 同名素材按上传先后自动顺延，避免设计师理解和维护编号。

### 完成内容

- 上传主图、追加版本、替换主图和详情改名统一经过全局名称分配服务。
- 未重名时原样保存；重名时追加固定三位序号，并识别已有 `001` 等序号后继续顺延。
- 回收站图片继续参与判重；前端在单图上传时预览“发布时将自动保存为”的最终名称，但不改写输入框。
- 主图改名同步素材组标题；卖点、体系、渠道和风格均不参与命名。
- PostgreSQL 以事务锁串行分配，数据库增加大小写/首尾空格归一化唯一索引作为并发兜底。

### 修改文件

- 后端：名称领域规则、名称服务、图片仓储/服务/API、素材版本服务、图片 schema/model。
- 前端：名称预览 API/hook、上传提示、上传完成和详情改名反馈。
- 数据库：`20260718_0017_unique_image_titles.py`、`20260718_0018_image_title_reservations.py`。
- 测试与文档：名称规则测试、上传/回收站/改名集成测试、总纲 D070 和项目日志。

### 数据迁移

- 迁移按创建时间保留最早名称；既有重名依次改为 `001、002…`，并同步对应主素材组标题。
- 新增 `uq_images_title_normalized` 表达式唯一索引。
- 新增轻量名称占用历史表；图片进入回收站或永久清除后，已使用名称和编号仍不释放。

### 测试结果

- 后端全量：`152 passed`。
- 前端：Vitest `18 passed`；TypeScript typecheck 与生产构建通过。

### 遗留问题

- 无阻塞问题。回收站和永久清除都不会释放名称或让编号倒退。

### 下一步

1. 继续录入代表素材并验证搜索，不再为不同风格建立复杂命名规则。
2. 若真实使用中出现同义但不同名称，不做自动合并，由设计师保留其有意义的自由命名。

### 常驻环境验收补记

- PostgreSQL 已升级到 `20260718_0018`，四个容器均为 healthy；当前 9 个已使用名称已回填占用历史。
- 真实库原有两张“课程同步”按创建时间迁移为回收站“课程同步”和当前素材“课程同步001”。
- 浏览器在上传弹窗选择测试图片后输入“课程同步”，页面准确预告“发布时将自动保存为‘课程同步002’”；输入框仍保留用户原文，取消弹窗后未发布任何测试素材。

---

## 2026-07-18：AI 私教启发式提问意图与 Meilisearch 越界修复

### 本轮目标

- 修正“通过启发式提问，还原思考过程，帮你从‘解一题’到‘通一类’”只得到 AI 私教弱候选并放行全库结果的问题。
- 保留 Meilisearch 的未知画面召回价值，但阻止它在可信卖点查询中跨越人工关系边界。

### 完成内容

- 读取真实搜索日志，确认旧查询为 `ambiguous_business_intent_search`，仅由短词“提问”产生 `AI私教答疑` 弱候选；查询理解、Embedding、Reranker 均超时。
- 核对真实关系：`ai私教`为人工 accepted `AI私教答疑/expresses`；`题型可视化`仅有 AI pending `AI私教答疑/supports`；两张极速素材只有 `极速预习复习`人工关系。
- Skill 理解层增加组合信号“启发式提问还原思考过程”指向 `ai_tutor_qa`；短词“提问”改为仅整句入口，不写入公共话术数据库。
- 新增显式 Meilisearch 干扰测试：即使外部搜索以满分返回题型可视化和两张极速素材，最终也只保留人工确认 AI 私教素材。

### 修改文件

- Skill 语言入口：`skills/understand-image-search-intent/references/public-phrase-governance.json`。
- 静态兜底边界：`taxonomy/business_intents.json`。
- 测试：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`。
- 文档：总纲 D072 与本项目日志。

### 数据迁移

- 无数据库迁移；无正式素材、公共话术或素材关系写入。

### 测试结果

- 查询理解、六体系对齐与搜索编排相关测试：`50 passed`。
- 后端全量：`156 passed`。
- Ruff、JSON 格式和 `git diff --check` 通过。
- 常驻服务使用原句复测：归一化为 `AI私教答疑`，只返回人工 accepted `AI私教答疑/expresses` 的“ai私教”1 张；总耗时 `253ms`、无超时。Meilisearch 分支仍召回 2 个候选，但均未进入最终结果。

### 遗留问题

- 常驻服务与真实数据已验证；自动化浏览器因本机 `127.0.0.1` 访问限制未完成页面点击复测，需在现有页面刷新后做一次非数据写入的界面目测。
- 其余业务真实话术继续逐条作为 Phase 0 评测样本沉淀。

### 下一步

1. 在真实页面刷新后复测原句，目测结果数量与卖点解释应为“ai私教 / AI私教答疑”且无降级提示；后端结果已确认。
2. 继续使用不同体系的真实小白话术验收；发现问题先区分“意图边界、人工关系、素材独有话术、外部弱召回”四层，不按单次结果整体关闭 Meilisearch。

---

## 2026-07-18：明确 AI 私教压过泛化薄弱点并收口匹配解释

### 本轮目标

- 修正明确出现“AI私教”后仍被“薄弱点/答疑”等泛化邻词降成待消歧，并放行全库语义结果的问题。
- 保留图片话术和语义召回的同卖点选图价值，但不向普通业务用户暴露内部算法来源。
- 澄清搜索反馈当前是运营证据，不是未经审核的在线自动学习。

### 完成内容

- 本地理解新增唯一明确主证据规则：`0.95` 卖点名称/官方功能入口可压过所有低于 `0.9` 的泛化弱候选；多个独立强卖点仍按多卖点或待消歧处理。
- 原句稳定归一为 `AI私教答疑/direct/0.95`，可信后跳过查询 Embedding 与模型理解，只允许人工 accepted `AI私教答疑/expresses|supports` 素材进入结果。
- 全链路回归显式让外部搜索满分返回动画、极速预习和极速复习干扰素材，最终仍只保留 AI 私教人工确认素材。
- 结果卡“为什么匹配”改为业务解释：人工主要表达/可以支持、卖点表达、素材独有话术；Embedding、Meilisearch、语义扩展和多路召回只保留在内部诊断。
- 核对反馈链路：`就是这张/不相关` 只写入 `search_feedback_events` 并进入搜索运营汇总，当前搜索排序不会读取它们；没有进行自动训练或自动事实改写。

### 修改文件

- 理解优先级：`backend/app/services/query_understanding_service.py`。
- 后端测试：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`。
- 前端解释：`client/src/pages/ImageHome/SemanticSearchResult/searchConceptPresentation.ts`、`ScoredImageCard.tsx` 及对应测试。
- 文档：总纲 D073 与本项目日志。

### 数据迁移

- 无数据库迁移；无正式素材、公共话术、素材话术、关系或反馈写入。

### 测试结果

- 后端定向回归：`33 passed`。
- 后端全量：`158 passed`。
- 前端定向：`6 passed`；TypeScript 与 ESLint 通过。
- Ruff、生产构建、JSON/差异检查通过。
- 常驻服务原句复测：`business_intent_search`、`AI私教答疑/direct/0.95`，只返回“ai私教”1 张；`457ms`，无超时，Embedding 与模型理解均跳过。

### 遗留问题

- 当前反馈是可审计运营数据，尚未形成受控的查询—素材排序特征；不能向用户宣称按钮会实时学习。
- 后续若接入反馈排序，必须按“归一化查询 + 卖点 + 素材组”聚合并设置最小样本/去重阈值，只影响同卖点内排序，不自动改变人工关系或话术。

### 下一步

1. 刷新真实页面复测原句，结果应只显示“ai私教”，匹配说明不再出现内部算法名。
2. 继续收集真实查询；系统性越界直接进入回归集，不要求业务方批量点击“不相关”。
3. 单独设计反馈学习 Phase：先形成离线评测和可撤销排序特征，再决定是否启用自动降权。

---

## 2026-07-18：可信卖点快速通道与外部语义降级提示校准

### 本轮目标

- 解释连续真实测试中“智能语义搜索暂时响应较慢”为何反复出现。
- 避免已经精准识别卖点并完整返回人工关系素材时，仍因可选技术分支超时误报结果不完整。
- 保留真正模糊查询的诚实降级提示，不用隐藏警告代替可用性治理。

### 完成内容

- 核对当前配置与真实搜索日志：查询理解模型为 `gpt-5.5`、查询 Embedding 为 `Qwen3-VL-Embedding-8B`、Reranker 为 `Qwen3-VL-Reranker-8B`；预算分别为 `0.9s/1.8s/1.4s`。这些外部分支在待消歧查询中多次触发硬超时，当前尚未达到稳定在线要求。
- 定位最近一次 AI 私教正确结果的黄色警告仅由 Meilisearch `202ms` 超过 `200ms` 预算触发；查询 Embedding、模型理解和 Reranker 均已跳过，实际结果并不缺失。
- 高置信本地卖点查询新增 Meilisearch 跳过规则，与既有查询 Embedding/模型理解跳过保持一致。
- 可信卖点只有 1～2 组候选时跳过 Reranker，避免为极少候选增加约 1.3 秒可选重排等待；候选较多时仍保留同卖点集合内重排。重排前剩余总预算不足以覆盖完整分支预算时也直接跳过，不再用最后几百毫秒启动一次注定失败的外部调用。
- 后台 `search_diagnostics` 继续记录全部分支超时和失败；用户级 `fallback` 只在没有可靠卖点、外部失败可能影响召回完整性时为真。可信 accepted 主通道完整时不再显示黄色误报。
- 页面提示改为说明“本次没有识别出可靠卖点，外部语义增强未在时限内完成”，不再把可选分支统称为一个看似每次必用的“智能语义搜索”。

### 修改文件

- 搜索分支与编排：`backend/app/services/search_external_branches.py`、`search_orchestrator.py`、`search_rerank_coordinator.py`、`search_diagnostics_service.py`。
- 回归测试：`backend/tests/test_phase4_search_orchestration.py`、`test_documentation_consistency.py`。
- 页面提示：`client/src/pages/ImageHome/SemanticSearchResult/index.tsx`。
- 文档：总纲 D074、本项目日志与 `docs/SEARCH_MODES_AND_AI.md`。

### 数据迁移

- 无数据库迁移；无正式素材、卖点、公共话术、素材独有话术或人工关系写入。

### 测试结果

- Phase 4 搜索编排专项在增加剩余预算回归后纳入完整测试；后端全量 `161 passed`。
- 前端 Vitest `20 passed`；TypeScript、ESLint、Ruff、生产构建和 `git diff --check` 通过。
- 后端与网页容器已重建，PostgreSQL、Meilisearch、后端和网页四个服务全部 healthy。
- 三条已校准真实业务查询复测：动画课 `201ms` 返回两张动画精讲素材；启发式 AI 私教 `116ms`、明确 AI 私教长句最终复测 `497ms`，均只返回人工关系正确素材、`fallback=false`，Meilisearch/Embedding/模型理解/Reranker 均按条件跳过。
- 无可靠卖点的模糊画面句复测为 `1916ms`：Meilisearch `196ms`、Embedding `1645ms` 成功，模型理解 `904ms` 超时，Reranker 因剩余预算不足跳过；`fallback=true`，页面保留诚实降级提示。修复前同类请求为 `2503ms` 且 Reranker 再次超时。

### 遗留问题

- 当前外部查询理解、Embedding 与 Reranker 服务仍未通过端到端 P95 验收；本轮只阻止无意义调用和误报警，没有把慢 Provider 描述成已经变快。
- 真正待消歧、纯画面和无可靠卖点查询仍可能触发外部语义超时并显示降级；后续需选择更快的在线模型/向量服务或将重型能力转为离线辅助，再做 P95 验收。

### 下一步

1. 重建常驻后端与前端，使用已测试的动画精讲、AI 私教启发式话术和明确 AI 私教话术复测，确认无黄色误报且结果边界不变。
2. 另用一条真正无可靠卖点的画面/模糊查询做故障验证，确认外部超时时仍保留诚实提示。
3. 在更多真实素材进入后单独评估快速 Embedding/Reranker 方案；未达到 P95 前不把外部语义列为稳定卖点搜索能力。

---

## 2026-07-18：Skill 渐进式两层意图理解

### 本轮目标

- 先只判断六大体系，再按需读取候选体系卖点，避免每次把 Skill 全部内容塞给模型。
- 配置模型时让“模型 + Skill”成为查询意图主判断，本地目录只保留封闭约束和失败兜底。
- 不改变六体系、16 卖点、公共话术与人工素材关系边界。

### 完成内容

- 新增第一层 `SYSTEM_ROUTER_RULES.md` 与第二层 `SELLING_POINT_ROUTER_RULES.md`；前者不含卖点，后者只能返回候选体系目录中的稳定 code。
- 后端新增 `search_system_routing` 结构协议；体系候选限制为单主体系、最多一个相邻候选，真多体系最多三个，纯画面/无可靠体系不调用第二层。
- Skill loader 改为按候选体系抽取单个 `runtime-intent` 摘要；只有多体系时才加载跨体系校准。旧全量搜索 Prompt 构造被显式禁止。
- 第二层目录只投影候选体系内数据库 active 卖点；模型跨体系返回会被拒绝。缓存加入渐进式 Prompt 版本。
- 搜索编排在模型成功时用模型卖点集合替换本地候选，不再合并出极速预习、动画精讲等无关弱卖点；模型失败后仍回退本地目录。
- 查询理解预算由 `0.9s` 调整为 `15s`，避免每次尚未完成第一层就降级。全局关键词/Embedding 仍不能突破可信卖点 accepted 关系集合。

### 修改文件

- Skill 与协议：`skills/understand-image-search-intent/`、`backend/app/ai/contracts.py`、`backend/app/schemas/ai.py`、`backend/app/ai/skill_loader.py`。
- 运行时：`backend/app/services/ai_service.py`、`ai_knowledge_service.py`、`query_understanding_service.py`、`search_external_branches.py`、`search_orchestrator.py`。
- 配置、测试和文档同步更新。

### 数据迁移

- 无数据库迁移；无正式素材、卖点、公共话术、素材话术或人工关系写入。

### 测试结果

- 第一层 Prompt 约 `1246` 字符；同步自学单体系第二层约 `2935` 字符，且测试确认没有其他体系卖点。
- 后端全量 `165 passed`；Ruff、Skill `quick_validate`、`git diff --check` 通过。
- 开发代理未向第三方模型地址发送私有项目 Prompt；GPT-5.5 两层真实耗时等待常驻页面验收。

### 遗留问题

- 两次顺序模型调用的总耗时和结构输出稳定性尚未通过真实 P95；`15s` 仅是保证实际使用的分支上限。
- 常驻容器需重建后再用六类代表话术确认 `query_understanding=ok`，并观察是否仍出现降级。

### 下一步

1. 重建常驻服务并在当前页面测试动画精讲、AI 私教、极速预习复习、真人督学、纯画面和真多卖点。
2. 记录两层合计耗时、命中体系、命中卖点和最终素材边界。
3. 若 GPT-5.5 仍超过 15 秒，保留两层 Skill 结构，单独选择更快的查询理解模型或增加体系路由缓存。

---

## 2026-07-18：纠正 Skill 第二层摘要化

### 本轮目标

- 保留先判体系、再按候选体系加载的渐进结构。
- 纠正把“按需读取”误做成“读取摘要”：命中的体系必须完整进入第二层判断。
- 不改六体系、16 个卖点、证明点、边界、公共话术或人工素材关系。

### 完成内容

- 删除临时第二层精简规则 `SELLING_POINT_ROUTER_RULES.md`；第一层 `SYSTEM_ROUTER_RULES.md` 保持不变。
- 第二层改为完整读取 `RULES.md` 和每个候选体系的完整 `references/sync-*.md`；候选超过一个时完整读取跨体系校准文件。
- 移除后端 `runtime-intent` 摘要抽取路径；按需加载现在只减少无关体系，不再压缩命中体系知识。
- Skill 和输出协议增加硬约束：命中体系后不得只读取摘要、关键词或局部段落。

### 修改文件

- `backend/app/ai/skill_loader.py`
- `backend/tests/test_taxonomy_catalog.py`
- `skills/understand-image-search-intent/SKILL.md`
- `skills/understand-image-search-intent/RULES.md`
- `skills/understand-image-search-intent/references/output-contract.md`
- 当前决策、搜索说明和后端说明文档。

### 数据迁移

- 无数据库迁移；无图片、卖点、话术或人工关系写入。

### 测试结果

- 第一层约 `1246` 字符；静态目录下同步自学单体系第二层约 `12254` 字符，规划+伴学双体系约 `18630` 字符。
- 自动化测试确认单体系 Prompt 包含完整业务原文、证明点、边界、意图用例与待确认内容，同时不加载其他体系或跨体系文件。
- 后端全量 `165 passed`；Ruff、Skill `quick_validate` 和 `git diff --check` 通过。
- Docker 镜像已重建；PostgreSQL、Meilisearch、后端和网页四个服务全部 healthy，容器内定向回归 `7 passed`。

### 遗留问题

- 完整候选体系知识会增加第二层 Prompt 体量；这是本轮明确选择的正确性优先行为，后续只能通过更准确的第一层路由或模型上下文能力优化，不能再次偷换为摘要。
- GPT-5.5 两层真实端到端质量和 P95 仍需用户明确允许发送项目 Skill 内容后验收。

### 下一步

1. 完成后端全量回归、Ruff、Skill 校验与差异检查。
2. 重建常驻容器并确认健康。
3. 经用户允许后，用真实模型复测六类代表查询并记录两层耗时和最终素材边界。

---

## 2026-07-18：修复两层模型共用超时导致的全库误召回

### 本轮目标

- 修复“一键拍照后思路点拨、拒绝直接给答案”应归 AI 拍题精学，却因模型超时返回全部素材的问题。
- 保留完整 Skill 和六体系/16 卖点边界，不通过再次摘要化换速度。
- 让外部语义真正完成时参与判断；未完成时宁可安全返回空，也不冒充精准结果。

### 完成内容

- 用当前 Provider 独立测得体系路由约 `4.906s`、完整同步自学卖点识别约 `13.337s`，确认旧 `15s` 外层预算小于两层真实合计耗时。
- 将体系路由、卖点识别拆为独立 `8s/20s` 预算；模型请求本身同步使用对应 HTTP 超时。旧单调用兼容预算调整为 `30s`。
- 新增分层结果状态：第一层成功、第二层失败/超时时保留“已确认业务体系”事实并启用精度保护；没有可信本地卖点关系时清空全局候选，不再返回全部图片。
- Reranker 的可选总预算改从查询理解完成后开始，Embedding/Reranker 分支预算按当前实测余量调整为 `2.5s/2s`。
- 只在 Skill 理解层为 `photo_guided_learning` 增加“拒绝直接给答案/思路点拨”信号；公共话术、体系、卖点和人工素材关系均未改动。
- 页面在精度保护空结果时明确提示“没有放开全库结果”，不再误称已经展示基础结果。

### 修改文件

- 模型与分层理解：`backend/app/ai/contracts.py`、`openai_compatible.py`、`backend/app/services/ai_service.py`、`query_understanding_service.py`、`search_external_branches.py`。
- 搜索编排：`search_models.py`、`search_service.py`、`search_orchestrator.py`、配置与依赖注入。
- 页面、测试与治理：搜索结果页、Phase 4 回归、Provider 回归、公共话术治理中的理解信号。
- 配置和文档：Docker 环境样例、Compose、搜索说明、总纲 D077 与本日志。

### 数据迁移

- 无数据库迁移；无图片、卖点、公共话术、素材独有话术或人工关系写入。

### 测试结果

- 已新增独立分层预算、第二层超时精度保护、Reranker 预算起点、当前真实话术唯一归类和 Provider 请求级超时回归。
- 定向测试、全量测试、容器重建和浏览器真实复测结果在本轮完成后补充。

### 遗留问题

- 两层模型真实总耗时仍高于普通本地搜索，后续需要缓存和 P95 评测；不能再次通过精简已命中体系知识规避耗时。
- 如果第一层自身也失败，系统仍无法确定查询是业务意图还是纯画面，只能使用本地高置信理解或普通降级；需持续观察第一层 `8s` 预算命中率。

### 下一步

1. 完成后端/前端全量回归、Skill 校验与差异检查。
2. 重建常驻容器并确认配置生效。
3. 用本轮真实句复测：期望只返回已审核 AI 拍题精学素材；若当前没有该关系，则返回空，不得出现极速预习复习或其他全库素材。

---

## 2026-07-18：启发式提问话术归属校正为拍题精学（D078）

### 本轮目标

- 修正 D072 的归属错误：真实查询“通过启发式提问，还原思考过程，帮你从‘解一题’到‘通一类’”被识别为 `AI私教答疑` 并返回“ai私教”素材；用户明确该话术描述的是 AI 拍题精学的“苏格拉底式提问”方法论，当前库中没有对应素材，正确结果应为空。

### 完成内容

- Skill 理解层信号“启发式提问还原思考过程”从 `ai_tutor_qa` 移到 `photo_guided_learning`，与既有“拒绝直接给答案、思路点拨”并列；治理文件版本升级到 `2026-07-18.4`，运行时目录指纹变化使旧模型理解缓存自动失效。
- 同步自学体系文件更新：拍题精学搜索语言加入“启发式提问、还原思考过程、从‘解一题’到‘通一类’”；`ai_tutor_qa` 与 `photo_guided_learning` 的识别边界及运行时摘要写明该方法论话术即使不带“拍题”字样也归拍题精学；意图用例表新增该原句。
- 本地理解回归改为期望 `AI拍题精学`；新增全链路回归：该查询在只有 AI 私教 accepted 素材、没有拍题精学素材时必须返回空结果，不得回退其他卖点素材补位。

### 修改文件

- Skill 语言入口：`skills/understand-image-search-intent/references/public-phrase-governance.json`。
- 体系知识：`skills/understand-image-search-intent/references/sync-self-study.md`。
- 测试：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`。
- 文档：总纲 0.37 / D078 与本项目日志。

### 数据迁移

- 无数据库迁移；无公共话术、素材或关系写入。

### 测试结果

- 后端全量：`169 passed`。

### 遗留问题

- 拍题精学当前没有人工 accepted 素材，该查询返回空是正确的素材缺口暴露；补充拍题精学代表素材后需复测。
- 浏览器页面复测待用户刷新后确认：期望顶部卖点为“AI拍题精学”且结果为空，不再出现“ai私教”。

### 下一步

1. 页面刷新后用原句复测，确认识别卖点与空结果。
2. 设计师补充拍题精学代表素材并确认“主要表达”关系后，再次绑定该查询作为评测用例。

---

## 2026-07-19：无对象拍照+讲解组合固定为探索型双卖点（D079）

### 本轮目标

- 修复“拍一下，AI马上给你讲解”无可靠卖点后放行全库 11 张素材的问题。
- 修复“一键拍照，AI 即刻为你提供思路点拨与详细解析，拒绝直接给答案”被硬路由为拍题精学单卖点后，因无素材返回空、极速预习/复习素材无法出现的问题。

### 完成内容

- 按用户校准确立规则：拍照入口没有说明拍摄对象时，“拍完就讲”既可能是拍题精学也可能是极速预习复习，输出探索型覆盖两个卖点并合并人工 accepted 素材。
- `public-phrase-governance.json` 新增 `explorationSignals`（入口词 拍照/拍一下/一拍/随手拍 × 目的词 讲解/解析/点拨/马上讲/给你讲/即刻讲 → `photo_guided_learning` + `rapid_preview_review`），版本升至 `2026-07-19.1`，旧理解缓存自动失效。
- `runtime_intents.py` 加载组合信号；`query_understanding_service.py` 在没有 `0.9` 以上单卖点证据时优先输出探索型双候选（`0.88` direct），负向表达仍可排除候选。
- 同步自学体系文件补充组合入口边界与两条意图用例；“拍题后分步点拨”“不会立即出答案”等官方表达仍收敛单卖点，“AI拍照”整句仍是四卖点探索。
- 更新 D077 相关的两条全链路/理解回归为探索型预期，新增“真实库只有极速素材时返回极速预习/复习而非空或全库”的回归。

### 修改文件

- Skill 治理与知识：`skills/understand-image-search-intent/references/public-phrase-governance.json`、`references/sync-self-study.md`。
- 运行时目录与理解：`backend/app/domain/runtime_intents.py`、`backend/app/services/query_understanding_service.py`。
- 测试：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`、`backend/tests/test_skill_selling_point_alignment.py`。
- 文档：总纲 0.38 / D079 与本项目日志。

### 数据迁移

- 无数据库迁移；无公共话术、素材或关系写入。

### 测试结果

- 后端全量：`171 passed`；变更文件 Ruff 通过；治理 JSON 校验通过。

### 遗留问题

- 组合信号当前只覆盖“拍照×讲解”一族；后续真实话术若暴露其他共享组合（如“拍照×归档”），按同一机制在治理层扩展，不逐句写死代码。
- 查询理解模型（GPT-5.5）第一层体系路由在 `8s` 预算内仍频繁超时，探索型当前主要依赖本地组合信号兜底；模型侧知识已同步，待更快 Provider 后复测模型主判断。

### 下一步

1. 重启常驻服务后用两句原话复测：期望“拍一下，AI马上给你讲解”“一键拍照…拒绝直接给答案”都返回极速预习/极速复习素材并提示“你可能在找”。
2. 补充拍题精学代表素材后复测，确认两个卖点素材合并展示且排序合理。

---

## 2026-07-19：待审核关系退出搜索，探索型候选封闭已确认关系（D080）

### 本轮目标

- 修复 D079 复测中“考前突击”混入“拍一下，AI马上给你讲解”探索结果的问题。
- 按用户硬规则落地：AI 关系建议在人工确认（accepted）之前不参与任何搜索环节。

### 完成内容

- 定位根因一：“考前突击”仅有一条 AI 待审核“表达极速预习复习”建议，但三处搜索投影都让 pending 关系参与——概念召回给 `0.62/0.7` 弱分、Meilisearch 可搜索字段含 `pendingConceptNames`、重排/向量文档含“AI待审核概念”行。
- 定位根因二：模型把探索候选标为 `related/0.7、0.66`，低于可信通道 `direct + 0.85` 门槛，探索型查询退回全库融合，绕过“只认 accepted `expresses/supports`”过滤。
- 概念召回打分对非 accepted 关系一律 0 分；Meilisearch 可搜索字段与索引文档删除 `pendingConceptNames`（`pendingAiConceptCodes` 仅保留为运营过滤字段）；重排/向量共用文档删除“AI待审核概念”行。
- 探索型理解（`exploratory_business_intent_search`）的候选卖点无论模型标注 relation/权重如何都进入可信通道，结果封闭在候选卖点人工 accepted 关系内合并；候选内无素材即空结果，不放行全库。
- 总纲废止第 10 节旧原则第 7 条“AI 待审核关系仅作弱召回弱排序信号”，审核待办/运营统计/管理页展示不受影响。

### 修改文件

- 搜索链路：`backend/app/services/concept_search_recall.py`、`backend/app/services/search_concept_routing_service.py`、`backend/app/services/meilisearch_client.py`、`backend/app/services/search_index.py`、`backend/app/services/image_semantic_profile_service.py`。
- 测试：`backend/tests/test_phase4_search_orchestration.py`（新增模型 related 低权重探索候选下 pending 关系与标题巧合均不得进入的全链路回归）、`backend/tests/test_search_index.py`。
- 文档：总纲版本 `1.45`、0.39 / D080、第 10 节排序原则、0.15 Meilisearch 字段描述与本项目日志。

### 数据迁移

- 无数据库迁移。重排/向量文档内容变化会在下次分析/索引刷新时自然重建，无需一次性刷库。

### 测试结果

- 后端全量：`172 passed`；变更文件 Ruff 通过。
- 常驻服务重启后复测两句真实话术：均为探索型“你可能在找：AI拍题精学、极速预习复习”，结果只返回“极速预习”（人工 accepted），“考前突击”不再出现。

### 遗留问题

- “考前突击”的“表达极速预习复习”AI 建议仍处于待审核，建议负责人在管理页驳回（该图核心是考前冲刺，不是拍照+讲解）；驳回与否均不再影响搜索结果。
- 模型对探索候选统一标 `related` 属于诚实表达，现由链路层兜住；如后续输出契约把探索候选权重规范化，可再简化路由判断。

### 下一步

1. 负责人审核“考前突击”素材上的待审核关系建议。
2. 补充拍题精学代表素材后复测探索型合并展示。

---

## 2026-07-19：16 卖点真实素材准确性基线（D081）

### 本轮目标

- 在每个稳定卖点都有人工确认代表素材后，重新建立 Phase 0 真实业务准确性基线。
- 把意图识别、图片关系命中、多卖点覆盖、范围泄漏、人工排除关系与外部 AI 可用性拆开评估。

### 完成内容

- 运行库确认六大体系 16 个卖点全部至少有 1 张已发布、人工 accepted `expresses` 素材；共读取 55 条人工 accepted `expresses/supports` 发布关系。
- 评测脚本默认扩展到第 5 批 103 条用例，并从运行数据库按稳定卖点 code 动态加载人工 `expresses/supports/excludes` 金标准；不再用标题、搜索解释或 AI 待审核建议代替正确素材关系。
- 新增业务数据就绪度、意图命中、Top 3 主表达、Top 5 全卖点覆盖、逐卖点指标、范围泄漏、人工 excludes 违规、Fallback、超时和 P95 汇总；支持只输出摘要。
- 本地可用链路在 95 条业务用例上达到意图 `95/95`、Top 3 `94/95`、Top 5 全卖点覆盖 `91/95`，业务空结果与人工 excludes 违规均为 0，P95 `642.44ms`。
- 定位 `SE094` 学情报告排第 4；`SE054/SE058/SE095/SE096` 未在 Top 5 覆盖全部卖点；`SE020/SE021/SE028/SE035/SE050` 因待消歧放行目标人工关系集合外素材。
- 带 AI 配置的全量运行中 23 条外部依赖用例全部降级。解除执行环境网络限制后抽样仍为 GPT-5.5/DeepSeek 调用失败、Kimi 403，且单条等待数分钟，因此停止重复故障调用；本轮没有可声明的 AI 精度或 AI P95。

### 修改文件

- 评测脚本：`backend/scripts/run_search_eval.py`。
- 机器报告：`docs/PHASE0_SEARCH_EVAL_REPORT_2026-07-19_LOCAL.json`、`docs/PHASE0_SEARCH_EVAL_REPORT_2026-07-19_AI.json`。
- 人读报告：`docs/PHASE0_SEARCH_EVAL_SUMMARY_2026-07-19.md`。
- 文档：总纲版本 `1.46`、0.1 / D081 / 下一步，以及本项目日志。

### 数据迁移

- 无数据库迁移；无素材、人工关系、公共话术或评测金标准写入数据库。

### 测试结果

- 评测数据校验：第 5 批共 `103` 条。
- `backend/tests/test_search_eval.py`：`7 passed`。
- `backend/scripts/run_search_eval.py`：Ruff 通过。
- 真实数据库本地全量评测完成并保存报告。

### 遗留问题

- `learning_report` 只有 1 张主表达素材，多卖点查询中容易被其他卖点的多张素材挤到第 6；需调整多卖点代表结果配额或排序。
- `SE096` 的极速预习复习 + 课后小测明确双需求只返回前者，是当前最明确的召回缺陷。
- 5 条范围泄漏中有 2 条明确边界问题、3 条需要先复核业务金标准或人工支持关系，禁止在未确认前批量扩词。
- 8 条纯画面/无可靠意图用例尚无画面级真实素材绑定，数据集总状态继续为 `partial`。
- 外部 Provider 可用性未通过，不能用全量降级报告宣称 AI 精度。

### 下一步

1. 优先修复 `SE096` 和 `SE094`，复测 Top 3 与 Top 5 全卖点覆盖。
2. 对 `SE020/SE028` 收紧可信本地意图；先业务复核 `SE021/SE035/SE050` 再决定修改理解还是人工关系。
3. 修复 Provider 配置/权限后重跑完整 AI 链路，并单独记录成功率、Fallback 率与端到端 P95。

---

## 2026-07-19：Kimi → DeepSeek → GPT-5.5 降级链贯通（D082）

### 本轮目标

- 让已有 Kimi、DeepSeek、GPT-5.5 配置真正按 Kimi → DeepSeek → GPT-5.5 自动降级。
- 修复模型链已经返回结果但搜索外层或浏览器先超时的问题，并完成工程与真实页面走查。

### 完成内容

- 定位原配置实际顺序为 `primary → fallback1 → fallback2`，与用户期望相反；新增 `MODEL_PROVIDER_ORDER`，以逻辑槽位声明顺序，当前本地为 `fallback2,fallback1,primary`。不移动密钥，不把密钥写入代码或日志。
- Provider 工厂按显式顺序组装已配置模型；非法/重复槽位被忽略，未显式列出的合法槽位仍追加为最终后备。自动降级链公开实际尝试数。
- 搜索体系路由和卖点识别外层预算按 Provider 尝试数扩展；单模型请求仍分别受 `8s/20s` 预算约束，避免前一个模型耗尽整条链。
- 前端语义搜索请求预算单独改为 `120s`。旧 `30s` 通用预算曾在后端 `30.036s` 成功返回 4 张图时先抛出 Axios 超时，随后页面误走普通列表查询并显示 0 张。
- 抽样连通性确认：Kimi 当前返回 `403`；DeepSeek 最小 JSON 请求成功；GPT-5.5 独立请求成功。真实页面冷查询在 Kimi/DeepSeek 失败后由 GPT-5.5 完成，`27.915s` 返回 4 张“AI定制学习方案”素材，无用户级降级或超时。
- 103 条不外发的本地全量评测复跑：95 条业务用例意图 `95/95`、Top 3 `94/95`、Top 5 全卖点 `91/95`、业务空结果 0、人工 excludes 违规 0，P95 `504.35ms`。

### 修改文件

- Provider 与配置：`backend/app/ai/factory.py`、`backend/app/ai/fallback.py`、`backend/app/core/config.py`、`backend/app/api/dependencies.py`、`backend/.env`、`.env.docker.example`、`docker-compose.yml`。
- 前端请求：`client/src/api/image.ts`。
- 测试：`backend/tests/test_ai_provider.py`。
- 评测与文档：`docs/PHASE0_SEARCH_EVAL_REPORT_2026-07-19_LOCAL.json`、`docs/PHASE0_SEARCH_EVAL_SUMMARY_2026-07-19.md`、总纲 0.40 / D082 与本项目日志。

### 数据迁移

- 无数据库迁移；不修改素材、人工关系、公共话术、素材话术、六大体系或 16 个卖点。

### 测试结果

- 后端全量：`175 passed`；专项 Provider/搜索编排：`31 passed`；Pyright 与 Ruff 通过。
- 前端：`20 passed`；TypeScript、ESLint、生产构建通过。
- `docker compose config --quiet` 与 `git diff --check` 通过。
- 真实页面冷查询返回 4 张图，诊断 `fallback=false`、`timedOut=false`。

### 遗留问题

- Kimi 当前凭据返回 `403`，需要在 Provider 侧修复权限或更换有效密钥；自动降级已保证它不阻断搜索。
- 103 条真实 AI 批量评测会向三家外部 Provider 发送业务搜索语句，本次执行未取得单独数据外发授权，未运行修复后的全量 AI 报告；修复前历史全量降级报告仅作故障对照。
- 本地准确性仍有 `SE094` Top 3 排序、`SE054/SE058/SE095/SE096` Top 5 多卖点覆盖和 5 条范围过宽问题，属于下一轮质量调优。

### 下一步

1. 修复 Kimi `403` 凭据并复测首选模型。
2. 取得 103 条业务语句外发授权后运行完整 `--with-ai` 评测，统计各模型成功率、Fallback 率与端到端 P95。
3. 优先调优 `SE096` 双卖点合并和 `SE094` 学情报告排序。

---

## 2026-07-19：三模型真实全量评测完成（D083）

### 本轮目标

- 在用户明确同意数据外发后，用 103 条完整数据验证 Kimi → DeepSeek → GPT-5.5 真实在线链路的准确性、降级与时延。
- 区分“自动降级可以运行”“模型理解正确”和“最终素材仍被本地关系兜住”，不再用单条成功代替全量验收。

### 完成内容

- 按当前生产装配运行第 1～5 批共 103 条 `--with-ai` 评测，机器报告确认 `withAi=true`、`caseCount=103`、95 条业务用例全部具备人工 accepted 金标准。
- AI 链路业务指标：意图全部命中 `59/95`、Top 3 主表达 `92/95`、Top 5 全卖点 `86/95`、声明查询类型命中 `44/54`；人工 excludes 与禁止词违规均为 0。
- 可用性：查询理解分支 `91 ok / 7 failed / 5 timed_out`；用户级 Fallback 5 条，任一分支超时 6 条；端到端 P50 `22.741s`、P95 `50.912s`、最大 `80.152s`，查询理解自身 P95 `50.540s`。
- 对照本地同批数据：意图 `95/95`、Top 3 `94/95`、Top 5 `91/95`、业务空结果 0、P95 `0.504s`。当前三模型主判断在准确性和延迟上都没有通过验收。
- 三条 AI 新增业务空结果：`SE041`“找不到提分重点”、`SE045`“孩子学习不走弯路”、`SE048`“学习过程不是黑盒”。AI 还使 `SE057`“拍题”和 `SE092`“AI拍照”的探索候选被缩窄；可信范围从本地 5 条泄漏增至 8 条。
- 模型意图最弱卖点：真人老师督学 `0/10`、极速预习复习 `1/8`、AI 错题本 `2/10`、AI 私教答疑 `2/8`。最终 Top 3 仍达 `92/95` 主要是本地召回和人工 accepted 关系兜底，不等于模型理解合格。
- 本轮不改变现有 D075 模型主判断代码，先记录真实差异。当前报告只记录查询理解分支状态，没有记录成功响应具体来自 DeepSeek 还是 GPT，不推测各 Provider 成功率。

### 修改文件

- 当前 AI 机器报告：`docs/PHASE0_SEARCH_EVAL_REPORT_2026-07-19_AI.json`。
- 人读对比报告：`docs/PHASE0_SEARCH_EVAL_SUMMARY_2026-07-19.md`。
- 文档：总纲版本 `1.48`、0.1 / 0.41 / D083 / 下一步，以及本项目日志。

### 数据迁移

- 无数据库迁移；无素材、人工关系、公共话术、素材话术或评测金标准写入。

### 测试结果

- 真实三模型全量评测命令正常退出，报告 `withAi=true`、103 条齐全。
- 分支统计、弱例清单和本地/AI 对比均从机器报告重新计算，不以运行警告条数推测成功率。

### 遗留问题

- 当前模型无条件覆盖本地可信理解会引入三条业务空结果并显著降低意图命中；需设计仲裁规则后才能继续作为在线主判断。
- Kimi 当前持续失败；DeepSeek 在完整 Prompt 下不稳定；GPT 承担主要后备但也存在少量失败。
- 缺少每次实际成功 Provider、各级耗时和错误类型遥测，暂时只能统计整条查询理解分支，不能给出三家分别成功率。
- 本地基线原有 `SE096` 多卖点合并和学情报告排序仍需单独调优，不能把所有失败都归因于 Provider。

### 下一步

1. 新增决策覆盖 D075：本地强证据不得被模型降级为无可靠意图或删除候选，模型只补本地缺口/真实歧义。
2. 增加 Provider 级尝试遥测，并修复 Kimi `403`。
3. 用同一 103 条复测，要求不低于本地 Top 3 `94/95`、Top 5 `91/95`、业务空结果 0，并重新限制在线 P95。

---

## 2026-07-20：三层角色约束与具体图片条件门槛（D084）

### 本轮目标

- 在不改变六大体系、16 个核心卖点、人工素材关系和搜索服务架构的前提下，补强体系判断、卖点判断和具体图片判断的决策约束。
- 修复“一键拍照，AI 即刻提供思路点拨与详细解析，拒绝直接给答案”返回苏格拉底方法图、却没有稳定保证拍题精学和极速预习入口图的问题。

### 完成内容

- 第一层体系路由增加专属系统角色、证据优先级和禁止事项：按对象、主动作、时间尺度、目的、执行主体判断，不得提前输出卖点或具体图片。
- 第二层卖点理解增加专属系统角色和对象/主动作、目的结果、方法证明的顺序；通用结果词和方法细节不得覆盖主入口证据，理由必须指出独立原话证据。
- Prompt 缓存版本升级为 `2026-07-20.three-layer-evidence-v1`，避免旧模型理解缓存继续复用。
- 新增独立 `AssetSelectionPolicyService`，第三层仍只在人工 accepted `expresses/supports` 集合内工作，不新增生成式图片裁判或额外模型调用。
- `taxonomy/search_policy.json` 增加可版本化 `asset_specificity_gates`。首条规则为拍题精学下的苏格拉底方法素材设置显式方法门槛；业务词不写进路由服务或总编排器。
- 探索型/真多卖点结果先按 active 卖点各保留一张最佳素材，再追加同卖点证明图，保证卖点覆盖优先于单卖点细节堆叠。
- 同步自学知识文件和第三层输出协议补充入口素材、补充素材、条件素材和排除素材的边界。

### 修改文件

- 模型与 Skill：`backend/app/ai/openai_compatible.py`、`backend/app/ai/skill_loader.py`、`skills/understand-image-search-intent/SYSTEM_ROUTER_RULES.md`、`RULES.md`、`references/output-contract.md`、`references/sync-self-study.md`。
- 图片选择策略：`backend/app/domain/search_policy.py`、`backend/app/services/asset_selection_policy_service.py`、`backend/app/services/search_concept_routing_service.py`、`taxonomy/search_policy.json`。
- 测试：`backend/tests/test_ai_provider.py`、`test_taxonomy_catalog.py`、`test_phase4_search_orchestration.py`、`test_architecture.py`。
- 文档：总纲版本 `1.49`、0.42 / D084 与本项目日志。

### 数据迁移

- 无数据库迁移；未修改或写入现有素材、素材独有话术、公共话术、人工关系或 AI 待审核建议。
- 未重启、重建或修改当前常驻服务。

### 测试结果

- 角色与选图专项：`41 passed`。
- 相邻搜索理解/召回回归：`48 passed`。
- 后端全量：`179 passed`。
- 变更文件 Ruff 与 `git diff --check` 通过；路由服务 199 行，独立图片策略服务 101 行，架构体量护栏通过。

### 遗留问题

- 本轮不覆盖 D075 的模型/本地仲裁；三模型在线主判断准确性和时延仍以 D083 为准，不能因 Prompt 增强宣称已经通过全量 AI 评测。
- 条件图片门槛目前只有本次业务确认的苏格拉底方法一条。后续必须根据真实误差逐条增加，并保持配置化、可评测，不得预先堆砌规则。
- 常驻服务与真实页面尚未在本轮重启复测；源码回归已通过，页面验收留到用户允许操作服务时执行。

### 下一步

1. 在不改素材关系的前提下，用真实页面分别复测通用“一键拍照”话术和明确“启发式提问”话术。
2. 继续用真实具体图片误差校准条件门槛，优先补齐评测用例，不批量改写业务体系。
3. 单独设计覆盖 D075 的本地强证据/模型仲裁，并用同一 103 条全量回归后再决定是否上线。

---

## 2026-07-20：方法谓词优先与本地强证据仲裁（D085）

### 本轮目标

- 修复“通过启发式提问，还原思考过程，帮你从解一题到通一类”被识别为“万能解法”的真实错误。
- 在不改变六大体系、16 个卖点、人工素材关系和服务架构的前提下，让句法证据、卖点判断和具体图片选择保持一致。

### 完成内容

- 搜索日志对照确认：模型超时时本地规则返回“同步自学体系 > AI拍题精学”，模型 `ok` 后约 `23s` 返回“同步培养体系 > 万能解法”并覆盖本地结果；根因位于查询理解仲裁，不是苏格拉底图片话术或第三层条件门槛。
- 第一层、第二层和同步自学知识统一增加句法角色规则：“通过/借助/采用 X，帮你/从而 Y”以 X 为核心手段/方法谓词，以 Y 为结果，不能只抓“通一类”等结果词改判体系或卖点。
- `QueryUnderstandingService` 增加本地强证据/模型仲裁：高置信直接单卖点、真多卖点和探索型候选已经闭合时跳过模型；模型只补本地无候选、弱候选和真实歧义。缓存或边缘路径中的冲突模型结果仍由同一服务拒绝。
- 外部分支增加“本地高置信业务证据已满足，无需模型补充”诊断；总编排器只消费仲裁后的封闭候选，不包含业务词特判。
- Prompt 缓存版本升级，防止旧错误模型理解复用。
- 新增端到端回归：即使模型被设置为错误返回“万能解法”，该句也只返回“AI拍题精学”下的苏格拉底图；数据库新增可信表达后，旧模型缓存同样不能覆盖本地判断。

### 修改文件

- 查询理解与编排：`backend/app/services/query_understanding_service.py`、`search_external_branches.py`、`search_orchestrator.py`。
- 模型角色与缓存：`backend/app/ai/openai_compatible.py`、`skill_loader.py`。
- Skill：`skills/understand-image-search-intent/RULES.md`、`SYSTEM_ROUTER_RULES.md`、`references/sync-self-study.md`。
- 测试：`backend/tests/test_phase4_search_orchestration.py`。
- 文档：总纲版本 `1.50`、0.43 / D085 与本项目日志。

### 数据迁移

- 无数据库迁移；无素材、人工关系、公共话术或评测金标准写入。

### 测试结果

- 目标句与苏格拉底边界专项：`3 passed`。
- Phase 4 搜索编排回归：`28 passed`。
- 查询状态与业务意图回归：`30 passed`。
- 后端全量：`180 passed`。
- 文档、架构与目录护栏：`33 passed`；Ruff 与 `git diff --check` 通过。
- 103 条本地优先评测：95 条业务卖点识别 `95/95`、Top 3 `94/95`、Top 5 全卖点覆盖 `94/95`、声明查询类型 `54/54`，P95 `365.87ms`，无 Fallback 或超时。

### 遗留问题

- 尚需用同一 103 条用例复测 D085 后的端到端准确率和只在缺口/歧义查询中发生的模型 P95。
- Provider 级成功来源、各级耗时和错误类型遥测仍待补齐；Kimi `403` 未在本轮处理。
- 当前常驻后端不是热加载进程。真实页面已显示“AI拍题精学”及“拍题精学/苏格拉底讲解提问”两张图，但日志证明仍是旧进程等待模型约 `24s` 超时后的本地回落；本轮重启申请受工具审批额度限制未执行，不能把该页面结果记作 D085 新快路径已加载。

### 下一步

1. 在当前真实页面复测本句，确认卖点为 AI 拍题精学且苏格拉底图进入结果。
2. 用同一 103 条评测集回归本地优先策略，并单独统计实际触发模型的弱候选/歧义用例。
3. 补 Provider 级遥测与 Kimi 鉴权问题，不把模型调用成功等同于业务判断正确。

---

## 2026-07-20：图片话术主筛选与证明素材条件准入（D086）

### 本轮目标

- 修复 AI 定制学习方案查询正确命中卖点后，仍把两张只作支撑的新课标创始人图片一并返回的问题。
- 在不改变六大体系、16 个卖点、人工素材关系和服务架构的前提下，让每张图片的已采纳话术真正承担第三层筛选职责，标题和画面内容只作辅助。

### 完成内容

- 真实日志确认目标查询返回 4 张，匹配理由没有任何“卖点内素材独有话术命中”；原句与四组 accepted 图片话术的最高字符相似度仅为 `0.175 / 0.140 / 0.075 / 0.074`，全部低于旧阈值 `0.58`。
- 数据库确认前两张“ai定制、ai定制规划”为人工 accepted `expresses`，后两张“创始人理念、创始人宣讲”仅为人工 accepted `supports`，且其 accepted 图片话术都在讲新课标、考试改革和发布会。
- 第三层改为两阶段选择：先收集当前卖点的人工 accepted 关系候选并识别是否存在 `expresses`；再用 accepted 图片话术执行候选内主筛选。话术比较上下文扩展为原句、标准化意图、可信扩展词、搜索意图和卖点名，不再只比较两条完整长句。
- 标题、语义总结、Semantic Profile V3 的画面事实与场景只提供辅助匹配；OCR、旧 `content_tags`、人工风格/场景筛选属性和 pending/rejected 图片话术不成为准入事实。
- 某卖点已有 `expresses` 时，只有 `supports` 的证明图必须命中 accepted 图片话术或得到标题/画面辅助证据，否则退出；某卖点没有 `expresses` 时保留 accepted `supports` 作为可信库存保底。
- 真实运行库使用固定模型理解复测同一句只返回“ai定制、ai定制规划”，两张创始人图退出；明确查询“创始人宣讲”时，辅助标题证据可以开放对应证明图。
- 用户明确同意后停止旧 PID `72430`，以新 PID `67486` 启动后端并通过 `/health`。真实浏览器目标句返回 2 张产品图，日志为 `result_count=2`、无超时/无 Fallback；“启发式提问”和通用“一键拍照”分别在 `227ms/179ms` 返回正确两张素材，查询理解、Embedding、Meilisearch 与 Reranker 均按高置信主通道跳过。

### 修改文件

- 第三层策略与文本证据：`backend/app/domain/asset_text_relevance.py`、`backend/app/domain/search_policy.py`、`backend/app/services/asset_selection_policy_service.py`、`backend/app/services/search_concept_routing_service.py`、`taxonomy/search_policy.json`。
- 回归：`backend/tests/test_phase4_search_orchestration.py`。
- Skill 与执行文档：`skills/understand-image-search-intent/SKILL.md`、`references/output-contract.md`、`docs/DEVELOPMENT_GUARDRAILS.md`、`docs/SEARCH_MODES_AND_AI.md`、总纲 0.1 / 0.44 / D086 / 下一步与本项目日志。

### 数据迁移

- 无数据库迁移；无素材、素材独有话术、人工关系、公共话术或评测金标准写入。

### 测试结果

- 第三层目标与相邻边界专项：`7 passed`。
- Phase 4、查询意图、架构与目录回归：`89 passed`。
- 后端全量：`182 passed`；变更文件 Ruff 通过。
- 103 条本地评测：95 条业务卖点识别 `95/95`、Top 3 `94/95`、Top 5 全卖点覆盖 `94/95`、查询类型 `54/54`，P95 `381.78ms`，无 Fallback 或超时。

### 遗留问题

- 当前后端已加载 D085/D086 并完成三条真实页面验收；AI 定制目标句仍需模型补充弱本地意图，耗时 `19.818s`，这是后续 Provider/弱意图 P95 优化对象，不影响本轮图片筛选正确性。
- 当前图片话术主筛选使用本地可解释文本证据与已有查询理解上下文，不新增一次外部生成式裁判；后续若真实误差显示口语跨度仍不足，应先补评测，再决定是否利用现有唯一一次 Reranker 分数校准阈值。

### 下一步

1. 继续以真实错误补充图片级回归，不批量修改人工关系或六大体系知识。
2. 单独优化弱本地意图触发模型时的 Provider P95，不用牺牲 D086 图片筛选换取速度。

---

## 2026-07-20：正式 Skill 体系收口与旧规则清理（D087）

### 本轮目标

- 把项目中混合存在的标准 Skill、运行时 Prompt 规则和底层 Python 职责重新整理为完整、可触发、可验证的正式 Skill。
- 删除已下线旧规则，同时保证当前页面、接口、数据库、六体系卖点和搜索结果不受影响。

### 完成内容

- 将项目收口为9个正式 Skill：搜索意图、图片素材分析、上传前图片话术、兼容文案匹配、图片库管理、卖点知识治理、搜索质量评测、模型 Provider 运维和架构维护。
- 每个正式 Skill 均提供标准 `SKILL.md` 和 `agents/openai.yaml`；四个运行时模型能力继续提供精简 `RULES.md`。
- `image_content_analysis` 改为加载整合后的 `analyze-image-asset`，保留 Semantic Profile V3、当前启用卖点校验和待审核关系建议，删除独立固定二级分类任务。
- 删除8个无运行引用或已被当前架构取代的旧规则目录：`analyze-image-content`、`classify-secondary-selling-points`、`integrate-model-provider`、`manage-local-image-storage`、`manage-tag-taxonomy`、`orchestrate-ai-tagging`、`recall-selling-point-images`、`score-image-search-results`。
- 保留兼容的 `/api/ai/selling-points/match` 接口，并把旧硬编码文案清单改为读取运行时版本化目录的正式 `match-copy-selling-points` Skill，避免破坏潜在调用方。
- 新增 `test_project_skills.py`，固定正式 Skill 清单、元数据、退休目录和模型任务映射。

### 修改文件

- Skill：`skills/INDEX.md`、9个正式 Skill 的 `SKILL.md/agents`，以及4个运行时能力的 `RULES.md`。
- 运行时：`backend/app/ai/skill_loader.py`、`backend/app/ai/contracts.py`。
- 测试：`backend/tests/test_project_skills.py`、`backend/tests/test_documentation_consistency.py`。
- 护栏与文档：`AGENTS.md`、`docs/ARCHITECTURE.md`、`docs/DEVELOPMENT_GUARDRAILS.md`、总纲 D087 与本日志。

### 删除内容与恢复边界

- 删除的是无运行引用的旧规则文件和空目录，不删除数据库数据、素材文件、人工关系、公共/图片话术、评测样本、API 或 Python 搜索服务。
- 旧规则文件可从 Git 历史恢复；恢复前必须先证明不会重新引入固定二级标签、`content_tags`、三层弱召回或旧评分公式。

### 数据迁移

- 无数据库迁移；无素材、话术、人工关系、卖点目录或评测金标准写入。

### 测试结果

- 9个 Skill `quick_validate.py` 全部通过。
- Skill映射、图片分析、目录、文档与六体系专项：`33 passed`。
- 后端全量：`185 passed`；Ruff 通过。
- 103条本地评测：意图 `95/95`、Top 3 `94/95`、Top 5 `94/95`、查询类型 `54/54`、P95 `391.81ms`，无 Fallback 或超时。

### 运行影响

- 常驻后端未重启，没有中断当前浏览器页面。当前进程继续使用启动时已加载代码；新的 Skill 映射会在下一次获准重启后生效。

### 下一步

1. 后续新增 AI 能力先定义触发、输入、输出、审核、超时、降级和评测，再决定是否成为正式 Skill。
2. 如果需要让当前常驻后端加载新的 Skill 映射，另行取得重启许可后执行，并复测上传分析、话术生成和三条搜索边界。

---

## 2026-07-20：虚拟班级个性化规划话术稳定化（D089）

### 本轮目标

- 修复“动态组建一个与你水平相匹配的虚拟班级，安排个性化的学习节奏与内容”重复点击时结果在正确两张、12 张和空结果之间变化的问题。
- 保持六大体系、16 个卖点、三层筛选、人工图片关系和 Provider 后备链不变，只补齐已经业务确认的稳定 Skill 语言边界。

### 完成内容

- 真实日志定位到同一句在模型成功时耗时 `19～50s` 并正确命中“AI定制学习方案”，模型超时时却退为 `0.72` 待消歧并开放外部语义链；不稳定来自每次依赖模型/缓存，不是图片库存或第三层规则失效。
- `ai_learning_plan` 新增边界唯一的 Skill 理解信号“与你水平相匹配的虚拟班级”，并以完整句中的个性化节奏/内容安排作为业务解释；信号只指向既有稳定 code，不新增卖点、不进入公共话术数据库。
- 第一层体系路由、第二层卖点规则和同步规划完整知识同步补充该表达，保证模型仅在其他弱/歧义查询中被调用时也遵守同一边界。
- 将原 D086 端到端回归改为外部模型一旦调用即失败，验证目标句完全依赖本地可信单卖点；结果仍只有“ai定制、ai定制规划”两张 `expresses` 产品图，两张创始人 `supports` 证明图继续被第三层过滤。
- 后端从 PID `59436` 重启为 `24066`。真实页面首次搜索及连续 5 次重复搜索均返回相同两张图；六条最新日志耗时 `132～235ms`，查询理解模型、Embedding、Meilisearch 与 Reranker全部跳过，0 超时、0 降级、0 空结果。

### 修改文件

- Skill 治理与体系知识：`skills/understand-image-search-intent/references/public-phrase-governance.json`、`references/sync-planning.md`、`SYSTEM_ROUTER_RULES.md`、`RULES.md`。
- 回归：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`。
- 文档：总纲 0.1 / D089 / 下一步与本项目日志。

### 数据迁移

- 无数据库迁移；无素材、图片话术、公共话术、人工关系或评测金标准写入。

### 测试结果

- 目标本地理解与端到端选图专项：`2 passed`。
- 后端全量：`188 passed`；Ruff 通过。
- 103 条本地评测：业务卖点意图 `95/95`、Top 3 `94/95`、Top 5 全卖点覆盖 `94/95`、查询类型 `54/54`，P95 `485.39ms`，无 Fallback、超时、人工排除违规。
- 真实页面连续 6 次：`6/6` 返回两张正确产品图，耗时 `132～235ms`。

### 遗留问题

- Kimi/DeepSeek/GPT 后备链继续只服务本地未识别、弱候选或真实歧义查询；其 Provider 级成功率和 P95 仍需单独治理，不能用本次确定性短语的快速结果代替模型链验收。
- 本次只固化一条经用户确认、边界唯一的完整表达，不把所有相似长句批量升级为高置信规则；后续新误差仍需逐条评测和跨卖点冲突检查。

### 下一步

1. 继续收集真实重复搜索不一致样本，先判断能否形成边界唯一的 Skill 信号，再决定是否固化。
2. 对仍需外部模型的弱/歧义用例补 Provider 级遥测与稳定性评测。

---

## 2026-07-20：拍题分步引导与动画兜底边界稳定化（D090）

### 本轮目标

- 修复“孩子拍一拍不会的题，AI先问步骤、讲思路，不懂再推对应知识点动画课，学会为止”被错误识别为“动画精讲”的问题。
- 保持六大体系、16 个卖点、三层筛选、人工素材关系和 Provider 后备链不变，明确连续流程中的主卖点与内部兜底证明边界。

### 完成内容

- 历史日志和本地理解复现确认：旧目录把“动画课 + 知识点”以 `0.88` 识别为动画精讲，而拍题精学只因“步骤”获得 `0.72`，因此错误发生在第二层卖点判断，模型被本地强信号跳过，第三层只能在错误卖点范围内选图。
- 按同步自学原始材料，将“拍题 → AI 问步骤/讲思路 → 不懂再推知识点动画课”固定为 `photo_guided_learning` 单卖点；动画课在该整句中仅是分步引导后的后备讲解证明。
- Skill 治理新增完整动作信号“AI先问步骤、讲思路”；动画精讲意图新增该完整流程的排除边界。相反的独立动画诉求仍保持动画精讲，不用全局禁用“动画课”。
- 图片条件门槛在查询触发侧新增“问步骤、先问步骤、讲思路”，允许明确分步引导诉求返回“苏格拉底讲解提问”；图片独有话术词表未增加这些泛词，避免扩大无关图片准入。
- 新增本地理解与端到端选图回归：外部模型一旦被调用即失败，目标句仍只返回“拍题精学、苏格拉底讲解提问”，动画素材不得进入结果。
- 后端重启后真实页面共 `4/4` 次目标句搜索稳定识别为“AI拍题精学”并返回相同两张图，日志耗时 `65～120ms`；“体现动画课很好”仍识别为“动画精讲”，返回 7 张，耗时 `1103ms`。页面最终保留在目标句的正确两张结果。

### 修改文件

- Skill 治理与体系边界：`skills/understand-image-search-intent/references/public-phrase-governance.json`、`references/sync-self-study.md`、`references/sync-school.md`、`references/cross-system-calibration.md`、`SYSTEM_ROUTER_RULES.md`、`RULES.md`。
- 运行策略：`taxonomy/business_intents.json`、`taxonomy/search_policy.json`。
- 回归：`backend/tests/test_query_states_and_negation.py`、`backend/tests/test_phase4_search_orchestration.py`。
- 文档：总纲 0.1 / D090 / 下一步与本项目日志。

### 数据迁移

- 无数据库迁移；无素材、图片话术、公共话术、人工关系或评测金标准写入。

### 测试结果

- 目标本地理解、端到端选图及相反动画边界专项通过。
- 后端全量：`190 passed`；Ruff 通过。
- 103 条本地评测：业务卖点意图 `95/95`、Top 3 `94/95`、Top 5 全卖点覆盖 `94/95`、查询类型 `54/54`，P95 `191.57ms`，无 Fallback、超时、人工排除违规。
- 真实页面目标句 `4/4` 稳定返回 2 张正确素材；独立动画诉求仍正确返回动画精讲素材。

### 遗留问题

- 本次只固定“拍题分步引导 + 不懂再推动画课”这一经业务确认的连续流程，不把所有含“动画/知识点”的句子一律改归拍题精学。
- Kimi/DeepSeek/GPT 后备链继续只服务本地未识别、弱候选或真实歧义查询；Provider 级可用性与时延仍需独立治理。

### 下一步

1. 继续用真实业务连续流程句走查“主入口、方法、兜底结果”的句法层级，避免末端证明词抢占主卖点。
2. 新发现的相邻卖点误差先同时补正例、反例和第三层图片边界回归，再决定是否进入 Skill 高置信目录。

---

## 2026-07-21：证明点运行时识别与素材精匹配（D099）

### 本轮目标

- 把已结构化的六体系证明点接到真实搜索链路，形成“体系 → 卖点 → 可选证明点 → 具体图片”的精细匹配。
- 保持六大体系、16 个稳定卖点、人工素材关系和数据库模型不变；证明点只作为可版本化语义层。

### 完成内容

- 新增证明点只读目录，解析六个体系知识文件中的 56 个 `pp_` code、父卖点、论断、搜索语言和当前素材线索，并把目录指纹纳入查询理解缓存版本。
- `SearchUnderstanding` 新增 `matched_proof_points`；本地可信卖点和模型结果统一在父卖点范围内补全/校验证明点，模型自造 code、跨父卖点 code 和低置信结果退出。
- 第三层在 accepted `expresses/supports` 候选内，分别计算证明点与已采纳素材独有话术、标题、语义摘要、V3 事实/场景的匹配置信度；明确证明点不匹配的同卖点通用图退出，泛搜卖点保持原有候选范围。
- 模型角色、Skill 输出协议和独立输出契约补充可选证明点边界；证明点不直接挑图、不绕过人工关系、不进入数据库固定标签树。
- 搜索结果页展示“进一步命中证明点”和查询识别置信度，单图“为什么匹配”增加证明点素材置信度。
- OpenAPI/前端类型同步新增证明点字段；Docker 后端与 Web 使用当前工作区重建并通过健康检查。

### 修改文件

- 证明点目录与理解：`backend/app/domain/proof_points.py`、`backend/app/services/proof_point_understanding_service.py`、`backend/app/services/query_understanding_service.py`、`backend/app/schemas/ai.py`、`backend/app/ai/normalizer.py`。
- 第三层选图：`backend/app/domain/asset_text_relevance.py`、`backend/app/services/asset_selection_policy_service.py`、`backend/app/services/asset_route_ordering.py`、`backend/app/services/search_concept_routing_service.py`。
- Prompt/Skill：`backend/app/ai/openai_compatible.py`、`backend/app/ai/skill_loader.py`、`skills/understand-image-search-intent/RULES.md`、`references/output-contract.md`。
- 页面与类型：`client/src/pages/ImageHome/SemanticSearchResult/index.tsx`、`searchConceptPresentation.ts`、相关测试、`client/src/types/api.ts`、`openapi.d.ts`。
- 回归与文档：`backend/tests/test_proof_point_runtime.py`、`test_phase4_search_orchestration.py`、总纲 D099 与本日志。

### 数据迁移

- 无数据库迁移；无素材、公共话术、素材独有话术、人工关系或评测金标准写入。
- 证明点继续以六个 Markdown 体系文件为版本化事实来源，不建立证明点表或图片证明点外键。

### 测试结果

- 后端全量：`204 passed`；Ruff 通过；证明点目录确认六体系共 56 条。
- 前端：TypeScript typecheck、ESLint、Vitest `21 passed`、Vite production build 通过。
- 真实页面：“做错的题自动收集归类到错题本”由 5 张收窄为 2 张，证明点识别为“线下错题拍照上传与归档 · 97%”；泛搜“AI错题本”保持 5 张且无证明点；“微信学习周报”识别“家长端查看与定期推送 · 100%”并返回 0 张。
- 页面桌面视口视觉检查通过，证明点行、空结果和反馈区无重叠；最终浏览器保留在 2 张归档证明素材结果页。

### 遗留问题

- 当前证明点到素材仍依赖知识文件“当前素材线索”、accepted 素材话术和客观语义文本推导，没有新增人工图片—证明点关系；后续积累误匹配样本后再评估是否需要版本化多对多审核关系，不能提前固化树。
- `npm run generate:api` 固定访问宿主机 `:8000`，而 Docker 当前只通过 Nginx 暴露 `:80`，脚本在此部署拓扑无法直接拉取契约；本轮按实际后端 schema 同步 `openapi.d.ts`，后续可把脚本改为可配置 OpenAPI URL。
- 证明点本地识别目前只在父卖点已可信时生效；弱/歧义卖点仍先完成体系和卖点裁决，不用证明点反向越权确定卖点。

### 下一步

1. 用其余五体系的真实证明点长句做批量回归，重点收集“同卖点兄弟证明点误放行”和“有素材却误判为空”样本。
2. 后续上传新素材时继续补充准确的 accepted 素材独有话术；素材缺口补齐后，无需改代码即可自动恢复证明点命中。

---

## 2026-07-21：证据表达点、级联纠偏与详情返回状态（D104）

### 本轮目标

- 把原始六体系脑图绿色制作文字作为证明点下的可版本化证据表达点，提升具体作图需求的识别与人工纠偏能力。
- 搜索识别后自动联动体系，并提供卖点、证明点、证据表达点三级筛选；上传和详情支持同层级标注。
- 修复从搜索结果进入详情后返回空白首页的问题，保留离开前的完整搜索状态和位置。

### 完成内容

- 建立 58 条 `ep_` 证据表达点目录，保存父证明点、父卖点、来源截图和少量稳定近义入口；绿色文案仍不是已核验产品事实或已存在素材声明。
- 证据表达点可在已确认卖点范围内反向确定父证明点；模型仅接收候选体系的精简证据目录，非目录 code、错误父链和跨体系结果由边界层纠正或丢弃。
- 素材组新增可空主要证明点和主要证据表达点字段，提供业务层级目录接口及素材层级更新接口；选择最细层时校验并派生父证明点和卖点。
- 搜索接口增加卖点、证明点、证据表达点显式约束。页面识别成功后自动选中对应体系和三级业务筛选；用户改选任一级会对当前句子执行后端重搜，输入新句子则清除上一句自动条件并重新识别。
- 修复人工选择“全部证明点/全部证据表达点”后被自动识别重新选回的问题：前端保留用户明确选择的空值，后端把手动卖点级约束视为停止证明点补全。真实页面从专属路径 1 张结果放宽为卖点级 2 张，且证明点说明同步消失。
- 上传页和素材详情工作台加入三级级联标注。老素材无需一次性迁移，未标注字段保持为空。
- 搜索结果、业务筛选、画面筛选和输入存入当前会话；进入详情时记录滚动位置，返回后恢复原结果、排序和滚动位置。
- 卖点内排序新增“素材对用户原话的直接文本命中”优先级，避免通用证明话术压过具体目标图。

### 修改文件

- 目录与 Skill：`skills/understand-image-search-intent/references/evidence-points.json`、`SKILL.md`、`RULES.md`、`references/output-contract.md`。
- 后端：证据目录/识别服务、查询理解、素材业务层级接口、搜索显式过滤、选图与排序、schemas/models/serializers 及 API router。
- 前端：业务层级目录 hook/共用字段、首页级联筛选、上传页、素材详情工作台、搜索会话状态和详情返回状态。
- 回归与文档：`test_evidence_point_runtime.py`、证明点/选图/编排/Phase 5 接口测试、前端展示测试、总纲与本日志。

### 数据迁移

- 新增 `20260721_0019_asset_business_facets.py`，为 `asset_groups` 增加可空且有索引的 `primary_proof_point_code`、`primary_evidence_point_code`。
- 本地数据库已执行升级到 `20260721_0019`；未批量写入或推测现有素材的最细业务层级。

### 测试结果

- 后端专项：`66 passed`；涉及文件 Ruff 通过。
- 前端：TypeScript typecheck、ESLint、Vitest `22 passed`、Vite production build 通过。
- 浏览器实测：变式训练长句正确联动“同步考点/举一反三/变式与同类题迁移训练/讲完例题后同类变式拓展”；短时讲透查询中目标图排在通用数据图前；详情返回完整恢复搜索词、三级筛选、两张结果顺序和约 `290px` 滚动位置；上传页可选到绿色文案“5-8分钟讲透一个知识点”。

### 遗留问题

- 现有 40 个素材组尚未逐一人工补标证明点和证据表达点；未标注老素材继续依赖已采纳素材独有话术和标题匹配，明确细分筛选可能如实返回空。
- 本轮只运行与 D104 直接相关的后端专项测试，没有重新执行后端全量套件或完整 103 条质量评测。

### 下一步

1. 由业务负责人/设计师在详情工作台按原作图依据补标现有素材，优先处理当前高频误差对应图片。
2. 补标后重跑 103 条评测和真实页面样本，记录证据表达点 Top 1、空结果和兄弟证明点误放行情况。

---

## 2026-07-23：搜索系统优化实施手册（D105）

### 本轮目标

- 把程序架构优化、API 调用治理、历史案例记忆、搜索准确性、数据飞轮和未来模型训练统一成一份可由后续模型逐项执行的标准文档。
- 明确证明点全量审核可以推迟，不阻塞运行一致性、架构减重、API 遥测、案例记忆、卖点优化和反馈闭环。

### 完成内容

- 新增 `docs/SEARCH_SYSTEM_OPTIMIZATION_IMPLEMENTATION_PLAYBOOK.md`，包含 10 个阶段、依赖顺序、具体文件边界、数据表/API 建议、执行步骤、测试、验收、灰度和回滚清单。
- 将“日志只有被审核并由在线链路消费后才构成数据飞轮”“Embedding 只做候选生成”“模型只在候选范围内做结构化判断”“证明点先做 3～6 张代表素材试点”等原则登记回总纲。
- 第一轮建议只做运行一致性、架构全绿、Provider/决策遥测和 accepted 案例记忆，不要求先补完 40 张素材的证明点。

### 修改文件

- `docs/SEARCH_SYSTEM_OPTIMIZATION_IMPLEMENTATION_PLAYBOOK.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。手册中的 `model_attempts`、search log 扩展和 `approved_query_cases` 均为后续实施建议，未创建表、未写数据库。

### 测试结果

- 本轮只修改 Markdown 文档；文档一致性与项目 Skill 测试 `8 passed`，`git diff --check` 通过，手册路径和未来建议文件边界已复核。
- 优化前检查点仍为 `codex/d104-pre-optimization-checkpoint-20260723` / `641d8bc`；本轮未修改搜索行为或运行容器。

### 遗留问题

- 需要从手册阶段 0 开始重新核对运行数据库 revision、容器版本和备份恢复。
- 已知后端 `222 passed`、3 个架构体量护栏失败；应在阶段 1 做等价拆分，不在本轮文档任务中修改代码。

### 下一步

1. 执行手册 Sprint A：运行一致性、版本接口、迁移核对和架构减重。
2. Sprint A 全绿后再实施 API Gateway/决策遥测；证明点审核可继续推迟。

---

## 2026-07-23：查询理解首选 Provider 切换（D106）

### 本轮目标

- 将模型理解的首选 Provider 切换为 DeepSeek，同时完整保留 GPT-5.5 作为第二顺位后备。

### 完成内容

- 当前 Docker 环境顺序改为 `DeepSeek → GPT-5.5`；本地直跑环境顺序改为 `DeepSeek → GPT-5.5 → Kimi`。
- DeepSeek 使用独立 fallback 配置槽位；GPT-5.5 原有主配置、模型名和密钥未删除、未移动。
- 未修改业务 Prompt、六体系、16 个卖点、证明点、素材关系、搜索 Schema 或失败降级逻辑。
- 密钥只保存于 Git 忽略的环境文件，不写入文档、日志或版本库。

### 修改文件

- `.env`、`backend/.env`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- DeepSeek `/models` 返回 `200`，目标模型可用；最小 Chat Completions 返回 `200` 且 JSON 可解析。
- Provider、Skill 与文档一致性专项测试：`15 passed`；Ruff 与 `git diff --check` 通过。
- 后端容器已重建并健康；脱敏运行配置确认顺序为 `DeepSeek → GPT-5.5`。
- 从运行中的后端容器通过项目 Provider 工厂再次调用 `deepseek-v4-pro`，结构化 JSON 返回成功。

### 遗留问题

- Provider 连通不等于业务准确性通过；后续仍需用真实搜索样本比较 DeepSeek 与 GPT-5.5 的意图、证明点和延迟表现。

### 下一步

1. 用真实但非敏感的搜索样本对比 DeepSeek 与 GPT-5.5 的意图、证明点和延迟表现。

---

## 后续日志模板

后续每次改造在本文末尾追加以下内容：

```markdown
## YYYY-MM-DD：本轮标题

### 本轮目标

### 完成内容

### 修改文件

### 数据迁移

### 测试结果

### 遗留问题

### 下一步
```
