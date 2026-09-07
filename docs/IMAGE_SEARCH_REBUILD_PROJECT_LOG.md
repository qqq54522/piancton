# 图片搜索改造项目日志

更新时间：2026-09-03
当前范围：Phase 0～Phase 6；火山 VikingDB 干净知识路由、渠道/版位筛选、搜索顶部命中解释和 API 调用边界收口继续按真实业务边界推进
当前状态：Phase 0～6 工程改造完成；当前打开的本地项目作为唯一基准；火山 VikingDB 当前只保留六大体系和 16 个卖点的干净知识文档；搜索主链路由火山先命中卖点，再回本地数据库按人工 accepted 关系取图库；API 中心当前正式自动调度只保留搜索结果顶部“命中卖点解释”和素材库 Agent 两类调用；搜索顶部解释由后端与前端双层清理过程文案；上传图片语义分析、上传前素材话术生成和兼容文案卖点匹配不再作为当前主流程任务。

> 本文档记录项目实际做过的工作、迁移、验证结果和遗留事项。架构原则、业务决策与后续阶段路线仍以 `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md` 为唯一事实来源。后续日志按日期追加，不覆盖历史记录。

---

## 2026-09-03：搜索顶部过程文案硬清理（D270）

### 用户目标

- 黑色命中说明框继续只保留业务判断。
- 彻底去掉“未指定渠道”“当前返回”“卡片下方只保留搜索卖点”等过程说明。

### 完成内容

- 后端 `SearchResultRecommendationService.explain_route()` 对模型解释做硬清理，遇到默认渠道、返回数量、已审核素材、卡片展示、渠道筛选或收窄版位等过程标记直接截断。
- 前端 `cleanRouteExplanation()` 同步增加同类截断，防止旧缓存或异常响应露出过程句。
- 新增回归测试覆盖模型返回“业务判断 + 未指定渠道 + 当前返回 + 卡片下方”时，最终解释只保留业务判断。

### 验证

- 后端 Ruff：通过。
- Docker 后端专项：`tests/test_search_result_recommendation_reason.py tests/test_taxonomy_catalog.py`，17 passed。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run lint`：通过。
- 前端 `npm run build -- --logLevel error`：通过。
- `git diff --check`：通过。
- Docker backend/web 重建成功，backend、web、postgres 均 healthy。

### 本轮边界

- 不改火山 VikingDB 知识库。
- 不改卖点命中、渠道筛选、排序、返回数量或素材卡片展示。

---

## 2026-09-03：搜索顶部专业命中分析（D269）

### 用户目标

- 搜索结果顶部黑色说明框不要再解释系统过程。
- 不再展示“未指定渠道默认保留什么”“当前返回多少组”“卡片下方只保留什么”。
- 说明要更精细、更有业务判断感，让人一眼觉得命中卖点是有依据的。

### 完成内容

- `search_result_recommendation_reason` Prompt 改为专业命中分析，只解释用户原话与已命中卖点之间的业务关系。
- Prompt 明确禁止输出内部实现、返回数量、渠道默认规则、卡片展示规则、模型分数、VikingDB、索引、算法和 Provider。
- 后端传给解释模型的卖点信息从纯卖点名升级为卖点名、关系和命中理由，便于模型写出更有依据的判断。
- 前端黑色框 fallback 改为“整句话有效信号 → 卖点核心能力”的业务说明。
- 前端清理旧解释中可能残留的“未指定渠道/当前返回/卡片下方”过程句。

### 本轮边界

- 不改火山召回、卖点判断、排序、渠道/版位筛选或候选准入。
- 不恢复逐图动态推荐理由。
- 不修改火山数据集或本地素材关系。

---

## 2026-09-03：API 中心模型位置收敛（D268）

### 完成内容

- API 中心页面导航从“调度配置”改为“模型位置”，页面描述明确当前搜索主判断由火山向量检索负责。
- 模型位置配置只围绕两处当前 API 调用解释：`search_result_recommendation_reason` 用于搜索结果顶部命中卖点解释，`asset_agent_chat` 用于素材库 Agent。
- 新增 API 表单内的 temperature 兼容探针默认任务从退役的 `search_system_routing` 改为 `search_result_recommendation_reason`。
- 健康度监测的单 API 测试默认任务也改为 `search_result_recommendation_reason`。
- 调用链路日志仍保留退役任务筛选，用于历史追溯，但项目 `skills/INDEX.md` 运行时映射只列当前两个模型位置。

### 本轮边界

- 不读取、不输出完整 API Key。
- 不修改火山 VikingDB 数据集内容。
- 不改变搜索召回、排序、渠道收窄、素材关系或 Agent 会话逻辑。

---

## 2026-09-03：API 路由槽位与任务范围硬收口（D267）

### 完成内容

- API 中心启动初始化会删除退役任务槽位，真实运行态只保留 `search_result_recommendation_reason` 和 `asset_agent_chat`。
- 自动调度和人工主/备槽位都按 Key 的任务范围过滤；明确范围不匹配的 Key 不再被拿去跑当前任务，空范围仅作为历史通用 Key 兼容。
- 健康检查、温度探测默认任务改为当前搜索解释任务；直接调度退役任务会返回 `model_task_retired`。
- 重建后端容器后，真实搜索 `拍` 返回 20 张并命中 `同步自学体系 > AI拍题精学`，顶部命中解释可由 API 生成。

### 验证

- `backend/.venv/bin/ruff check backend/app/services/api_center_service.py backend/app/repositories/api_center_repository.py backend/app/schemas/api_center.py backend/tests/test_api_center.py`
- `PYTHONPYCACHEPREFIX=/tmp/piancton-pycache python3 -m compileall backend/app backend/tests`
- Docker backend 重建并 healthy。
- Docker 后端专项：`tests/test_api_center.py tests/test_search_result_recommendation_reason.py`，70 passed。

---

## 2026-09-03：API 调用边界收口，保留搜索级命中解释（D266）

### 用户目标

- 上传不再做图片语义分析。
- 文案卖点匹配不再作为单独能力保留。
- 搜索结果仍需要一段动态解释，但解释对象从“每张图为什么合适”改为“用户输入为什么命中这些卖点”。
- 素材库 Agent 继续保留 API 调用。

### 完成内容

- API Center 默认调度槽位收敛为 `search_result_recommendation_reason` 和 `asset_agent_chat`。
- `search_result_recommendation_reason` 改为搜索结果顶部命中解释，只消费用户原话、已命中卖点和结果数量，不参与召回、排序或候选准入。
- 上传图片语义分析接口和兼容文案卖点匹配接口改为退役响应；前端详情页移除重新分析入口，仅保留历史画面信息只读展示。
- 运行时 Skill 映射移除图片分析和文案卖点匹配，历史 Skill 目录继续保留作资料。

### 本轮边界

- 不改变火山 22 条体系/卖点知识库。
- 不写入图片标题、主图、新版主图、竖版延展等污染数据。
- 不删除历史数据库表，旧素材话术和旧语义字段仍可作为审计/回滚兼容读取。

---

## 2026-09-01：第三轮卖点优化，背后意思与边界（D255）

### 用户目标

- 真正优化“卖点背后的意思与边界”，而不是继续堆更多话术。
- 让模型先理解每个卖点在业务上解决什么问题，再判断它和相邻卖点的差异。

### 完成内容

- 16 个卖点判断卡片新增 `meaningBehind`。
- 16 个卖点判断卡片新增 `boundaryLogic`。
- 第二层 Prompt 渲染新增“背后意思”和“边界逻辑”。
- 判断顺序调整为 `oneSentenceDecision → meaningBehind → boundaryLogic → definition → object → action → purpose → positiveSignals → boundaries → confusesWith`。

### 验证结果

- 16 张卡片均包含 `oneSentenceDecision/meaningBehind/boundaryLogic`。
- 16 个卖点 code 无重复。
- 相关 Skill/查询状态回归通过。

### 本轮边界

- 不修改数据库。
- 不新增或删除公共话术。
- 不改变召回、排序、证明点、人工素材关系或素材事实源。

---

## 2026-09-01：卖点判断卡片第一轮精修（D254）

### 用户目标

- 判断 16 个卖点解释是否足够清晰。
- 不继续堆公共话术，而是让每个卖点有一条更硬、更容易迁移到不同模型的判断标准。

### 完成内容

- 16 个核心卖点统一新增 `oneSentenceDecision`。
- 运行时 Prompt 渲染把“一句话判定”放到每张卡片最前。
- 判断顺序调整为 `oneSentenceDecision → definition → object → action → purpose → positiveSignals → boundaries → confusesWith`。
- 收紧易混边界：同步校内/极速预习复习、AI私教答疑/AI拍题精学、专家规划/AI定制学习方案/真人老师督学、动画精讲的概念探索、万能解法/举一反三。

### 验证结果

- 16 张卡片均包含一句话判定。
- 16 个卖点 code 无重复。
- 相关 Skill/查询状态回归通过。

### 本轮边界

- 不修改数据库、公共话术、召回、排序、证明点或人工素材关系。
- 不改变卡片层开关；仍可通过 `search_selling_point_decision_cards_enabled=false` 关闭。

---

## 2026-09-01：卖点判断卡片层（D253）

### 用户目标

- 不希望继续靠大量公共话术硬堆准确率，避免话术越补越死。
- 希望换 Keyme、DeepSeek Pro 或其他模型时，卖点理解仍主要依靠稳定业务定义和边界，而不是只依赖某个模型对短句的理解。
- 这次先加一层替代当前话术 Skill 的主要判断位置；如果不好，可以直接关掉这一层。

### 完成内容

- 新增 `selling-point-decision-cards.json`，为 16 个核心卖点分别写入判断卡片。
- 每张卡片包含本体定义、核心对象、主动作、用户目的、正向信号、排除边界、易混卖点和判定规则。
- 第二层卖点 Prompt 会先加载第一层候选体系内的卡片，再加载候选体系运行时摘要和目录。
- `SELLING_POINT_ROUTER_RULES.md` 明确：有卡片时先按卡片本体和边界判断，公共话术只能辅助解释，不能覆盖卡片边界。
- 新增 `search_selling_point_decision_cards_enabled` 配置开关；关闭后可回到旧 Prompt 结构。

### 验证结果

- 卡片 JSON 格式校验通过。
- `skill_loader.py` 和配置文件 Python 编译通过。
- `tests/test_taxonomy_catalog.py`：`9 passed`。

### 本轮边界

- 不删除旧公共话术。
- 不修改数据库 schema、素材事实源、人工 accepted 关系、召回、排序或第三层证明点。
- 不把 16 个卖点一次性全塞给模型；运行时仍只加载第一层路由后的候选体系卡片。

---

## 2026-09-01：多卖点结果按理解重点编排（D252）

### 用户目标

- 修复“洋葱的拍题精学举一反三”这类明确多卖点查询只突出一个方向的问题。
- 精准不等于每次只返回一个卖点；原话里明确涉及几个卖点，就应该返回几个卖点方向，并把话里重点排在前面。

### 完成内容

- 确认当前理解层已经能把“洋葱的拍题精学举一反三”识别为 `multi_business_intent_search`，同时命中 `举一反三` 和 `AI拍题精学`。
- 定位问题在后续多卖点结果编排：召回分数或标题强命中可能把次要卖点抢到第一。
- 修改多卖点 active concept 编排逻辑，按 `SearchUnderstanding.matched_business_concepts` 的顺序重排可信卖点，而不是只按召回分数排序。
- 保持多卖点“每个方向至少先保留一张可信素材”的既有策略，后续结果再展示剩余相关素材。

### 验证结果

- Docker 后端已重建并 healthy。
- 新增多卖点排序测试通过。
- 多卖点边界、查询状态和业务校准回归：`40 passed`。
- 真实后端搜索“洋葱的拍题精学举一反三”前两位为 `举一反三`、`拍题精学`，两个卖点方向均保留。

### 本轮边界

- 不修改查询理解规则。
- 不修改业务词库、公共话术、模型 Prompt、人工素材关系或数据库 schema。
- 不放宽可信素材准入：多卖点仍只从已审核 `expresses/supports` 关系中进入主通道。

---

## 2026-08-31：专项培优训练拔高口语强路由（D251）

### 用户目标

- 修复“题型突破”“想训练拔高的图”等话术在页面搜索中搜不到或前排不准的问题。
- 不能靠随手堆长句补丁，要保持专项培优、举一反三、学段衔接等相邻卖点边界稳定。

### 完成内容

- 确认 `题型突破` 后端已能通过 `targeted-module-breakthrough` 组合语义命中 `专项培优 / 按题型和薄弱点定向突破`。
- 定位 `想训练拔高的图` 的真实问题：数据库 accepted 话术存在，但人工 alias 在口语长句中只形成弱/中证据，加上“图/素材”泛搜索词后没有进入强路由。
- 在 `public-phrase-governance.json` 的 `difficulty-excellence-upgrade` 组合信号里补入 `训练拔高/拔高训练`，让“训练 + 拔高”类口语统一进入受治理组合语义，而不是逐句硬贴。
- 新增两条业务校准样例：`想训练拔高的图`、`想找训练拔高素材`。
- 补充搜索理解回归，锁定这两类口语必须进入 `pp_exam_focus_targeted_modules`。

### 验证结果

- Docker 后端已重建并 healthy。
- 搜索理解与业务校准回归：`39 passed`。
- 真实后端搜索验证：`题型突破` 首位 `考前专项突破`；`想训练拔高的图`、`想找训练拔高素材` 首位 `重难点培优`。

### 本轮边界

- 不修改数据库 schema。
- 不修改模型 Prompt、API 调度、上传链路或排序主链路。
- 不新增卖点、证明点或体系。
- 不把泛词“训练”“拔高”单独升为强公共话术；只有“训练拔高/拔高训练”这类完整业务表达进入专项培优组合语义。

---

## 2026-08-29：API 中心 P0 可靠性第五步（D241）

### 用户目标

- 进入 API 库存治理阶段，避免未来导入 100～200 个 API 后出现重复、不可追溯和难维护问题。
- 同一个中转站、同一个模型、同一个 Key 不应重复保存；同站不同 Key 或同 Key 不同模型仍应允许。
- API 新增、修改、停用、删除和整站停用需要留下后台审计，但不能泄露密钥。

### 完成内容

- `model_api_credentials` 新增 `api_key_fingerprint`，保存不可逆 SHA-256 指纹，用于库存判重。
- 新增迁移 `20260829_0031_api_credential_inventory_governance.py`，并为 Provider 类型、规范化地址、模型和 Key 指纹建立库存身份索引。
- 新增和关键字段更新时，服务层先按库存身份判重，再执行真实探针；重复时返回 `api_credential_duplicate`，不消耗模型调用。
- 历史凭据在运行时初始化或后续 API 操作中自动补齐 Key 指纹。
- 后台 API Center route 接入 `AuditService`，记录凭据新增、修改/启停、删除、温度调优和整站停用。
- 审计详情只包含非敏感字段、变更字段、受影响凭据 ID/标签和 request_id；完整 Key、Key preview、Prompt、图片字节和上游响应不进入审计。

### 验证结果

- 本地 API Center 专项：`55 passed`。
- 后端定向 Ruff：通过。
- 后端定向 Pyright：`0 errors, 0 warnings, 0 informations`。
- 文档一致性：`4 passed`。
- 临时 SQLite 从空库升级到 head：通过。

### 本轮边界

- 不改变 API 调度排序、接力、预算或并发算法。
- 不改变搜索语义、六大体系、16 个卖点、证明点、Prompt、素材事实源或 Agent 记忆。
- 不实现多服务器共享容量租约。
- 不实现服务器定时巡检。
- 当前仍不做密钥静态加密，生产密钥加密继续作为后续 P1。

---

## 2026-08-29：API 中心 P0 可靠性第四步（D240）

### 用户目标

- 开始第四波“规模化调度基础”，先按单 backend 进程内实现，不提前复杂化到多服务器。
- 未来 API 数量可能增长到 100～200 个，当前调度不能继续依赖一次请求内反复全量查库和重算指标。
- 如果某个中转站整体抽风，系统应该能识别和提示，但不要擅自停用；管理员需要有一键停用该站全部 API 的操作。

### 完成内容

- 新增请求级调度快照：单次模型任务开始时读取凭据、路由槽位和滚动指标，后续接力循环复用同一快照。
- 新增 15 秒短 TTL 调度指标缓存，滚动成功率、失败率和延迟不再在一次请求内反复读取 24 小时日志；当前并发占用仍实时读取进程内容量账本。
- API Center Summary 新增中转站聚合数据，按 Provider 主机展示 Key 数、启用数、自动候选数、当前占用、24h 调用、失败率、超时数和状态建议。
- API 管理页新增“中转站概览”，系统按最近异常集中程度标记稳定、观察或建议处理。
- 新增管理员一键停用某个中转站下全部 API 的后端接口和前端操作；系统不会自动停用或偷偷改管理员启停状态。
- 同步更新 `docs/API_CENTER_RELIABILITY_REQUIREMENTS.md` 1.2 和总纲 D240。

### 验证结果

- 后端 API Center 专项：`38 passed`。
- 后端全量：`332 passed, 4 skipped`。
- 后端定向 Ruff：通过。
- 后端定向 Pyright：`0 errors, 0 warnings, 0 informations`。
- 前端 TypeScript：`tsc --noEmit` 通过。
- 前端 ESLint：通过。
- 前端 Vitest：`16 files / 51 tests passed`。
- `git diff --check`：通过。

### 本轮边界

- 不实现多服务器共享容量租约。
- 不做服务器定时巡检。
- 不改变搜索语义、六大体系、16 个卖点、证明点、Prompt、素材事实源或 Agent 记忆边界。
- Provider 级异常只形成观察和人工治理入口，不做系统自动停用。

---

## 2026-08-28：API 中心 P0 可靠性第一步（D237）

### 用户目标

- 开始一步一步优化 API 中心的随机问题，但避免用巨大补丁堆复杂度。
- 优先处理会导致“页面保存成功、运行时失败/不认模型/不走备用”的结构边界问题。
- 当前仍不做服务器定时巡检。

### 完成内容

- 后台创建 API 和关键字段更新接口强制执行后端真实探测；探测失败时不入库、不覆盖旧配置。
- Provider 类型收口到当前已实现的 `openai_compatible`，未知协议保存前拒绝。
- API 地址会把误填的完整 `/chat/completions` 端点规范化为 Provider 根地址，避免运行时重复拼接。
- 自动调度候选池不再按 `max_parallel <= 4` 截断，失败时可以继续尝试第 5 个及之后的健康候选。
- 一键巡检在并行环境按 Provider 主机分组，同站 Key 组内顺序执行，避免同一中转站多 Key 同时压测造成假超时。
- OpenAI-compatible Provider 的 404 和 5xx 错误码对齐可靠性基线，分别归为 `model_not_found` 和 `upstream_unavailable`。
- API 中心页面撤掉浏览器本地“定时巡检”伪能力，并把容量文案改为“默认安全容量 + 当前占用”，不再声称系统已估算容量。
- 更新 `docs/API_CENTER_RELIABILITY_REQUIREMENTS.md` 到 1.1，标记已完成项和剩余 P0。

### 验证结果

- 后端 API 中心专项：`44 passed`。
- 前端 TypeScript：`tsc --noEmit` 通过。
- 前端相关 Vitest：`1 passed / 3 tests passed`。

### 剩余 P0

- 建立任务能力探针，至少区分文本 JSON 能力和图片输入能力。
- 继续优化任务预算切片，避免首个慢 API 在极端情况下吃完全部 fallback 时间。
- 最后补一次更大范围回归和 Docker 真实中转站验收。

### 本轮边界

- 不新增数据库迁移。
- 不改变搜索语义、六大体系、16 个卖点、证明点、素材事实源、Prompt 或 Agent 隐私边界。

---

## 2026-08-28：API 中心可靠性需求基线（D236）

### 用户目标

- 不再等每次出现网络、连接、模型、检测或调度问题后逐个打补丁；先建立覆盖完整 API 生命周期的统一需求和验收标准。
- 当前不实现服务器定时巡检，先确认 API 中心还有哪些已知差距和潜在问题。

### 完成内容

- 新增 `docs/API_CENTER_RELIABILITY_REQUIREMENTS.md`，覆盖故障分类、API 管理、健康与能力探测、调度、日志和管理员体验。
- 需求逐项标注已完成、部分完成、未完成和延期，并给出 P0/P1/P2 优先级。
- 建立 16 类场景验收矩阵，覆盖错误密钥、错误模型、地址路径、参数兼容、慢响应、瞬时连接失败、同站多 Key、跨站均衡、429/5xx、非法 JSON、图片能力、重复搜索、停用、删除、页面等待和敏感日志。
- 明确当前 P0 差距，后续先收口可靠性闭环，再考虑定时巡检等新增能力。

### 本轮边界

- 只新增和更新需求文档，不修改后端、前端、数据库或运行配置。
- 不改变搜索语义、业务事实、负载均衡、现有健康策略、人工主备或 Agent 隐私边界。

---

## 2026-08-28：API 健康巡检自动等待与校准（D235）

### 用户目标

- 健康检查只需要确认不同速度的 API 能否真实连接并完成最小调用，不应被当前凭据的 20 秒运行上限提前截断。
- 管理员不手动把 20 秒改成 30、40 秒，也不逐个重复测试；等待、复测和参数校准由系统完成。

### 实现边界

- 健康巡检使用独立的 60 秒系统窗口，瞬时连接/限流/上游/响应错误同轮自动再试一次，页面等待自动覆盖两次最坏尝试和批量并行轮次。
- 成功后根据真实耗时自动提高该 API 的运行单次上限；失败后保留后续自动巡检，不提示人工调秒数。
- 不新增数据库字段或迁移，不改变搜索任务总预算、负载均衡、任务屏蔽、人工主备或业务事实。

### 完成与验证

- Provider 响应等待错误不再显示“可调大超时秒数”；健康巡检连续等待失败时明确说明系统已自动重试且后续巡检会继续处理。
- 健康探针忽略凭据当前运行单次上限，固定使用 60 秒系统窗口；成功后按真实耗时两倍加 10 秒计算 20～60 秒安全值，只自动提高、不向下抖动。
- 单个与批量巡检的前端等待覆盖每个凭据两次最坏尝试；瞬时错误重试专项、系统窗口与自动校准专项均通过。
- API 中心与 Provider 专项 `65 passed`，后端全量 `336 passed`，Ruff、目标 Pyright、前端 TypeScript、ESLint、Vitest `16 files / 51 tests passed` 和 production build 均通过。
- Docker 真实验收：旧记录中约 21 秒被判超时的 `ohmygpt1/2` 单独巡检均恢复 `ok`；最终一键巡检 10 个 API 在约 12.6 秒内完成，结果为健康 10、异常 0。

---

## 2026-08-28：自动 API 健康负载均衡（D234）

### 用户目标

- 多个 API 使用相同模型、但来自不同中转站时，自动调度应动态分散调用，不能让同一个 Key 承受整条五层搜索链和连续请求。
- 分配必须以搜索成功为前提；异常或满载 API 不应为了随机而被强行选中。
- 人工指定任务继续严格使用管理员选择的主 API 和备用池。

### 实现边界

- 自动模式在健康档位内按当前占用与最近五分钟调用次数做轮转，再用失败率、延迟和优先级细排。
- 运行账本在每次调用结束后立即更新；同一搜索的下一层也会重新选择当前压力最低的健康 API。
- 不新增数据库字段或迁移，不改变模型任务、Prompt、搜索语义、业务事实、任务屏蔽或 Agent 隐私边界。

### 完成与验证

- 调度键新增 Provider 主机级压力与凭据级压力：先均衡不同中转站，再均衡同站内多个 Key；健康档位、任务屏蔽和人工主备边界保持不变。
- 新增连续 6 次调用覆盖：三个同档健康凭据会全部使用且次数差不超过 1；同一 Provider 有两个 Key、另一 Provider 只有一个 Key 时，两个 Provider 的调用次数差不超过 1。
- API 中心专项 `35 passed`，后端全量 `333 passed`，Ruff 通过，目标 Pyright `0 errors / 0 warnings`。
- Docker 实搜“想找一个会提问的AI老师”连续两次均正确返回 1 张素材且五层全部 `ok`。第一次 Provider 顺序为 `laozhang → ohmygpt → laozhang → ohmygpt → laozhang`，第二次自动从 `ohmygpt` 开始并继续交替，证明运行账本会跨层级、跨连续搜索持续分散压力。
- 当前自动池实际只有 `laozhang` 的三个健康 Key 和 `ohmygpt` 的一个健康 Key；另外四个 ohmygpt Key 当前健康状态仍为超时/失败，DeepSeek 两个 Key 的自动候选资格关闭，因此不会为了均衡而牺牲搜索成功率。

---

## 2026-08-28：搜索 API 必经执行策略（D233）

### 用户目标

- 普通搜索每次都必须真实调用 API 中心，不以模型费用或 2.5 秒速度优先。
- 一个 API 失败或超时后继续主备，模型链完成后再返回结果；本地链只保护业务事实和全部外部 API 失败时的最终可用性。
- 相同搜索再次执行也必须产生新的 API 调用，不能命中模型缓存后直接返回。

### 完成内容

- 搜索总等待上限从 2.5 秒提高到 180 秒，页面等待提高到 210 秒。
- 第一层体系路由、第二层卖点识别、第三层证明点识别、第四层候选复核和第五层推荐理由任务预算调整为 45/60/45/45/45 秒。
- API 中心任务总预算与凭据单次调用上限分离：槽位预算负责主备合计，单个 attempt 只读取当前凭据上限。
- 手动业务筛选也会调用模型；删除查询理解和候选复核跨搜索缓存，重复查询每次重新执行 API。
- 保留 Embedding 向量缓存；它只减少相同向量服务调用，不替代 API 中心模型理解或候选复核。
- 新增迁移 `20260828_0029_search_api_execution_policy.py`，只提升仍处于旧默认值的五个搜索槽位，不覆盖管理员设置的更大预算。

### 不变边界

- 身份码、素材码和分享链接精确查找继续不调用模型。
- 模型结果不能覆盖人工 accepted 关系、可信卖点准入、证明点边界或素材事实。
- 所有外部 API 最终不可用时仍允许本地确定性链返回结果，避免 API 中心成为整站单点故障。

### 验证结果

- 数据库迁移已升级到 `20260828_0029`，五个搜索任务槽位均为自动调度，实际预算为 `45/60/45/45/45` 秒。
- 后端全量测试 `331 passed`；Ruff、目标 Pyright、前端 TypeScript、ESLint、Vitest `16 files / 51 tests passed` 和 `git diff --check` 均通过。
- Docker 重建后使用同一句“想找一个体现AI互动教学的卖点”连续搜索两次，两次都返回 1 张正确素材且整次搜索未超时；请求 ID 分别独立。
- 第一次产生 3 条真实模型调用，第二次产生 5 条真实模型调用；第二次完整执行体系路由、卖点理解、证明点理解、候选复核和推荐理由，全部状态为 `ok`。这证明重复搜索不会再用模型缓存跳过本次 API 调用。

---

## 2026-08-28：搜索结果与 API 调用链路关联（D232）

### 问题与结论

- 查询“想找一个体现AI互动教学的卖点”在 2.605 秒内正确返回 1 张“AI拍题精学”素材；本地概念和数据库召回成功，模型查询理解、重排和候选复核因 2.5 秒搜索总预算到期而降级。
- 同期调用链路的搜索运行时记录全部缺少 `search_log_id/request_id`，导致不同搜索和被取消的旧请求平铺混在一起。
- 搜索响应结束后底层同步网络线程才返回连接异常；取消信号已经触发，但 Provider 把关闭连接产生的 `ConnectError` 误分类为 API 地址、DNS 或本机网络故障。

### 完成内容

- 请求编号贯穿请求级 API 中心调度 Provider 和每个模型 attempt；上传分析、素材话术、素材库 Agent 等请求级模型任务也同步保留请求编号。
- 搜索日志与调用记录支持双向时序关联：先完成的调用在搜索日志提交时回填，晚完成的调用在写入时按请求编号反查搜索日志。
- API 中心调用链路新增“所属请求”，搜索调用显示搜索原话、返回结果数、是否为部分增强超时和请求编号；分支状态与整次搜索结果分开表达。
- 取消信号触发后的连接超时、读取超时、通用超时和连接错误统一映射为模型调用取消，不再误报地址或 DNS 故障。

### 修改文件

- `backend/app/ai/contracts.py`
- `backend/app/ai/openai_compatible.py`
- `backend/app/api/dependencies.py`
- `backend/app/repositories/api_center_repository.py`
- `backend/app/repositories/search_log_repository.py`
- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_service.py`
- `backend/app/services/search_log_service.py`
- `backend/tests/test_ai_provider.py`
- `backend/tests/test_api_center.py`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`

### 验证结果

- 后端 API 中心、Provider 和取消专项：`60 passed`；后端全量：`330 passed`；Ruff、定向 Pyright 通过。
- 前端 TypeScript、ESLint、Vitest `16 files / 51 tests passed`、production build：通过。
- Docker backend/web 重建完成，backend/web/postgres/meilisearch 均 healthy。
- 内置浏览器真实复测同一句查询仍返回 1 张正确素材；最新调用记录显示搜索原话、`结果已返回 1 张 · 部分增强超时` 和同一请求编号，取消记录为 `超时 / 模型调用已取消`，未再误报地址或 DNS 故障。
- 无数据库迁移，不改变搜索语义、总预算、召回、排序或素材事实。

---

## 2026-08-28：API 等待预算分层与自动设置（D231）

### 问题

- 健康页“请求等待超时”来自浏览器 30 秒 HTTP 上限，但页面提示错误地让管理员调大模型超时。
- 新增 API 暴露“超时秒数”，管理员无法在首次接入未知中转站时合理判断。
- 任务槽位也只显示“超时”，没有说明它是主备尝试合计的任务总预算。

### 本轮目标

- 分开表达页面等待、单次 API 调用和任务总预算，消除三个同名参数。
- 新增 API 的单次调用上限由兼容测试根据真实耗时自动设置，不再要求管理员猜数字。
- 健康巡检的页面等待时间根据实际检查数量和后端上限计算，避免后端仍在执行而页面先报错。

### 不变边界

- 不改变任务默认预算、API 主备关系、自动候选资格、健康排序或容量算法。
- 不改变搜索语义、素材事实、Agent 会话和用户权限。

### 完成内容

- 全局页面请求超时提示移除“调大超时秒数”，避免把 HTTP 等待误导成模型配置问题。
- 新增 API 表单移除可编辑超时数字，改为“单次调用上限：测试后自动设置”；兼容测试最多给单次探针 60 秒，成功后按最慢探针耗时的 2 倍加 10 秒余量计算，最终限制在 20～60 秒。
- API 列表把“超时”改为只读“单次调用上限”；测试按钮改为“测试 API 并自动设置”。
- 调度配置把“超时”改为“任务总等待上限（秒）”，页面明确解释它包含主 API、备用 API、容量等待和重试，通常无需修改。
- 健康巡检的前端等待上限按 API 数量、单次 30 秒上限、4 路并行轮数和 15 秒页面余量计算；单个检测也保证页面等待长于后端探针。
- 正式 PostgreSQL 环境的批量巡检使用独立数据库会话最多并行检查 4 个 API；SQLite 测试环境继续顺序执行，避免共享测试连接的线程风险。

### 修改文件

- `backend/app/services/api_center_service.py`
- `client/src/api/apiCenterWaitPolicy.ts`
- `client/src/api/apiCenterWaitPolicy.test.ts`
- `client/src/api/admin.ts`
- `client/src/api/client.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 验证结果

- 后端 API 中心专项：`30 passed`；后端全量：`327 passed`。
- 前端 TypeScript、ESLint、Vitest `16 files / 51 tests passed`、production build：通过。
- Ruff、Pyright、`git diff --check`：通过。
- Docker backend/web 重建完成，backend/web/postgres/meilisearch 均 healthy。
- 内置浏览器确认新增 API 不再提供超时输入，API 列表展示“单次调用上限”，调度页展示“任务总等待上限（秒）”及完整解释。
- 真实点击“一键巡检全部 API”后，10 个 API 均返回检测结果，页面未出现原 30 秒等待误报；结果为 9 个健康、1 个真实连接失败，调用链路准确记录具体 Provider 错误。

---

## 2026-08-28：API 启停、健康与兼容探测分离（D230）

### 本轮目标

- 消除一次网络或模型失败后，人工指定 API 因进入 cooling/invalid 而被静默跳过的复发路径。
- 把两个层级的“自动调度”改成明确的自动候选资格和任务运行方式。
- 让新增 API 测试准确区分鉴权、地址/模型、限流、网络、超时、返回格式和温度问题。
- 支持完全不接受 temperature 参数的 OpenAI-compatible 中转站。

### 已确认边界

- `status` 是管理员启停事实；`last_status/last_error`、健康快照和调用链路是运行健康事实。
- 人工任务只排除管理员明确停用的 API；自动任务继续使用自动候选资格、任务屏蔽和健康容量排序。
- 温度探测只对明确温度兼容错误继续尝试；其他错误立即返回真实原因。
- Provider 分类错误不得记录中转站原始响应、密钥、Prompt 或业务内容。

### 完成内容

- 管理员持久化状态收口为 `active/disabled`；真实调用和健康巡检不再把凭据自动改成 `cooling/invalid`，初始化时会把历史健康状态迁回 `active`。
- 人工主 API 和备用池只排除管理员明确停用的凭据；一次超时、限流或网络失败仍保留人工配置，并按主备顺序继续尝试。
- OpenAI-compatible Provider 增加稳定错误码，区分鉴权失败、地址或模型不存在、限流、上游故障、连接失败、连接超时、响应超时、非法 JSON、temperature 值不兼容和参数不支持。
- 温度测试只在明确的 temperature 兼容错误时继续；鉴权、地址、网络等错误立即停止。新增“不发送 temperature”候选，测试成功后连同 `temperature_enabled=false` 一起保存。
- API 管理开关改为“允许进入自动候选池（关闭后仍可人工指定）”；任务配置改为“当前任务自动选择/当前任务人工指定”，屏蔽名单改为“本任务自动排除”。
- OpenAPI 契约和前端类型已重新生成，前后端均使用新的 temperature 模式和错误字段。

### 修改文件

- `backend/alembic/versions/20260828_0028_api_temperature_mode.py`
- `backend/app/ai/contracts.py`
- `backend/app/ai/openai_compatible.py`
- `backend/app/models/api_provider.py`
- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_runtime_policy.py`
- `backend/app/services/api_center_service.py`
- `backend/tests/test_ai_provider.py`
- `backend/tests/test_api_center.py`
- `client/src/api/admin.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`

### 数据迁移

- 新增 `20260828_0028_api_temperature_mode.py`，为 `model_api_credentials` 增加非空 `temperature_enabled`，历史记录默认继续发送 temperature。
- Docker 启动日志确认执行 `20260827_0027 -> 20260828_0028`；数据库 `alembic_version` 为 `20260828_0028`。
- 本地 10 个 API 均保持 `active`；DeepSeek1/2 为 `auto_assign_enabled=false`，素材库 Agent 仍是 DeepSeek1 主、DeepSeek2 备。

### 验证结果

- 后端专项：`56 passed`；后端全量：`327 passed`。
- Ruff 通过；Pyright `0 errors / 1 existing warning`，warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build：通过；OpenAPI 生成通过；`git diff --check` 通过。
- Docker backend/web 已重建，backend/web/postgres/meilisearch 均 healthy；`/health` 返回 ready。
- 内置浏览器验证：新增 API 表单展示 temperature 发送开关和自动候选资格；DeepSeek1/2 展示“仅人工使用”；任务页展示两个明确运行方式，素材库 Agent 保持 DeepSeek1 主和 1 个备用；页面请求成功且无空白或网络失败状态。
- 真实 Provider 验证：在健康度页面选择 DeepSeek1 和“素材库 Agent：业务解释”执行最小 JSON 探针，页面返回“单个 API 测试完成”，健康 API 从 8 增至 9，24h 调用增加 1 且失败数不变。

### 当前限制

- 第三方中转站仍可能真实超时、限流或宕机；本轮保证的是错误能够被准确分类、自动模式可降级、人工配置不会被瞬时故障静默抹掉，而不是伪造“第三方永不失败”。

---

## 2026-08-28：API 库存与任务调度职责分离（D229）

### 本轮目标

- 修正 D228 把模型与固定任务绑定的错误抽象。
- 让未来新增任何中转站、密钥和模型在测试保存后立即进入全部人工选择列表，无需改代码。
- 保持自动调度、人工指定和任务级屏蔽的边界清晰且可组合。

### 已确认边界

- API 管理只负责可用模型库存和全局“加入自动调度池”开关，不再维护模型固定任务范围。
- 人工指定可以选择任意已启用 API，即使该 API 关闭了自动分配。
- 自动调度只选择已启用且加入自动调度池的 API，再应用当前任务自己的屏蔽名单和健康容量排序。
- 任务屏蔽名单只影响自动模式；人工模式由主 API 和备用池完全接管。
- 旧 `task_scope_json` 暂留数据库兼容，不再作为运行时门槛或管理页面配置。

### 完成内容

- 后端调度策略移除 `task_scope_json` 过滤；自动模式只检查 active、`auto_assign_enabled`、当前任务屏蔽名单和既有健康容量排序。
- 人工主 API/备用池允许选择任意 active API，不要求开启自动分配，也不受旧任务范围限制；disabled API 仍禁止保存为人工主备。
- API 管理移除新增和已有 API 的“任务范围”配置；新增表单保留“加入自动调度池”，已有 API 列表新增“自动调度/仅人工指定”即时切换。
- 调度配置的主 API、备用池和自动屏蔽列表统一展示所有 active API，不再按旧任务范围过滤。
- 当前 DeepSeek1/DeepSeek2 已设为 `auto_assign_enabled=false` 并清空旧 `task_scope_json`；素材库 Agent 仍为人工主 `deepseek1`、备用 `deepseek2`。

### 修改文件

- `backend/app/services/api_center_runtime_policy.py`
- `backend/app/services/api_center_service.py`
- `backend/tests/test_api_center.py`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无 Alembic 迁移，保留旧字段保证历史数据库兼容。
- 当前本地数据只调整 DeepSeek1/DeepSeek2 的自动调度开关和已废弃任务范围，不改 API 地址、模型、密钥、健康记录或素材业务数据。

### 验证结果

- 后端 API 中心专项：`26 passed`；后端全量：`316 passed`。
- Ruff 通过；Pyright `0 errors / 1 existing warning`，warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- Docker backend/web 已重建，backend/web/postgres/meilisearch 均 healthy，`http://127.0.0.1` 返回 200。
- 运行时验证：`asset_agent_chat` 人工候选为 DeepSeek1/DeepSeek2；其他八个自动任务候选均不包含 DeepSeek。
- 内置浏览器验证：九个任务的人工主 API 下拉均包含全部 10 个 active API；API 管理显示 DeepSeek1/2 为“仅人工指定”；素材库 Agent 主 API 为 DeepSeek1、备用池 1 个；控制台无错误。

### 与 D228 的关系

- D229 修订 D228 的任务范围硬边界；D228 保留为历史记录，不再作为当前实现口径。
- DeepSeek1/DeepSeek2 作为当前专用模型关闭全局自动分配，并继续由素材库 Agent 人工指定；未来替换成 GPT 或其他模型只需在页面切换人工主备 API。

---

## 2026-08-28：API 任务范围与调度边界收敛（D228）

### 本轮目标

- 解决专用模型需要在其他任务逐个屏蔽的问题。
- 确认 DeepSeek1/DeepSeek2 只用于素材库 Agent，不会被搜索、上传分析、动态推荐理由等其他任务调用。
- 避免“调度页保存成功，但运行时未分配”的前后端边界错位。

### 完成内容

- API 管理新增 API 表单增加“可用任务范围”，新增 Key 时直接选择它能跑哪些任务。
- API 列表新增“任务范围”编辑器，已有 Key 也可在 API 管理中直接调整可用任务。
- 调度配置页按当前任务过滤主 API、备用池和自动调度屏蔽列表，只展示该任务可用的 API。
- API 列表展示每个 Key 的可用任务范围，便于检查专用模型边界。
- 后端 `update_slot` 增加任务范围和启用状态校验；不支持当前任务的 API 不能保存为人工主/备用 API。
- 当前数据库中 DeepSeek1/DeepSeek2 已收敛为仅允许 `asset_agent_chat`；素材库 Agent 人工指定 DeepSeek1 + DeepSeek2，搜索和动态推荐理由调度均不会选中 DeepSeek。

### 修改文件

- `backend/app/services/api_center_service.py`
- `backend/tests/test_api_center.py`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无 Alembic 迁移。
- 当前本地数据修正：DeepSeek1/DeepSeek2 的 `task_scope_json` 改为 `["asset_agent_chat"]`；其他任务槽位未保留 DeepSeek 主/备用引用。

### 验证结果

- 后端 API 中心专项：`25 passed`。
- 后端全量：`315 passed`。
- 后端 Ruff：通过。
- 后端 Pyright：`0 errors / 1 existing warning`，该 warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- 运行时调度验证：`asset_agent_chat` 选中 DeepSeek1/DeepSeek2；`search_system_routing` 与 `search_result_recommendation_reason` 未选中 DeepSeek。

### 剩余问题与下一步

- 任务范围是专用模型的主边界；自动调度屏蔽只用于同一任务内临时排除某些候选 API。
- 新增和已有 API 的任务范围都已在 API 管理闭环；后续不需要为专用模型到其他任务逐个屏蔽。

---

## 2026-08-27：API 中心温度探测与任务屏蔽（D227）

### 本轮目标

- 让管理员不再靠猜测判断新 API 的 `temperature`，可在 API 管理新增 API 表单中先测试并回填可用值，再由管理员确认保存。
- 在智能调度配置中按任务屏蔽不希望被自动调用的 API，让其余符合任务范围和健康容量要求的 API 继续自由调度。
- 保持 API 中心作为唯一运行时入口，不改变搜索语义、素材关系或业务事实。

### 完成内容

- 新增未保存 API 温度探测接口：按当前温度和常见候选值发起最小 JSON 探针，首个成功值回填到新增 API 表单，不创建 API、不保存 Key、不写健康快照或调用链路。
- 新增 API 表单的温度探测请求等待时间按“单次探测超时 × 候选温度数量 + 缓冲”计算，避免前端全局 30 秒超时先断开并误报网络请求失败。
- 温度兼容探测固定为最多 5 个候选、单候选最多等待 12 秒；前端按同一上限等待并区分“请求等待超时”和“网络请求失败”，不再靠 30/60/120 秒猜测。
- 新增 API 表单要求当前地址、模型、密钥测试通过后才能保存；任一关键字段变更后，保存按钮重新锁定，避免未经验证的 Key 进入调度池。
- 保存 API 和未保存温度探测均校验 `http/https` API 地址和非空模型，明显错误配置直接返回明确错误。
- 已保存 API 的内部温度调优能力保留，探测记录写入 `model_api_health_checks` 和 `model_call_traces`，调用链路用 `outputSummary.kind=temperature_probe` 区分。
- `model_routing_slots` 新增任务级屏蔽名单；自动调度筛选候选 API 时会排除当前任务屏蔽的 Key。
- 删除 API 时同步清理主 API、备用池和屏蔽名单引用。
- 前端 API 管理新增 API 表单新增“测试并匹配温度”按钮；健康度监测只保留巡检和状态反馈；智能调度配置新增“自动调度屏蔽”选择器。
- OpenAPI 生成类型和手写前端类型已同步。

### 修改文件

- `backend/alembic/versions/20260827_0027_api_center_slot_exclusions.py`
- `backend/app/models/api_provider.py`
- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_service.py`
- `backend/app/api/v1/api_center.py`
- `backend/tests/test_api_center.py`
- `client/src/api/admin.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 新增并应用 `20260827_0027_api_center_slot_exclusions.py`。
- Docker PostgreSQL 当前 revision：`20260827_0027`。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 API 中心专项：`24 passed`。
- 后端 API 中心 + Provider 专项：`41 passed`。
- 后端全量：`314 passed`。
- 后端 Ruff：通过。
- 后端 Pyright：`0 errors / 1 existing warning`，该 warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- OpenAPI 类型已重新生成。
- Docker backend/web 已重建，backend/web/postgres/meilisearch 均 healthy，`http://127.0.0.1` 返回 200。
- 内置浏览器刷新 `/admin/api-center`，确认 API 管理新增表单内渲染“测试并匹配温度”，健康度监测不再展示温度匹配入口，智能调度配置仍渲染“自动调度屏蔽”控件。

### 剩余问题与下一步

- 温度探测当前以“首个可用候选值”为准，不对回答质量做业务评测；模型可用不等于搜索准确性变化。
- 屏蔽名单是任务级自动调度候选收口；如果关闭自动调度，仍由人工主 API/备用池 override。

---

## 2026-08-27：素材库 Agent 自然日记忆重置（D226）

### 本轮目标

- 按用户确认，把素材库 Agent 从“滚动 24 小时过期”改成“每天 00:00 统一清空”。
- 保持每个用户一个独立 Agent 沙箱，用户内当天可有多个互不干扰的聊天记录。
- 清空后只保留一个空白新对话，避免昨天的记忆进入新一天。

### 完成内容

- 后端按 Asia/Shanghai 自然日判断当前 Agent 会话是否仍属于今天。
- 每次列表、创建、更新、删除或发送消息前，清理当前用户今天以前的 Agent 会话和已过期会话。
- 当清理后列表为空时，自动创建一个只含默认问候的空白新对话。
- 保留用户当天最多 20 个会话的上限。
- 跨午夜页面继续拿昨天同用户会话 ID 发消息时，会自动进入新的空白会话，不继承昨天消息。
- 跨用户或管理员继续他人会话仍按不存在处理。
- 前端文案改为“今日记录”，清空时间展示为下一次 00:00。

### 数据迁移

- 无数据库迁移。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 Agent 专项：`3 passed`。
- 后端全量：`310 passed`。
- 后端 Ruff：通过。
- 后端 Pyright 应用代码：`0 errors / 1 existing warning`，该 warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 Agent 会话模型 Vitest 专项：`1 file / 3 tests passed`。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- `git diff --check`：通过。

### 剩余问题与下一步

- 当前为请求触发式清理；无人访问时不额外启动定时任务，但用户在新一天首次访问或发消息会立即看到空白 Agent。

---

## 2026-08-26：架构边界收口与使用统计（D225）

### 本轮目标

- 以当前打开的本地项目为唯一基准，不采纳之前共享链接中疑似回滚生成的代码。
- 收口 API 中心与 `.env` 的边界，确保管理员页面是唯一运行时管理入口。
- 确认素材库 Agent 的用户级沙箱和会话隔离关系。
- 为管理员新增按用户、今日和区间查看登录、访问、下载使用量的后台入口。

### 完成内容

- 新增 `api_center_settings`，记录 `.env` 初始导入是否完成。
- `.env` 只在 API 中心没有任何凭据且从未导入时作为一次性迁移来源；导入或管理员手动新增 API 后，后续不再自动导入。
- 新增 API 删除接口；删除 Key 时同步清理调度槽位主备引用和运行容量状态。
- 新增 `user_usage_events`，记录 `login`、`page_view`、`download` 三类事件。
- 登录成功、页面访问和成功下载进入统一使用量事件；原图片 `downloadCount` 继续保留。
- 新增管理员“使用统计”页面，支持今日、7 天、30 天和 90 天聚合。
- 确认素材库 Agent 继续按 `current_user.id` 过滤所有会话读写：每个用户是沙箱，用户内每个聊天记录彼此隔离并从属于该用户。

### 数据迁移

- 新增并应用 `20260826_0026_usage_and_api_center_settings.py`。
- 本地 SQLite 当前 revision：`20260826_0026`。
- 当前本地库：40 个素材组、40 张图片、16 个业务概念、55 条人工 accepted 关系。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 API 中心、使用统计和下载计数专项：`23 passed`。
- 后端全量：`309 passed`。
- 后端 Ruff 通过。
- 后端 Pyright：`0 errors / 1 existing warning`，该 warning 为既有 `search_branch_runner.py` TypeVar 提示。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build 通过。
- OpenAPI 类型已重新生成。
- `git diff --check` 通过。
- 内置浏览器已打开 `/admin/usage`，页面渲染正常，控制台无错误；刷新后页面访问统计进入汇总。

### 剩余问题与下一步

- 使用统计当前记录聚合事件，不做独立会话时长推算。
- 若未来多 backend 部署，需要重新评估 API 中心容量状态和使用统计写入的横向扩展策略。

---

## 2026-08-26：API 中心健康明细展示统一（D224）

### 本轮目标

- 解决健康度监测页和调用链路日志重复展示同一批健康检查明细的问题。
- 让管理员明确区分“健康状态快照”和“真实调用明细”的用途。

### 完成内容

- 健康检查完成后继续保存 `model_api_health_checks` 状态快照，供健康状态、调度排序和指标计算使用。
- 同一次真实探测继续写入 `model_call_traces`，并以 `outputSummary.kind=health_check` 标识调用明细。
- 健康度页面移除底部历史列表，只保留自动监测、一键巡检、定时巡检和结果反馈。
- 健康度页面增加“查看调用链路日志”入口，所有 Provider、模型、任务、状态、耗时和错误摘要统一从调用链路日志查看。
- `ApiCenterSummary`、前端 API 类型和 OpenAPI 类型移除 `recentHealthChecks`，避免维护第二套展示契约。

### 业务和架构边界

- 不删除 `model_api_health_checks` 表；它仍是调度和健康状态的内部数据源。
- 不新增第二套调用日志，不改变 Provider、API 调度、容量算法、搜索链路或业务事实。
- 不记录完整 API Key、Authorization、Prompt、图片字节或 Agent 私有聊天正文。

### 数据迁移

- 无数据库迁移。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 API 中心与文档一致性专项：`22 passed`。
- 后端全量：`305 passed`；Ruff 通过；Pyright `0 errors / 1 existing warning`。
- 前端 TypeScript、ESLint、Vitest `15 files / 48 tests passed`、production build 通过。
- `git diff --check` 通过；本地容器重建和管理员页面复核完成。

### 剩余问题与下一步

- 健康状态快照与调用明细是两个用途不同的记录，不能为了前台去重而删除健康快照。
- 继续观察真实服务器上一键巡检后调用链路日志的展示顺序和可读性。

---

## 2026-08-26：单服务器 Provider 请求取消收口（D222）

### 本轮目标

- 解决外部模型请求超过搜索分支预算后，本机只停止等待、底层同步 HTTP 仍可能继续运行的问题。
- 保持当前单 backend 部署，不为尚未存在的多 backend 扩展引入共享容量租约。

### 完成内容

- 新增请求级 `CancellationSignal`，从搜索分支超时/取消一路传到 Provider。
- `OpenAICompatibleModelProvider` 为当前请求注册取消回调；取消时关闭 `httpx.Client`，清理本机连接池和传输，并把取消/超时竞态归一为取消状态。
- 兼容响应格式的第二次请求前再次检查取消，避免已经取消后又发起一次请求。
- `FallbackModelProvider` 和 API 中心调度 Provider 在取消后停止继续尝试其他 Provider/Key。
- 查询理解服务和 `SearchBranchRunner` 已统一使用正式请求级 Provider 契约，不再保留无取消参数的生产兼容分支。
- API 中心在等待并发名额、请求开始前已取消、或没有可用 API 时也会立即结束，不再把取消请求拖到任务预算结束。
- 容量压测脚本同步到显式 `initialize_runtime()` 和新的调度 Provider 接口，保持维护工具与运行代码一致。

### 业务和架构边界

- 不改变六大体系、16 个核心卖点、证明点、人工 accepted 关系、召回、排序、搜索结果展示和 API 容量算法。
- “取消完成”的验收口径是：本机不再继续等待、HTTP 连接被关闭、后续 fallback 不再发起。
- 不能把本机关闭连接描述成撤销 Provider 服务端已经开始的内部推理；如果底层 SDK 忽略关闭信号，线程仍需等待底层调用返回。

### 数据迁移

- 无数据库迁移。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 `./.venv/bin/python -m pytest tests -q`：`305 passed`。
- 后端 `./.venv/bin/ruff check app tests scripts`：通过。
- 后端 `./.venv/bin/pyright`：`0 errors / 1 existing warning`。
- 前端 typecheck、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- `git diff --check`：通过。

### 剩余问题与下一步

- 继续观察真实服务器上的 Provider 取消、连接释放和调用台账状态；不宣称能撤销远端服务端推理。
- 只有未来增加第二个 backend 时，才重新评估把进程内容量账本迁移为共享租约。

---

## 2026-08-26：Provider 正式契约收口（D223）

### 本轮目标

- 删除 Provider 调用链上已经没有必要的旧方法、实例级遥测状态和动态签名兼容。
- 让每次调用的业务结果、attempts 和取消信号都通过明确的请求级协议传递。

### 完成内容

- 删除 `generate_json_with_attempts` 和 `generate_validated_json_with_attempts`。
- 删除 Provider/Service 实例级 `last_attempts`、`last_call_attempts` 及其兼容读取。
- 删除依赖 `inspect.signature` 的动态兼容判断；搜索理解、候选复核和推荐理由统一依赖正式能力协议。
- 所有 Provider、API 中心调度、Fallback、AiService、搜索理解、素材库 Agent、推荐理由、脚本和测试替身统一使用 `ModelCallResult` 与请求级 `CancellationSignal`。
- 修复查询理解结果被多包一层 `ModelCallResult` 后，搜索响应丢失 `search_understanding` 的真实问题。

### 业务和架构边界

- 不改变六大体系、16 个核心卖点、证明点、人工 accepted 关系、召回、排序、API 中心容量算法或单服务器部署边界。
- `.env` 一次性导入仍是部署迁移入口；API 中心仍是日常 API Key 的唯一管理入口。
- 本轮只删除已无调用方的正式契约兼容路径，不新增数据库迁移，也不改变业务事实。

### 数据迁移

- 无数据库迁移。
- 无正式素材、概念、公共话术或人工 accepted 关系写入。

### 验证结果

- 后端 `./.venv/bin/python -m pytest tests -q`：`305 passed`。
- 后端 `./.venv/bin/ruff check app tests scripts`：通过。
- 后端 `./.venv/bin/pyright`：`0 errors / 1 existing warning`。
- 前端 typecheck、ESLint、Vitest `15 files / 48 tests passed`、production build：通过。
- `git diff --check`：通过。

### 剩余问题与下一步

- 取消仍只能停止本机等待、连接和后续 fallback，不能撤销外部 Provider 已经开始的内部推理。
- 当前单 backend 的进程内容量账本继续符合部署边界；只有未来横向扩展时才评估共享租约。
- 仍需在真实服务器完成 Provider 取消、连接释放和调用台账的运行观察。

---

## 2026-08-25：正式素材身份码与精确查找（D210）

### 产品确认

- 上传成功后由系统自动分配素材身份码，不调用大模型，不依赖图片内容识别。
- 素材组使用长期稳定的 `asset_code`，具体图片版本使用唯一的 `version_code`。
- 普通业务端继续只保留一个搜索框；识别码和分享链接是同一个入口的确定性查找分支。
- 分享链接仍需登录并经过当前角色权限校验，不变成公开下载地址。

### 实施边界

- 标题修改、主图替换、延展尺寸增加和业务关系调整不改变素材码。
- 删除或永久清理后身份码不回收、不重新分配。
- 历史素材通过迁移补齐身份码。
- 精确身份查找优先于语义搜索；身份查找失败时不把码交给大模型。

### 当前进度

- 已完成正式决策、迁移命名、现有上传/版本/搜索入口审计、数据库字段与不可复用登记、后端精确解析、前端展示复制、分享路由和历史数据补码。
- 迁移 `20260825_0025_asset_identity_codes.py` 已执行，本地数据库已从 `20260825_0024` 升级到 `20260825_0025`。
- 身份码专项、架构护栏和 Phase 5 回归共 `35 passed`；新增及受影响后端文件 Ruff 通过。
- 前端 OpenAPI 类型已重新生成，typecheck、lint、production build 通过。
- 全量后端仍有 9 项既有搜索意图校准测试失败，集中在当前工作区原有语义规则，本轮未改动这些规则。
- 内置浏览器标签页未能加载本地开发地址，因此未将浏览器走查结果冒充为通过；身份码主链路已由接口和自动化测试覆盖。

---

## 2026-08-25：搜索结果卡悬浮径向操作环（D211）

### 本轮目标

- 让图片结果卡默认保持干净，减少四个常驻操作按钮对图片内容的干扰。
- 在用户靠近卡片时提供轻量、有上下文关系的快捷操作。

### 完成内容

- 新增可复用 `RadialActionMenu`，将发送到素材库 Agent、项目夹、复制身份码和下载收进右上角开放式操作环。
- 操作环使用轻描边轨道和 180～240ms 的收拢/展开动效；卡片 hover、键盘 focus 和触摸设备均可触达。
- 版本/尺寸选择继续使用标准下拉并保留现有下载链接，未改变下载尺寸、身份码复制、项目夹或 Agent 事件。
- 普通浏览卡片暂不接入该操作环，保持其现有操作边界，避免把低频版本/项目夹能力扩散到无对应数据上下文的页面。
- 增加 `prefers-reduced-motion` 降级，关闭操作环过渡。

### 修改文件

- `client/src/pages/ImageHome/RadialActionMenu.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/ScoredImageCard.tsx`
- `client/src/tailwind-theme.css`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm run build --prefix client`：通过。
- Vitest 与内置浏览器走查待本轮结束前完成。

### 遗留问题

- 当前操作环接入搜索结果卡；普通浏览卡仍使用原有轻量按钮布局。
- 当前 Tooltip 复用原生 `title` 和 `aria-label`，未新增独立 Tooltip 组件。

### 下一步

1. 运行前端 Vitest。
2. 在首页搜索结果中走查默认态、hover/focus 展开态和触摸降级。

---

## 2026-08-25：图片卡操作说明与完整推荐文案（D212）

### 本轮目标

- 让操作环中的 Icon 同时显示短文字，降低第一次使用时的理解成本。
- 让首页普通瀑布流卡片和搜索结果卡片使用一致的身份码、Agent、下载操作环。
- 让每张搜索结果卡完整展示自身推荐点和动态推荐说明。

### 完成内容

- 径向操作环展开后显示“发送到 Agent、加入项目夹、复制身份码、下载”等短标签；默认状态仍不显示工具栏。
- 普通网格卡片和瀑布流卡片接入同一 `RadialActionMenu`，保留现有图片跳转、动图预览、设计师下载统计和权限边界。
- 普通瀑布流新增当前图片下载动作和身份码复制动作，使用现有图片字段与下载接口，不新增后端接口。
- 搜索结果推荐点、主推荐说明和补充说明移除前端两行截断，改为自动换行完整展示。
- 修正菜单外溢与图片容器 `overflow-hidden` 的关系，保证右上角操作环不会被图片裁掉。

### 修改文件

- `client/src/pages/ImageHome/RadialActionMenu.tsx`
- `client/src/pages/ImageHome/ImageCard.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/ScoredImageCard.tsx`
- `client/src/tailwind-theme.css`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm test -- --run --prefix client`：45 项通过。
- `npm run build --prefix client`：通过。
- 内置浏览器走查搜索结果卡：文字操作环、完整推荐说明和下载入口正常。

### 遗留问题

- 推荐说明现在按内容自然撑开卡片高度，瀑布流列高差会比截断版本更明显，这是完整可读性换来的布局结果。

### 下一步

1. 继续观察真实业务搜索中的长推荐文案，必要时只优化文字层级和卡片宽度，不恢复省略截断。

---

## 2026-08-25：径向操作环节点重排（D213）

### 本轮目标

- 修复带文字操作环沿原短半径堆叠、标签互相覆盖的问题。
- 让搜索结果卡和普通首页卡片在 3 动作、4 动作两种情况下都保持稳定节奏。

### 完成内容

- 操作环扩大开放轨道，并改为四个动作节点的固定绝对落点。
- 4 动作卡片分别安排复制身份码、加入项目夹、发送到 Agent、下载；不再通过短距离负位移叠加。
- 3 动作卡片通过 `data-action-count` 使用独立坐标，移除项目夹时不留下明显空位。
- 操作环 hover/focus、触摸设备和 reduced-motion 行为保持不变。

### 修改文件

- `client/src/pages/ImageHome/RadialActionMenu.tsx`
- `client/src/tailwind-theme.css`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm test -- --run --prefix client`：45 项通过。
- `npm run build --prefix client`：通过。
- 内置浏览器走查：4 个文字动作节点不再重叠，3/4 动作布局规则已生效。

### 遗留问题

- 操作环仍会在卡片右上外沿占用一定空间，这是文字可读性与点击区域的必要空间。

---

## 2026-08-25：Agent 闭合入口上移（D214）

### 本轮目标

- 解决首页右下角 Agent 机器人位置过低，压近搜索反馈和输入框的问题。

### 完成内容

- 闭合态 Agent 容器由 `bottom-6` 调整为 `bottom-14`，整体上移约 32px。
- 问候气泡与机器人入口同步上移。
- 打开后的聊天面板固定位置不变。

### 修改文件

- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm test -- --run --prefix client`：45 项通过。
- 内置浏览器走查：入口距离底部约 61px，不再贴近输入区。

### 遗留问题

- 无。

---

## 2026-08-25：Agent 闭合入口再次上移（D215）

### 本轮目标

- 在 D214 基础上再将首页闭合态 Agent 入口上移 40px。

### 完成内容

- `AssetAgentWidget` 的闭合态容器由 `bottom-14` 调整为 `bottom-24`。
- 机器人和问候气泡同步上移。
- 打开后的聊天面板位置不变。

### 修改文件

- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- 待本轮前端快速检查完成。

---

## 2026-08-25：素材库 Agent 彩色流光反馈（D209）

### 设计确认

- 用户希望白色变形球体周围偶尔出现彩色流光，让 Agent 更灵动、更有趣。
- 彩色只作为短时状态反馈：沿球体外圈扫过后消失，不持续发光，不改变整体黑白暖灰主题。
- 不复制录屏或外部页面中的角色、SVG 和未知许可资源，继续使用项目原创 CSS。

### 完成内容

- Agent 光球新增独立的彩色边缘流光层，使用柔和的青、蓝、紫、粉、黄渐变。
- 默认约 14 秒低频触发一次，流光只在短时间内出现。
- 思考状态将节奏缩短到约 8 秒一次，让等待回复时更有反馈，但仍保持克制。
- 流光只作用于球体边缘，不遮挡眼睛、嘴巴或聊天面板，不产生布局尺寸变化。
- `prefers-reduced-motion: reduce` 下关闭彩色流光动画。

### 修改文件

- `client/src/components/PianctonAgentMark.tsx`
- `client/src/tailwind-theme.css`
- `docs/UX_UI_DESIGN_SYSTEM.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 边界

- 本轮只改变 Agent 前端表现，不修改后端、会话、权限、模型调用、搜索排序或素材业务事实。
- 彩色流光不是新的品牌主色，也不承载业务状态含义；后续如需更多状态表达，仍应优先使用现有表情和黑白暖灰动效。

---

## 2026-08-25：素材库 Agent 球体形变反馈（D208）

### 录屏复核结论

- 参考机器人真正的灵动感来自球体本身的形态变化，不只是眼睛或嘴巴动画。
- 录屏中包含白色球体、黑色球体、细长形态和球体回弹，眼睛始终像贴在球面上跟随注视。
- 本项目不直接复制录屏中的角色、SVG 或外部素材，只吸收“形体响应状态”的交互方式。

### 完成内容

- Agent 光球根据鼠标位置增加轻微横向偏移、上下偏移和倾斜。
- 光球使用非圆形 `border-radius` 周期形变，避免长期保持静态圆形。
- 唤醒状态使用弹性放大和回位。
- 思考状态使用压缩、聚焦和轻微上下呼吸。
- 完成状态使用短促回弹，配合微笑表情。
- 眼睛和瞳孔继续跟随指针，脸部整体随球体产生同步偏移。

### 验证结果

- `cd client && npm run typecheck`：通过。
- `cd client && npm run lint`：通过。
- `cd client && npm test -- --run`：14 个测试文件、45 项通过。
- `cd client && npm run build`：生产构建通过。
- `git diff --check`：通过。
- 内置浏览器重新打开首页并展开 Agent 面板：布局和聊天内容正常。

### 边界

- 本轮只改变 Agent 前端动效，不修改后端、会话、权限、模型调用和素材业务事实。
- 形变幅度保持克制，避免遮挡面板内容、造成布局抖动或影响移动端点击。

---

## 2026-08-25：素材库 Agent 灵动表情交互（D207）

### 完成内容

- 保留现有原创暖白光球，不引入参考页面中的外部角色视觉或素材。
- 光球眼睛根据全局指针位置平滑跟随，鼠标移开或窗口失焦后回到中性注视。
- 眨眼由单一固定节奏改为自然双眨，减少“静态图标感”。
- 增加状态表情：
  - 唤醒：打开 Agent、创建新对话时放大眼睛并抬起脸部。
  - 思考：等待模型回复时切换专注嘴型并显示旋转光环。
  - 完成：回复成功后短暂显示更明显的微笑。
  - 异常：请求失败后短暂回到唤醒表情，提示 Agent 仍在等待下一次输入。
- 增加 `prefers-reduced-motion` 支持，用户关闭动态效果时停止循环动画和过渡。

### 修改文件

- `client/src/components/PianctonAgentMark.tsx`
- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `client/src/tailwind-theme.css`
- `docs/UX_UI_DESIGN_SYSTEM.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `cd client && npm run typecheck`：通过。
- `cd client && npm run lint`：通过。
- `cd client && npm test -- --run`：14 个测试文件、45 项通过。
- `cd client && npm run build`：生产构建通过。
- `git diff --check`：通过。
- 内置浏览器走查首页悬浮入口和展开后的 Agent 面板：正常；会话菜单、消息区和输入区未受影响。

### 边界

- 本轮只改变 Agent 的前端状态表达，不改变后端回答质量、权限、个人会话隔离、24 小时过期、素材事实或搜索排序。
- 内置浏览器脚本环境不支持直接构造 `PointerEvent`/`MouseEvent`，因此鼠标跟随以实际页面渲染走查和代码路径确认；不影响真实浏览器中的全局 `pointermove` 监听。

---

## 2026-08-25：API 中心智能调度边界与一键巡检（D196）

### 完成内容

- 明确“智能调度”的真实含义：当前不是生成式 Agent 在实时判断，而是可解释、可复现的算法调度。
- 页面新增说明卡，直接解释：
  - 实时调度不是 Agent 玄学，而是按任务范围、状态、健康度、优先级和最近耗时选择 Key。
  - 体系路由和卖点识别等在线链路必须稳定，不交给 Agent 临场发挥。
  - Agent 更适合后续做巡检总结、异常解释、容量建议等离线运维辅助。
- 健康度监测新增“一键巡检所有 Key”：
  - 后端新增 `POST /api/admin/api-center/health-checks/run-all`。
  - 默认巡检所有非停用 Key。
  - 每个 Key 使用任务范围里的代表任务发起最小 JSON 探针。
  - 返回 checked/ok/failed 汇总和逐条检查结果。
  - 不记录完整 Key、完整 Prompt、图片或完整外部响应。
- 健康度来源在页面上拆成三类：
  - 自动监测：真实模型调用自动回写健康状态、耗时和错误摘要。
  - 一键巡检：管理员按钮主动巡检所有非停用 Key。
  - 定时巡检：后端批量巡检接口已可被服务器 cron 或任务队列定时调用。

### 修改文件

- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_service.py`
- `backend/app/api/v1/api_center.py`
- `backend/tests/test_api_center.py`
- `client/src/api/admin.ts`
- `client/src/types/api.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 验证结果

- `cd backend && .venv/bin/python -m ruff check app/services/api_center_service.py app/api/v1/api_center.py app/schemas/api_center.py tests/test_api_center.py`：通过。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py -q`：8 passed。
- `cd backend && .venv/bin/python -m pyright`：0 errors，保留既有 `search_branch_runner.py` TypeVar warning。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py tests/test_ai_provider.py::test_fallback_chain_exposes_attempt_count_for_search_budget tests/test_phase4_search_orchestration.py::test_phase4_staged_model_uses_independent_layer_budgets tests/test_phase4_search_orchestration.py::test_phase4_candidate_review_filters_top_candidates -q`：11 passed。
- `npm run lint --prefix client`：通过。
- `npm run typecheck --prefix client`：通过。
- `docker compose up -d --build backend web`：通过，前端生产 build 成功。
- `curl -sf http://127.0.0.1/health`：返回 ready；backend、web、postgres、meilisearch 均 healthy。

### 边界

- 本轮没有把生成式 Agent 接入实时 Key 选择；这是刻意保留的稳定性边界。
- 定时巡检的后端批量接口已具备，生产部署时还需要接服务器 cron、worker 或任务队列来定时触发。
- 真实并发 hedged request 尚未接入；当前仍是健康优先 + 顺序 fallback + 总预算不放大。

---

## 2026-08-24：API 中心调度接入运行链路（D195）

### 完成内容

- 把 API 中心从“管理页/日志页”推进为运行时 Provider 调度入口：
  - 搜索四层 Skill：体系路由、卖点识别、证明点识别、候选图片复核
  - 上传主图：图片语义分析
  - 上传前：素材搜索话术生成
- 新增环境 Key 自动导入：系统会读取原环境配置中的 4 个模型 Key 槽位，自动同步为 API 中心里的脱敏 Key 记录：
  - 环境导入 · 搜索主 Key
  - 环境导入 · 搜索备用 Key
  - 环境导入 · 主图分析 Key
  - 环境导入 · 话术生成 Key
- 新增 API 中心调度 Provider：`AiService` 不再直接知道具体 Key；每次模型请求按 `request.task` 到 API 中心选择候选 Key，再调用 OpenAI-compatible Provider。
- 自动调度规则：
  - 只选择 `active`、开启 `auto_assign_enabled`、任务范围匹配的 Key。
  - 优先级顺序：健康状态 `ok` > 未知冷启动 > 失败状态；同一状态下按 priority、最近耗时和创建时间排序。
  - 每个任务最多选择 4 个候选 Key。
  - 成功调用会更新最近健康状态；失败会记录安全错误摘要并把 active Key 置为 `cooling`，避免继续优先使用。
  - 若 API 中心没有可用 Key，则回退旧环境变量 Provider，保障迁移阶段不成为单点故障。
- 搜索外层预算不再按 Key 数量放大：调度器内部负责 fallback，避免多 Key 时把整体搜索耗时线性拉长。
- 前端 API 中心调整为“自动调度为主、人工指定为高级 override”：
  - 页面说明改为 Key 池自动分配。
  - “调度配置”改为“智能调度配置”。
  - 增加“自动调度/人工指定”开关。
  - 解释 `20` 为“超时秒数”，`0.2` 为“输出稳定度/temperature”，减少纯工程参数感。

### 修改文件

- 后端：
  - `backend/app/services/api_center_service.py`
  - `backend/app/repositories/api_center_repository.py`
  - `backend/app/api/dependencies.py`
  - `backend/tests/test_api_center.py`
- 前端：
  - `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- 文档：
  - `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
  - `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 验证结果

- `cd backend && .venv/bin/python -m ruff check app/services/api_center_service.py app/api/dependencies.py tests/test_api_center.py`：通过。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py -q`：7 passed。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py tests/test_ai_provider.py::test_fallback_chain_exposes_attempt_count_for_search_budget tests/test_phase4_search_orchestration.py::test_phase4_staged_model_uses_independent_layer_budgets tests/test_phase4_search_orchestration.py::test_phase4_candidate_review_filters_top_candidates -q`：10 passed。
- `cd backend && .venv/bin/python -m pyright`：0 errors，保留既有 TypeVar warning。
- `npm run lint --prefix client`：通过。
- `npm run typecheck --prefix client`：通过。
- `docker compose up -d --build backend web`：通过，前端生产 build 成功。
- `curl -sf http://127.0.0.1/health`：返回 ready；backend、web、postgres、meilisearch 均 healthy。

### 边界

- 本轮尚未实现真正并发的 hedged request；当前是健康优先 + 顺序 fallback + 总预算不放大。后续如果真实日志显示单 Key 偶发长尾明显，再把 `hedging_delay_ms` 接成“延迟抢跑备用 Key”。
- 当前 `cooling` 是运行失败后的保守降级状态；后续可补定时巡检，把 cooling Key 自动恢复或转 invalid。
- API Key 已在 UI/API/日志中脱敏，但数据库字段仍是明文密钥存储；正式生产前可继续接 KMS/加密字段和更细的操作审计。

---

## 2026-08-24：API 中心与调用链路产品化第一版（D194）

### 完成内容

- 新增后台一级入口“API 中心”，包含 API 实验、API 管理、调度配置、健康度监测和调用链路日志 5 个区域，作为后续公司服务器上维护模型 Key、模型健康和搜索调用链路的明确入口。
- 新增 OpenAI-compatible Key 池数据模型与管理员接口：支持 label、base_url、model、适用任务、优先级、超时、启停和自动分配开关；完整密钥只写入后端存储，不在接口、页面或日志中回显，只展示 preview。
- 新增搜索四层 Skill 运行槽位配置：
  - 第一层：体系路由 `search_system_routing`
  - 第二层：卖点识别 `search_intent_understanding`
  - 第三层：证明点识别 `search_proof_point_understanding`
  - 第四层：候选图片复核 `search_candidate_review`
- 新增手动健康测试：管理员可在 API 实验页选择某个 Key 和任务，执行一次轻量 JSON 生成测试，记录 healthy/degraded/down、耗时和安全错误摘要。
- 新增调用链路遥测：搜索链路会把每层模型 provider attempt 的 task、layer、provider、model、credential label、fallback index、耗时、状态、错误摘要和结构化输出摘要写入 `model_call_traces`，用于后续判断是哪一层慢、哪一个 Provider 不稳定。
- 运行时保持现有 env Provider 优先兼容：第一版先把 Key 池、健康度和链路日志产品化，不直接把 DB Key 池接入线上调度，避免后台误配置变成搜索单点故障；后续等真实健康数据积累后，再接入自动健康调度、冷却和延迟抢跑。

### 修改文件

- 后端模型/迁移/API/服务：
  - `backend/app/models/api_provider.py`
  - `backend/alembic/versions/20260824_0022_api_center.py`
  - `backend/app/schemas/api_center.py`
  - `backend/app/repositories/api_center_repository.py`
  - `backend/app/services/api_center_service.py`
  - `backend/app/api/v1/api_center.py`
  - `backend/app/api/router.py`
  - `backend/app/api/dependencies.py`
- 搜索链路遥测接入：
  - `backend/app/services/search_models.py`
  - `backend/app/schemas/image.py`
  - `backend/app/services/search_diagnostics_service.py`
  - `backend/app/services/query_understanding_service.py`
  - `backend/app/services/search_external_branches.py`
  - `backend/app/services/search_log_service.py`
- 前端后台页面与导航：
  - `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
  - `client/src/types/api.ts`
  - `client/src/api/admin.ts`
  - `client/src/app.tsx`
  - `client/src/components/Layout.tsx`
- 测试：
  - `backend/tests/test_api_center.py`

### 验证结果

- `cd backend && .venv/bin/alembic upgrade head`：通过；本地 SQLite 升至 `20260824_0022`。
- `cd backend && .venv/bin/alembic downgrade 20260805_0021 && .venv/bin/alembic upgrade head`：通过，迁移可回滚再升级。
- `docker compose exec -T backend alembic current`：Docker Postgres 当前为 `20260824_0022 (head)`。
- `cd backend && .venv/bin/python -m ruff check app scripts alembic/versions/20260824_0022_api_center.py`：通过。
- `cd backend && .venv/bin/python -m pyright`：0 errors，保留既有 TypeVar warning。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py -q`：5 passed。
- `cd backend && .venv/bin/python -m pytest tests/test_api_center.py tests/test_phase4_search_orchestration.py::test_phase4_staged_model_uses_independent_layer_budgets tests/test_phase4_search_orchestration.py::test_phase4_candidate_review_filters_top_candidates tests/test_phase4_search_orchestration.py::test_phase4_classmate_usage_query_prefers_official_scale_data_asset -q`：8 passed。
- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `docker compose up -d --build backend web`：通过；backend、web、postgres、meilisearch 均 healthy；`curl -sf http://127.0.0.1/health` 返回 ready。

### 已知边界与下一步

- 本轮不承诺“每次第三方 API 都一定成功”。第三方 Provider 天然可能超时、限流或返回异常；第一版把可观测性、Key 池、健康度和槽位配置补齐，先让问题可定位、可维护，再进入自动调度。
- 下一步可以在真实日志基础上接入 DB Key 池调度：按任务选择 healthy Key，支持冷却、失败熔断、延迟抢跑/hedged request、并发上限、成本与 P95 延迟约束。
- 密钥当前已在 UI/API/日志层面隐藏完整值；生产安全加固可继续接入 KMS/加密字段、操作审计和权限细分。
- 更大范围搜索回归中额外暴露了 3 个既有业务语义边界用例失败，分别涉及考前阶段修复、显式证明点素材筛选、多意图 query_type 判定；这些不属于 API 中心链路本身，后续可按搜索边界专项继续修。

---

## 2026-08-24：数据规模图口语入口校准（D193）

### 完成内容

- 根据业务负责人现场校验，“孩子班上，大概率就有同学在用”应召回“官方数据规模”数据图，含义是全国 1.3 亿学生、400 万教师共同选择等用户规模/数据背书，而不是 AI 定制班。
- `public-phrase-governance.json` 升至 `2026-08-24.10`，新增 `animation-platform-scale-data` 组合信号和 5 条业务校准样例；当前组合信号 33 个，业务校准样例 310 条。
- 同步校内与跨体系校准补充边界：多少人在用、同学在用、学生教师共同选择、用户规模、数据背书和数据图，归 `animation_explanation` 的 `pp_animation_scale_data`；“班上/同学”只有和在用、共同选择或数据背书组合才触发，不因“班”字误归 AI 定制班。
- 本地 SQLite 与 Docker Postgres 中素材组“官方数据规模”已补：
  - 主证明点：`pp_animation_scale_data`
  - 主证据表达点：`ep_school_animation_scale_numbers`
  - manual accepted 素材话术：`孩子班上，大概率就有同学在用`、`孩子班上大概率就有同学在用`、`孩子班上大概率就有同学在用的数据图`、`全国1.3亿学生400万教师共同选择`、`学生和老师共同选择的数据图`
- 新增 Phase4 搜索回归 `test_phase4_classmate_usage_query_prefers_official_scale_data_asset`，确保该句只返回官方数据规模，不被同卖点其他动画素材或 AI 定制班抢位。

### 验证结果

- `backend/.venv/bin/python -m json.tool skills/understand-image-search-intent/references/public-phrase-governance.json >/tmp/piancton-governance.json`：通过。
- `cd backend && .venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py::test_public_phrase_layer_can_only_reference_the_frozen_selling_points tests/test_skill_selling_point_alignment.py::test_business_calibration_examples_route_without_becoming_public_phrases tests/test_query_states_and_negation.py::test_remaining_business_compositions_keep_neighbor_boundaries tests/test_phase4_search_orchestration.py::test_phase4_classmate_usage_query_prefers_official_scale_data_asset -q`：4 passed。
- `cd backend && .venv/bin/ruff check tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- `git diff --check`：通过。
- SQLite 真实搜索验证：`孩子班上，大概率就有同学在用` → 只返回“官方数据规模”，命中 `pp_animation_scale_data` / `ep_school_animation_scale_numbers`。

### 边界

- 不新增核心卖点、证明点、公共话术或数据库 schema。
- 该修正属于校验阶段“小补丁”：真实误命中才补边界和素材 accepted 话术，不开启大规模整句词库。

---

## 2026-08-24：剩余卖点业务搜索语义第二批补齐（D192）

### 完成内容

- 第二批补齐 7 个尚未专项校准的卖点：
  - `new_curriculum_prediction`：新增“课标改革/新考试对象 + 趋势拆解目的”与“新题型/新情境/跨学科对象 + 课程训练动作”两类组合，分别下钻 `pp_exam_reform_trend_alignment` 与 `pp_exam_new_format_course_practice`。
  - `transfer_practice`：新增“出题原理/底层逻辑 + 举一反三迁移目的”与“当前题讲完 + 同类/相似/变式题动作”两类组合，分别下钻 `pp_exam_transfer_principle_first` 与 `pp_exam_transfer_variant_practice`。
  - `expert_planning`：新增专家身份依据与通用长期课程路径两类组合，分别下钻 `pp_cultivation_expert_team_credentials` 与 `pp_cultivation_expert_path_design`。
  - `stage_transition`：新增升学节点衔接课程与小初高连续覆盖两类组合，分别下钻 `pp_cultivation_stage_bridge_courses` 与 `pp_cultivation_stage_full_cycle_coverage`。
  - `universal_method`：新增同题多路径拆解与底层思维长期基础两类组合，分别下钻 `pp_cultivation_method_multiple_paths` 与 `pp_cultivation_method_transfer_foundation`。
  - `human_teacher_supervision`：新增真人诊断阶段计划与持续提醒回访两类组合，分别下钻 `pp_companion_teacher_diagnosis_plan` 与 `pp_companion_teacher_follow_up`。
  - `learning_report`：新增报告核心指标、行为异常线索与家长端交付三类组合，分别下钻 `pp_companion_report_core_metrics`、`pp_companion_report_behavior_signals`、`pp_companion_report_parent_delivery`。
- `public-phrase-governance.json` 升至 `2026-08-24.9`，新增 15 个组合信号和 84 条业务校准样例；当前业务校准样例总数为 305 条。
- 同步考点、同步培养、同步伴学与跨体系校准补充边界：新课标趋势不抢教材同步，专家规划不抢 AI 定制，当前题同类/变式不抢万能解法，个人错题复练不抢举一反三，真人过程管理不抢学情报告，学习周报不抢高频错题。
- 新增查询状态回归 `test_second_remaining_business_compositions_keep_neighbor_boundaries`，覆盖第二批正例与相邻误伤边界。

### 验证结果

- 业务校准脚本：305 条 `businessCalibrationCases` 全通过。
- `cd backend && .venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py -q`：38 passed。
- `cd backend && .venv/bin/python -m pytest tests/test_phase4_search_orchestration.py::test_phase4_short_animation_micro_lesson_query_only_returns_matching_detail tests/test_phase4_search_orchestration.py::test_phase4_proof_point_filters_sibling_assets_but_generic_selling_point_does_not tests/test_phase4_search_orchestration.py::test_phase4_trusted_small_concept_route_skips_optional_reranker -q`：3 passed。
- JSON 校验、Ruff 与 `git diff --check`：通过。

### 边界

- 本轮只增强“意图 → 卖点 → 证明点”的理解，不新增核心卖点、证明点、公共话术、数据库 schema 或素材关系。
- 完整业务长句只进入校准评测，不逐条复制到公共话术或素材话术。
- 若某证明点缺正式已确认素材，搜索应暴露缺口，不用相邻卖点或同卖点兄弟证明图补位。

---

## 2026-08-24：剩余卖点业务搜索语义第一批补齐（D191）

### 完成内容

- 第一批补齐 4 个尚未专项校准的卖点：
  - `animation_explanation`：新增“动画/知识点/课堂听懂 + 讲透拆解/短时补位”与“抽象原理/看不见知识 + 动画可视化呈现”两类组合，分别下钻 `pp_animation_pedagogy_design` 与 `pp_subject_animation_visualization`。
  - `instant_quiz`：新增“学完当前课或知识点 + 立即练测/确认掌握”组合，下钻 `pp_learn_practice_loop`。
  - `ai_tutor_qa`：新增“AI 私教或学习卡住对象 + 即时互动提问/继续追问动作”组合，下钻 `pp_selfstudy_tutor_interactive_qa`。
  - `ai_error_book`：新增个人错题拍照归档、历史错题分类复盘、个人错题后同类题推荐三类组合，分别下钻 `pp_selfstudy_error_photo_capture`、`pp_selfstudy_error_classification_review`、`pp_selfstudy_error_variant_recommendation`。
- `public-phrase-governance.json` 升至 `2026-08-24.8`，新增 7 个组合信号和 54 条业务校准样例；不新增核心卖点、证明点、公共话术或数据库 schema。
- 同步校内、同步自学与跨体系校准补充业务边界：短时间高效复习仍归考前突击，启发式/会提问 AI 老师仍归 AI 拍题精学，周报正确率仍归学情报告，群体高频错题仍归专项培优，当前题后同类题仍归举一反三。
- 新增查询状态回归 `test_remaining_business_compositions_keep_neighbor_boundaries`，覆盖第一批正例与相邻误伤边界。

### 验证结果

- `cd backend && .venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py -q`：37 passed。
- `cd backend && .venv/bin/python -m pytest tests/test_phase4_search_orchestration.py::test_phase4_short_animation_micro_lesson_query_only_returns_matching_detail tests/test_phase4_search_orchestration.py::test_phase4_proof_point_filters_sibling_assets_but_generic_selling_point_does_not tests/test_phase4_search_orchestration.py::test_phase4_trusted_small_concept_route_skips_optional_reranker -q`：3 passed。
- JSON 校验、Ruff 与 `git diff --check`：通过。

### 边界

- 完整业务长句只进入校准评测，不逐条复制到公共话术或素材话术。
- 本轮只增强“意图 → 卖点 → 证明点”的理解，不写数据库素材关系；若某证明点缺正式已确认素材，搜索应暴露缺口，不用相邻卖点或同卖点兄弟证明图补位。

---

## 2026-08-24：极速复习与考前突击边界校准（D190）

### 完成内容

- 将业务负责人补充的 4 条边界样例加入校准评测：
  - `日常快速复习`、`当天学当天复习` → `rapid_preview_review` / `pp_selfstudy_preview_dual_entry` / `ep_selfstudy_fast_review`
  - `明天月考快速复习`、`期末前三天冲刺` → `focused_excellence` / `pp_exam_focus_stage_review`
- 查询状态回归补充上述边界，固定“日常/当天/学完后短时回顾”与“具体考试节点/临考倒计时冲刺”的分流。
- 同步自学知识与跨体系校准补充说明：判断核心不是“快速复习”这几个字，而是对象和时间节点。日常快速复习、当天学当天复习属于极速复习；明天月考、期末前三天、临考、考前等考试节点与复习/冲刺组合属于考前突击。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py::test_business_calibration_examples_route_without_becoming_public_phrases tests/test_query_states_and_negation.py::test_rapid_review_after_class_composition_keeps_neighbor_boundaries tests/test_query_states_and_negation.py::test_exam_stage_composition_does_not_capture_daily_or_reform_review tests/test_phase4_search_orchestration.py::test_phase4_rapid_review_after_class_composition_prefers_review_asset tests/test_phase4_search_orchestration.py::test_phase4_rapid_preview_before_class_composition_prefers_preview_asset tests/test_phase4_search_orchestration.py::test_phase4_exam_stage_composition_prefers_exam_rush_asset_facet -q`：6 passed。
- JSON 校验与 `git diff --check`：通过。
- 本地理解验证：
  - `日常快速复习`、`当天学当天复习` → `rapid_preview_review` / `pp_selfstudy_preview_dual_entry` / `ep_selfstudy_fast_review`
  - `明天月考快速复习`、`期末前三天冲刺` → `focused_excellence` / `pp_exam_focus_stage_review`

### 边界

- 不新增卖点、证明点、公共话术或数据库 schema。
- 不改变 D189 对正式“极速复习”素材缺口的处理：没有正式 `ep_selfstudy_fast_review` 素材时，不用“极速预习”素材补位。

---

## 2026-08-24：极速复习组合语义校准（D189）

### 完成内容

- 新增 `rapid-review-after-class` 组合语义信号，将“极速复习/快速复习/课后复习/知识回顾/快速回顾/学完/学过/当天知识/知识点/复习/回顾/巩固/碎片时间”等已学内容对象，与“快速过一遍/5分钟复习/十分钟复习/碎片化复习/快速巩固/轻量复习/当天复习/快速查漏补缺/快速回忆/重新过一遍/短时间复习/花很少时间复习/快速回顾重点”等短时回顾目的组合识别为 `rapid_preview_review` 下的 `pp_selfstudy_preview_dual_entry`。
- 22 条业务代表搜索进入校准评测，不进入公共话术库，不新增“极速复习”核心卖点或证明点。
- 组合语义信号新增可选 `evidencePointCode`，本轮将极速预习侧标到 `ep_selfstudy_fast_preview`，极速复习侧标到 `ep_selfstudy_fast_review`，用于同证明点内部做素材 facet 分流。
- 同步自学知识与跨体系校准补充边界：课后/学完后短时间回顾重点、巩固当天知识、碎片时间查漏补缺属于极速预习复习的课后复习侧；考试节点前冲刺复习仍归专项培优，教材版本/学校进度仍归同步校内，学习计划/路径仍归 AI 定制学习方案，拍题讲解和个人历史错题长期复盘仍分别归 AI 拍题精学与 AI 错题本。
- 当前真实本地库没有正式“极速复习”素材组，只有测试占位承接 `rapid_preview_review`；本轮未将 22 条复习话术写入“极速预习”素材，避免业务侧复习查询被预习图误承接。待业务上传或人工确认正式“极速复习”素材后，再补充人工 accepted 素材独有话术。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_rapid_preview_before_class_composition_prefers_preview_asset tests/test_phase4_search_orchestration.py::test_phase4_rapid_review_after_class_composition_prefers_review_asset tests/test_phase4_search_orchestration.py::test_phase4_ai_personalized_plan_composition_prefers_ai_custom_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_question_composition_prefers_photo_learning_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_socratic_value_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_socratic_thinking_coach_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：45 passed。
- `cd backend && ./.venv/bin/ruff check app/domain/runtime_intents.py app/services/query_understanding_service.py app/repositories/image_repository.py app/services/search_orchestrator.py app/services/proof_point_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- JSON 校验与 `git diff --check`：通过。
- 22 条业务校准用例均命中 `rapid_preview_review` / `pp_selfstudy_preview_dual_entry` / `ep_selfstudy_fast_review`。
- 旧校准“短时间高效复习”仍命中 `focused_excellence` / `pp_exam_focus_stage_review`，未被极速复习规则截走。
- 后端容器已重建，`docker compose ps backend` 显示 healthy。
- 容器运行环境验证 22/22 均识别到极速复习侧；由于当前真实库没有正式 `ep_selfstudy_fast_review` 素材组，搜索结果保持空，不退回“极速预习”素材补位。Postgres 检查显示仅有 21 个“极速预习复习”测试占位素材组，且均为 `ep_selfstudy_fast_preview`。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “极速复习”作为 `极速预习复习` 的课后复习侧治理；没有正式素材前只稳定语义和测试，不强行挪用预习素材。

---

## 2026-08-24：极速预习组合语义校准（D188）

### 完成内容

- 新增 `rapid-preview-before-class` 组合语义信号，将“极速预习/快速预习/课前预习/新课预习/提前学/上课前先学/明天课程提前看/先学再听课/课堂/每天晚上”等课前或新课前对象，与“快速过知识点/5分钟/十分钟/几分钟快速预习/轻量预习/快速了解新知识/提高课堂效率/带着问题进课堂/上课之前先建立认知/提前知道课堂重点/新课学习前/短时间完成预习”等短时准备目的组合识别为 `rapid_preview_review` 下的 `pp_selfstudy_preview_dual_entry`。
- 23 条业务代表搜索进入校准评测，不进入公共话术库，不新增“极速预习”核心卖点或证明点。
- 同步自学知识与跨体系校准补充边界：课前/新课前短时间建立认知、带着问题进课堂属于极速预习复习的课前预习侧；教材版本/学校进度适配仍归同步校内，考试节点冲刺复习仍归专项培优，自动学习计划/学习路径仍归 AI 定制学习方案，拍题讲解和个人错题长期归档仍分别归 AI 拍题精学与 AI 错题本。
- 本地真实库中为素材组 `56e44e39-0572-41a5-9691-92a3d50dd3dd`（极速预习）补充主证明点 `pp_selfstudy_preview_dual_entry`、主证据表达点 `ep_selfstudy_fast_preview`，并补充 23 条人工已采纳素材独有话术。
- 数据库关键字召回补充精确标题/素材组标题/accepted 素材话术优先排序；候选复核返回结果后再次执行人工卖点主通道路由，避免测试占位素材或第四层复核覆盖已确认的素材优先级。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_rapid_preview_before_class_composition_prefers_preview_asset tests/test_phase4_search_orchestration.py::test_phase4_ai_personalized_plan_composition_prefers_ai_custom_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_question_composition_prefers_photo_learning_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_socratic_value_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_socratic_thinking_coach_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：43 passed。
- `cd backend && ./.venv/bin/ruff check app/repositories/image_repository.py app/services/search_orchestrator.py app/services/proof_point_understanding_service.py app/domain/runtime_intents.py app/services/query_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- JSON 校验与 `git diff --check`：通过。
- 23 条业务校准用例均命中 `rapid_preview_review` / `pp_selfstudy_preview_dual_entry`。
- 真实本地库验证截图中的 23 条代表搜索首位均为“极速预习”。
- 后端容器已重建，`docker compose ps backend` 显示 healthy。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “极速预习”作为 `极速预习复习` 的课前预习侧治理；同证明点下的占位素材可跟随出现在后位，但不得压过正式素材。

---

## 2026-08-24：AI定制班/个性化学习组合语义校准（D187）

### 完成内容

- 新增 `ai-personalized-learning-plan` 组合语义信号，将“AI定制班/定制班/个性化学习/千人千面/个性化课程/因材施教/AI定制学习/专属学习方案/个性化学习路径/不同学生/不同基础/每个孩子/根据水平/根据薄弱点/AI个性化推荐”等对象，与“定制/课程/学习方案/学习路径/安排课程/推荐内容/学习计划自动生成/AI规划学习路径/个性化教学/动态调整/持续调整/不是所有孩子学一套/专属课程方案”等动作或结果组合识别为 `ai_learning_plan` 下的 `pp_planning_generated_schedule`。
- 24 条业务代表搜索进入校准评测，不进入公共话术库，不新增“AI定制班/个性化学习”核心卖点或证明点。
- 同步规划知识与跨体系校准补充边界：个性化、千人千面、因材施教、不同基础匹配内容属于 AI 量身定制学习方案；仅教材版本/章节一致仍归同步校内，仅薄弱题型专项训练仍归专项培优，真人持续督促仍归真人老师督学，学习结果周报仍归学情报告反馈。
- 本地真实库中为素材组 `f70de8b0-a833-48f3-bede-8cebfb48d5c6`（ai定制）补充主证明点 `pp_planning_generated_schedule`，并补充 24 条人工已采纳素材独有话术。
- 本地真实库中为素材组 `1ce654e9-7090-46d9-adf2-c6a6ed58feb9`（ai定制规划）补充主证明点 `pp_planning_transition_adaptation`，继续承接小升初/初升高等新学段定制规划表达。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_ai_personalized_plan_composition_prefers_ai_custom_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_question_composition_prefers_photo_learning_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_socratic_value_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_socratic_thinking_coach_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：41 passed。
- `cd backend && ./.venv/bin/ruff check app/services/proof_point_understanding_service.py app/domain/runtime_intents.py app/services/query_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- JSON 校验与 `git diff --check`：通过。
- 24 条业务校准用例均命中 `ai_learning_plan` / `pp_planning_generated_schedule`。
- 真实本地库验证截图中的 24 条代表搜索首位均为“ai定制”。
- 后端容器已重建，`docker compose ps backend` 显示 healthy。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “AI定制班/个性化学习”作为 `AI定制学习方案` 的业务入口治理；“ai定制规划”素材保留给学段衔接定制规划，不和普通个性化学习入口混排。

---

## 2026-08-24：AI思维教练/苏格拉底式引导组合语义校准（D186）

### 完成内容

- 新增 `ai-socratic-thinking-coach` 组合语义信号，将“AI思维教练/思维教练/苏格拉底式教学/苏格拉底式引导/AI引导思考/AI互动教学/真正的AI教学/会提问的AI老师”等对象，与“不直接给答案/引导式讲题/启发式学习/AI追问/一步一步引导/培养解题思路/培养独立思考/自己想出答案/不是直接搜答案/从答案到思路/启发而不是灌输/连续追问”等方法价值组合识别为 `photo_guided_learning` 下的 `pp_selfstudy_photo_socratic_guidance`。
- 23 条业务代表搜索进入校准评测，不进入公共话术库，不新增“AI思维教练”核心卖点或证明点。
- 同步自学知识与跨体系校准补充边界：这类表达是 AI 拍题精学的教学方法证明；只表达“随时问 AI 老师/即时答疑/当前疑问有人回答”且没有启发、追问、引导思考证据时，仍归 AI 私教随时答疑。
- 搜索策略中 `photo_guided_socratic_method` 素材门槛补充“不直接给答案、AI思维教练、启发式学习、连续追问”等触发词，避免“苏格拉底讲解提问”被特异性门槛挡掉。
- 本地真实库中为素材组 `5f438a69-b842-445e-954f-440fe7dc8fe8`（苏格拉底讲解提问）补充 25 条人工已采纳素材独有话术，覆盖截图代表搜索和相近长尾入口。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_photo_question_composition_prefers_photo_learning_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_socratic_value_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_socratic_thinking_coach_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：39 passed。
- `cd backend && ./.venv/bin/ruff check app/services/proof_point_understanding_service.py app/domain/runtime_intents.py app/services/query_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- JSON 校验与 `git diff --check`：通过。
- 23 条业务校准用例均命中 `photo_guided_learning` / `pp_selfstudy_photo_socratic_guidance`。
- 真实本地库验证截图中的 23 条代表搜索首位均为“苏格拉底讲解提问”。
- 后端容器已重建，`docker compose ps backend` 显示 healthy。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “AI思维教练/苏格拉底式引导”是 `AI拍题精学` 下的教学方法证明点入口，不是新的卖点；“AI老师答疑”若只是随问随答，仍保留在 AI 私教答疑。

---

## 2026-08-24：AI拍题精学组合语义校准（D185）

### 完成内容

- 新增 `photo-question-learning-entry` 组合语义信号，将“拍题精学/AI拍题/拍照讲题/拍题讲解/AI辅导题目/拍一道学一道/整页拍题/拍题相关证明点”等入口、讲题和证明点目的表达识别为 `photo_guided_learning` 下的 `pp_selfstudy_photo_question_recognition`。
- 新增 `photo-socratic-value-differentiation` 组合语义信号，将“拍题不是只给答案/AI一步步讲题/拍题后还能追问/区别于普通搜题软件/AI拍题差异化/从搜答案到学会/拍题功能核心价值”等方法和价值表达识别为 `photo_guided_learning` 下的 `pp_selfstudy_photo_socratic_guidance`。
- 15 条业务代表搜索进入校准评测，不进入公共话术库，不新增核心卖点或证明点。
- 同步自学知识与跨体系校准补充拍题边界：拍课本/笔记用于课前课后快速梳理仍归极速预习复习，拍纸质错题长期归档复练仍归 AI 错题本，拍题后做同类题/变式迁移仍归举一反三，普通 AI 问答仍归 AI 私教随时答疑。
- 证明点理解服务保留“组合语义命中”的优先级，避免后续通用短词匹配把“AI拍题差异化”等长句从苏格拉底式提问覆盖回拍题入口。
- 本地真实库中为素材组 `9259f447-a83f-4221-8ef8-fe5db8dca23b`（拍题精学）补充主证明点 `pp_selfstudy_photo_question_recognition`，并补充 8 条人工已采纳素材独有话术。
- 本地真实库中为素材组 `5f438a69-b842-445e-954f-440fe7dc8fe8`（苏格拉底讲解提问）补充主证明点 `pp_selfstudy_photo_socratic_guidance`，并补充 7 条人工已采纳素材独有话术。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_photo_question_composition_prefers_photo_learning_asset tests/test_phase4_search_orchestration.py::test_phase4_photo_socratic_value_composition_prefers_guidance_asset tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：37 passed。
- `cd backend && ./.venv/bin/ruff check app/services/proof_point_understanding_service.py app/domain/runtime_intents.py app/services/query_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- 15 条业务校准用例均命中预期证明点：入口/讲题类下钻 `pp_selfstudy_photo_question_recognition`，方法/价值差异化类下钻 `pp_selfstudy_photo_socratic_guidance`。
- 真实本地库验证截图中的 15 条代表搜索首位按两类表达分别为“拍题精学”或“苏格拉底讲解提问”。
- `git diff --check`：通过。
- 后端容器已重建，`docker compose ps backend` 显示 healthy。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “AI拍题精学”内部用两个证明点分流：找拍题入口/讲题/证明点时看“拍题精学”，找不只给答案、可追问、从搜答案到学会时看“苏格拉底讲解提问”。

---

## 2026-08-24：教材同步组合语义校准（D184）

### 完成内容

- 新增 `textbook-version-alignment` 组合语义信号，将“教材同步/同步教材/教材版本/版本适配/人教版/北师大版/校内同步/学校进度/多教材版本/全国教材/不同地区”等对象，与“同步/适配/覆盖/跟学校进度学/不同地区都能用/覆盖广/教材版本卖点/校内同步宣传”等动作或目的组合识别为 `school_sync` 下的 `pp_textbook_version_coverage`。
- 14 条业务代表搜索进入校准评测，不进入公共话术库，不新增核心卖点或证明点。
- 同步校内知识与跨体系校准补充“教材版本、版本名、地区教材适配”的边界：新课标/新题型/新考法仍归同步考点，拍课本/笔记做课前课后短时梳理仍归极速预习复习，按个人成绩目标排每日任务仍归 AI 定制学习方案。
- 本地真实库中为素材组 `97bb8e7f-d774-4c87-8f53-ebd76f83795f`（教材同步）补充主证明点 `pp_textbook_version_coverage`，为素材组 `b144065b-4c94-42ab-9a85-38a9a378a999`（课程同步）补充主证明点 `pp_textbook_version_selection`。
- 本地真实库中为“教材同步”补充 14 条人工已采纳素材独有话术，对应本轮代表搜索。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_textbook_version_composition_prefers_textbook_sync_asset -q`：32 passed。
- 后端容器已重建。真实本地库验证截图中的 14 条代表搜索均命中 `pp_textbook_version_coverage`，首位素材均为“教材同步”。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “教材同步”与“课程同步”同属 `school_sync`，但前者承接教材版本覆盖/适配表达，后者承接课程目录与版本选择/章节对应表达；公共入口仍由组合语义治理。

---

## 2026-08-24：重难点培优组合语义校准（D183）

### 完成内容

- 新增 `difficulty-excellence-upgrade` 组合语义信号，将“重难点/难题/压轴题/高分/优生/学有余力/90分/满分/高阶能力/不是只教基础”等对象，与“培优/拔高/突破/提升/冲高分/继续提升/往满分冲/冲刺高分”等动作组合识别为 `focused_excellence` 下的 `pp_exam_focus_targeted_modules`。
- 14 条业务代表搜索进入校准评测，不进入公共话术库，不新增核心卖点或证明点。
- 同步考点知识与跨体系校准补充“高阶难题、优生拔高、冲高分”的边界：考试节点冲刺仍归考试阶段重点梳理，升学断层归学段衔接，同一道题多解归万能解法，当前题后的同类/变式迁移归举一反三。
- 搜索策略扩展重难点培优素材触发词，并新增“考前专项突破”标题级素材门槛，避免“冲高分/优生拔高”误召回考前专项突破；同时避免用素材级泛化话术误杀“重难点培优”。
- 本地真实库中为素材组 `b1d51c72-1d11-4ba3-9427-8d98aad977b8`（重难点培优）补充 9 条人工已采纳素材独有话术：“重难点”“压轴题提升”“冲高分”“从90分往满分冲”“优生拔高”“高阶能力”“不是只教基础”“学有余力进一步提升”“成绩好的孩子还能继续提升”。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset tests/test_phase4_search_orchestration.py::test_phase4_difficulty_upgrade_composition_prefers_difficulty_module_asset -q`：32 passed。
- 后端容器已重建。真实本地库验证截图中的 14 条代表搜索均命中 `pp_exam_focus_targeted_modules`，首位素材均为“重难点培优”。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、公共话术库准入原则或 Provider 配置。
- “重难点培优”与“考前专项突破”共用 `pp_exam_focus_targeted_modules`，只在素材级查询表达上分流；公共入口仍由组合语义治理。

---

## 2026-08-24：专项突破组合语义校准（D182）

### 完成内容

- 新增 `targeted-module-breakthrough` 组合语义信号，将“专项/题型/单项/薄弱项/精准补弱”等对象与“突破/练习/强化/针对性训练/集中练/大量练习”等动作组合识别为 `focused_excellence` 下的 `pp_exam_focus_targeted_modules`。
- 13 条业务代表搜索进入校准评测，不进入公共话术库，不新增核心卖点。
- 同步考点知识与跨体系校准补充“专项题型或薄弱项训练”的边界：群体高频错题、个人错题、同类/变式迁移、课前课后复习分别保留原归属。
- 搜索策略新增重难点培优素材特异性门槛，避免“专项突破”查询混入“重难点培优”素材。
- 组合语义解释改为读取真实证明点名称，不再把所有组合命中都描述成“考试阶段重点梳理”。
- 查询明确命中证明点后，将该证明点受治理的 `evidence_terms` 加入数据库召回入口，保证“精准补弱”等未直接点名素材标题的表达也能召回专项突破素材。
- 本地真实库中为素材组 `17101f75-93ec-4c0c-a34c-34b46f675ec4`（考前专项突破）补充两条人工已采纳素材独有话术：“精准补弱”“体现精准补弱的卖点”。

### 验证结果

- `cd backend && ./.venv/bin/python -m pytest tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py::test_phase4_exam_stage_composition_prefers_exam_rush_asset_facet tests/test_phase4_search_orchestration.py::test_phase4_targeted_module_composition_excludes_difficulty_module_asset -q`：31 passed。
- `cd backend && ./.venv/bin/ruff check app/domain/runtime_intents.py app/services/query_understanding_service.py app/services/query_expansion_service.py tests/test_skill_selling_point_alignment.py tests/test_query_states_and_negation.py tests/test_phase4_search_orchestration.py`：通过。
- 后端容器已重建；`/health` 返回 ready。真实本地库验证“专项突破、薄弱题型、针对性训练、精准补弱、单题型大量练习”均命中 `pp_exam_focus_targeted_modules`，首位素材均为“考前专项突破”。

### 边界

- 不新增数据库 schema，不改变 16 个稳定卖点、人工 accepted 素材关系或 Provider 配置。
- “专项突破”仍属于 `focused_excellence`，只是在证明点和素材筛选层下钻到按题型和薄弱点定向突破。

---

## 2026-08-05：设计源文件链接与业务端隐藏（D178）

### 完成内容

- 新增素材组源文件链接能力，支持保存 Figma、设计文件、网盘、需求文档、素材包和其他可追溯链接。
- 后端新增 `asset_source_links` 模型、迁移、读写接口和审计记录；链接绑定素材组，不绑定单张图片版本。
- 素材组序列化新增 `include_source_links` 权限开关：设计师/管理员可读取，普通业务用户只收到空 `sourceLinks`。
- 前端素材工作台新增“设计源文件”维护区，支持添加、编辑、删除和新窗口打开链接；该区域只在可编辑详情页展示。

### 数据迁移

- 新增 `backend/alembic/versions/20260805_0021_asset_source_links.py`。

### 验证结果

- `./.venv/bin/python -m ruff check app tests/test_phase5_endpoints.py` 通过。
- `env PYTHONPYCACHEPREFIX=/tmp/piancton-pycache ./.venv/bin/python -m pytest tests/test_phase5_endpoints.py::test_phase5_source_links_are_editor_only` 通过。
- `npm run typecheck` 通过。

### 边界

- 源文件链接是设计协作资料，不进入普通业务端展示、搜索结果解释、四层搜索理解、推荐排序、下载逻辑或业务卖点关系。
- 普通业务用户没有新增、编辑、删除源文件链接权限。

---

## 2026-07-30：业务端双测试集真实 API 评测（D177）

### 完成内容

- 经用户明确授权，将 D176 的 50 条业务端测试话术发送给当前配置的老张和 OhMyGPT API 跑真实评测。
- 使用 `backend/scripts/run_business_side_search_eval.py --production-deps` 完成真实链路测试，报告输出为 `docs/BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_API.json` 和 `docs/BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_API.md`。

### 验证结果

- 精确话术 25 条：意图命中 `25/25`，Top5 预设素材关系命中 `25/25`，空结果 `0`，越界 `0`，错误 `0`，P95 `80209.84ms`。
- 模糊话术 25 条：意图命中 `23/25`，Top5 预设素材关系命中 `23/25`，空结果 `0`，越界 `2`，错误 `0`，P95 `72372.11ms`。
- 剩余问题：`BSF002` 未命中“动画精讲”，转向拍题精学/AI私教；`BSF006` 未命中“举一反三”，转向 AI 拍题精学。
- Provider 诊断显示 OhMyGPT 有真实接手成功记录：体系层 4 次、卖点层 9 次、证明点层 3 次、第四层 2 次；第四层有 1 次两家均失败。
- 真实 API 模式下中位耗时约 `55.4s`，最大耗时约 `115.7s`，主要风险是外部 Provider 慢失败和返回结构漂移。

### 边界

- 本次只新增真实 API 评测报告，不修改搜索逻辑、数据库 schema、Provider 配置、人工 accepted 关系、渠道过滤、四层搜索链路或占位素材数据。

---

## 2026-07-30：业务端双测试集专项评测（D176）

### 完成内容

- 新增业务端精确话术测试文档 `docs/BUSINESS_SIDE_PRECISE_SEARCH_EVAL_25_2026-07-30.md`，覆盖直接卖点、内部卖点名称、渠道加卖点等 25 条业务找图表达。
- 新增业务端模糊话术测试文档 `docs/BUSINESS_SIDE_FUZZY_SEARCH_EVAL_25_2026-07-30.md`，覆盖更偏业务语境和隐喻表达的 25 条找图话术。
- 新增机器可读数据集 `taxonomy/business_side_search_eval_2026-07-30.json`，包含精确集和模糊集两个 suite。
- 新增只读评测脚本 `backend/scripts/run_business_side_search_eval.py`，默认使用本地无外发链路跑测，也支持后续在明确授权后使用 `--production-deps` 跑线上同款依赖。

### 验证结果

- 使用 Docker PostgreSQL 真实本地库完成 50 条专项评测，输出 `docs/BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_LOCAL.json` 和 `docs/BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_LOCAL.md`。
- 精确话术 25 条：意图命中 `25/25`，Top5 预设素材关系命中 `25/25`，空结果 `0`，越界 `0`，P95 `586.71ms`。
- 模糊话术 25 条：意图命中 `18/25`，Top5 预设素材关系命中 `17/25`，空结果 `5`，越界 `3`，P95 `328.7ms`。
- 失败集中在动画精讲、新课标预测、专项培优、AI 错题本、学段衔接，以及课后小测/极速预习复习/真人督学相邻边界。
- `backend/.venv/bin/ruff check backend/scripts/run_business_side_search_eval.py` 通过；`git diff --check` 通过；Docker 服务健康检查通过。

### 边界

- 本次评测默认 `local_no_external`，没有调用老张、OhMyGPT 或任何外部 Provider。
- 不修改搜索逻辑、数据库 schema、Provider 配置、人工 accepted 关系、渠道过滤、四层搜索链路或占位素材数据。
- 若后续需要真实验证 GPT-5.5/OhMyGPT 在这 50 条业务话术上的表现，需要单独确认可将这些话术发送给当前配置的外部 Provider。

---

## 2026-07-28：批量占位素材与一键清理（D166）

### 完成内容

- 将 `backend/scripts/seed_placeholder_assets.py` 升级为批量测试数据工具，支持 `seed`、`status`、`delete` 三个动作。
- 默认 `seed --count 320`，按 16 个稳定核心卖点循环生成 20 轮批量占位素材。
- 渠道覆盖单渠道与混合渠道：`PPT`、`品牌手册`、`手机端大图`、`手机端小图`、`官网大图`、`官网小图`、`PPT、品牌手册`、`PPT、手机端大图`、`PPT、官网小图`、`品牌手册、官网大图`、`手机端大图、官网大图`、`手机端小图、官网小图`、`手机端大图、手机端小图`、`PPT、品牌手册、官网大图`。
- 场景状态覆盖 `true`、`false` 和 `null`，用于测试场景图筛选中的“有/无/未标注”边界。
- 每第 5 轮额外创建一个相邻卖点 `supports` 关系，用于模拟一张图适配多个卖点的搜索与展示。
- 新增 `delete --dry-run` 与 `delete`，只清理 `created_by/uploader=placeholder-seed` 且标题以“测试占位”开头的素材，并同步删除搜索索引、素材组、图片、原图和缩略图。

### 数据迁移

- 无数据库 schema 迁移。
- 当前本地数据库在 D165 原有 16 张基础占位图上新增 320 张批量占位图，当前占位库存共 336 张。

### 验证结果

- `python3 -m py_compile backend/scripts/seed_placeholder_assets.py` 通过。
- `backend/.venv/bin/ruff check backend/scripts/seed_placeholder_assets.py` 通过。
- `docker compose exec -T backend python -m scripts.seed_placeholder_assets seed --count 320`：`created=320, skipped_existing=0`。
- 重复执行 dry-run：`would create=0, skipped_existing=320`，确认批量标题幂等。
- `status` 显示：`groups=336`、`images=336`；场景分布为 `true=134`、`false=138`、`unset=64`。
- 数据库确认占位素材关系：`expresses=336`、`supports=64`。
- `delete --dry-run` 显示将删除 `groups=336`、`images=336`、`files=672`，确认清理范围只覆盖占位素材。

### 边界

- 这些素材仅用于本地搜索和页面压测，不代表真实业务已审核素材。
- 不改变数据库 schema、上传准入、四层搜索链路、渠道字典、卖点/证明点目录、人工关系规则、Provider 配置或线上数据口径。

### 常用命令

- 查看占位素材分布：`docker compose exec -T backend python -m scripts.seed_placeholder_assets status`
- 再补一批指定数量：`docker compose exec -T backend python -m scripts.seed_placeholder_assets seed --count 320`
- 删除前预演：`docker compose exec -T backend python -m scripts.seed_placeholder_assets delete --dry-run`
- 一键清理占位素材：`docker compose exec -T backend python -m scripts.seed_placeholder_assets delete`

---

## 2026-07-28：本地测试占位素材种子（D165）

### 完成内容

- 新增 `backend/scripts/seed_placeholder_assets.py`，用于真实素材不足时一键生成本地测试占位素材。
- 默认生成 16 张 “测试占位” PNG 主图，逐一覆盖当前 16 个稳定核心卖点。
- 渠道循环覆盖 `PPT`、`品牌手册`、`手机端大图`、`手机端小图`、`官网大图`、`官网小图`，并包含 `PPT、品牌手册` 与 `手机端大图、官网大图` 多渠道样例。
- 每张占位图都会创建 published/approved 素材组、当前主图、人工 accepted `expresses` 卖点关系、accepted 素材独有话术、渠道、画面风格、场景图布尔值、语义总结、Semantic Profile V3，并尽量写入该卖点下可用的主证明点/证据表达点 code。
- 脚本按标题幂等跳过已有占位素材，重复执行不会重复灌库。

### 数据迁移

- 无数据库 schema 迁移。
- 当前本地数据库已执行脚本并新增 16 张测试占位图、16 个素材组、16 条 accepted 卖点关系、80 条 accepted 素材话术。

### 验证结果

- `python3 -m py_compile backend/scripts/seed_placeholder_assets.py` 通过。
- `backend/.venv/bin/ruff check backend/scripts/seed_placeholder_assets.py` 通过。
- `docker compose exec -T backend python -m scripts.seed_placeholder_assets --dry-run`：执行前显示将创建 16 张；执行后显示 `would create=0, skipped_existing=16`，确认幂等。
- 容器内查库确认：`images=16`、`groups=16`、`accepted_links=16`、`accepted_phrases=80`，渠道覆盖默认六类及两个多渠道组合。

### 边界

- 这些素材仅用于本地测试库存，不代表真实业务已审核素材。
- 不改变上传准入、四层搜索链路、渠道字典、卖点/证明点目录、人工关系规则、数据库 schema 或 Provider 配置。

### 下一步

1. 用业务端搜索和渠道筛选实际验证占位素材能否覆盖搜索、详情推荐、下载菜单和反馈模块。
2. 真实素材补齐后，可按标题前缀筛选这些占位素材，再统一清理或保留为测试数据。

---

## 2026-07-28：卖点结果推荐语人工维护（D161）

### 完成内容

- `business_concepts` 新增可空 `recommendation_text`，用于维护每个卖点在搜索结果卡片下方展示的人工推荐语。
- 管理员侧边栏新增“推荐语”页面，可按卖点集中编辑推荐语；该文案只影响结果展示，不进入模型 Prompt 或召回排序。
- 搜索响应中的 `matchedQueryConcepts` 透传当前查询命中卖点的 `recommendationText`。
- 结果卡片优先展示当前搜索命中卖点及其人工推荐语；同一图片如果 accepted 支持多个卖点，不展示非当前搜索命中的其他卖点文案。
- 未维护人工推荐语时继续回退到证明点 claim、素材独有话术和既有解释，避免空白。

### 数据迁移

- 新增 `20260728_0020_concept_recommendation_text.py`，为 `business_concepts` 增加 `recommendation_text`。

### 边界

- 不修改体系/卖点/证明点识别、候选召回、排序、Reranker、人工素材关系、渠道过滤或 Provider 配置。

## 2026-07-28：GPT-5.5 Provider 兜底遥测（D155）

### 完成内容

- OpenAI-compatible provider 记录最后一次调用的脱敏 attempt 摘要：provider host 标签、模型名、状态、耗时和错误摘要。
- Fallback 链汇总每个 provider 尝试；成功切换兜底时写入日志，全部失败时错误信息包含脱敏摘要。
- 三层搜索诊断 detail 追加体系、卖点、证明点各层 Provider 摘要，便于后台判断每层实际由老张还是 OhMyGPT 完成。
- 所有遥测只记录 host 标签和错误摘要，不记录、不展示、不写入任何 API key。

### 验证

- `docker compose exec -T backend python -m pytest tests/test_ai_provider.py tests/test_phase4_search_orchestration.py tests/test_search_service.py tests/test_search_index.py -q`：`67 passed`。
- `git diff --check` 通过。
- 真实 HTTP 搜索 `家长可以查看学习结果`：总耗时约 `35.442s`，`fallback=false`，`timedOut=false`，`query_understanding=ok`；诊断包含 Provider 摘要：体系 Provider `laozhang/gpt-5.5 ok 7114ms`，卖点 Provider `laozhang/gpt-5.5 ok 10111ms`，证明点 Provider `laozhang/gpt-5.5 ok 7206ms`。
- 脱敏最小 JSON 健康检查：老张约 `3206ms` 成功，OhMyGPT 约 `2788ms` 成功。
- 强制主 Provider 失败的兜底测试：主 provider 约 `30ms` 失败，OhMyGPT 约 `2294ms` 接手成功，attempt 摘要未包含密钥。

### 后续建议

- 把分层 Provider attempt 摘要写入搜索日志结构化字段，便于后台页面筛选统计成功率、P95 和错误类型。
- 补充 10～20 条真实业务话术压测，分别统计老张首发成功率与 OhMyGPT 接手成功率。

## 2026-07-28：GPT-5.5 搜索理解容错接入（D154）

### 完成内容

- 第一层体系路由增加模型返回归一化：兼容 `systems/candidates/candidateSystems`、中文体系名、字符串候选和简写 `route_type`，统一落到封闭六体系 code。
- 第二层卖点判断不再因为模型顺带返回证明点/证据表达点而整体失败；后端只保留已命中父卖点范围内、目录存在且父链合法的 `pp_`/`ep_`，越界项丢弃。
- 第三层证明点判断同样改为范围过滤，避免少量跨父卖点或多余证据项报废已完成的卖点理解。
- 运行预算从体系 `8s`、卖点 `20s`、证明点 `20s`、聚合理解 `30s` 调整为体系 `15s`、卖点 `25s`、证明点 `20s`、聚合理解 `75s`，避免 Provider 网关抖动时第一层还没返回就进入降级。
- 保留三层模型参与：本轮不恢复本地强证据跳过模型，不改 Prompt 纪律、六体系、16 个卖点、人工 accepted 素材关系、数据库或图片准入。

### 验证

- 重新构建后端镜像并启动：`docker compose up -d --build backend`。
- `docker compose exec -T backend python -m pytest tests/test_ai_provider.py tests/test_phase4_search_orchestration.py tests/test_search_service.py tests/test_search_index.py -q`：`65 passed`。
- `git diff --check` 通过。
- 真实 HTTP 搜索 `家长可以查看学习结果`：最终预算生效后总耗时约 `29.891s`，`fallback=false`，`timedOut=false`，`query_understanding=ok`；诊断为体系路由 `10430ms`、卖点识别 `11103ms`、证明点识别 `8104ms`。模型理解为 `同步伴学体系 > 学情报告反馈`，并命中证明点 `pp_companion_report_core_metrics`，返回 1 张结果。

### 后续建议

- 将 D155 的 Provider attempt 遥测进一步结构化写入搜索日志和后台统计，而不只停留在诊断 detail。
- 评估新增召回后 top-K 模型复核层：输入用户话术、候选图标题、语义摘要、已采纳素材话术和业务关系，输出相关性/排除原因；该层只复核候选，不作为入口全库裁判。

## 2026-07-28：GPT-5.5 Provider 配置收口（D153）

### 完成内容

- 确认根目录 `.env` 才是 Docker Compose 实际读取的运行配置，`backend/.env` 中已写入的目的专用密钥此前未进入容器。
- `docker-compose.yml` 新增透传 `IMAGE_ANALYSIS_*`、`ASSET_PHRASE_*`、`SEARCH_FALLBACK_*` 和 `SEARCH_PROOF_POINT_TIMEOUT_SECONDS`。
- 根目录 `.env` 与 `backend/.env` 已同步为：图片分析、上传前素材话术和搜索主判断均使用 GPT-5.5；搜索兜底使用 OhMyGPT GPT-5.5。
- 当前运行配置清空 DeepSeek/Kimi fallback 槽位，并清空 SiliconFlow Embedding/Reranker 槽位；Meilisearch 继续保留为本地关键词索引。

### 边界

- 不修改六大体系、16 个卖点、人工素材关系、搜索 Prompt、数据库结构或 Meilisearch 索引职责。
- DeepSeek/Kimi 及 SiliconFlow 相关历史评测保留为历史记录，不再代表当前默认运行策略。

## 2026-07-27：GPT-5.5 严格三级搜索理解（D152）

### 完成内容

- 自然语言在线搜索改为 `体系 → 卖点 → 证明点` 三次独立模型调用。
- 第二层只加载候选体系运行时卖点摘要与当前启用卖点，禁止提前输出 `pp_`/`ep_`。
- 第三层只加载已命中卖点的直属证明点和内部证据表达线索，使用独立 Schema 校验父子范围。
- 新增 `SEARCH_PROOF_POINT_TIMEOUT_SECONDS`，三级默认预算分别为 `8s/20s/20s`。
- 只有三级完整成功结果进入查询理解缓存；诊断记录三段独立耗时。
- 自然语言搜索不再因本地高置信卖点跳过模型；本地判断继续作为防止错误模型覆盖的仲裁真值。手动筛选保持确定性执行。

### 边界

- 纯画面或无可靠体系在第一层结束；第二层没有卖点时不调用第三层。
- 第二层命中的数据库临时卖点若尚未建立证明点目录，也不空跑第三层。
- 第三级只做证明点理解，不直接选择图片；图片仍由人工 accepted 关系、素材话术、确定性门槛和最多一次 Reranker 处理。
- 无数据库迁移，不修改六体系、16 个卖点、人工素材关系或已有素材。

### 验证

- 三层链路、Prompt 边界、Schema 校验、路由仲裁、证明点运行时和三级独立超时编排定向回归 `94 passed`。
- Ruff 与 `git diff --check` 通过；三级 Prompt 规模分别约为 `2113/2203/1841` 字符。
- 后端全量回归 `228 passed, 6 failed`；剩余失败为当前工作区既有的服务行数约束、页头品牌断言和证据表达点公开接口旧断言，与 D152 三层链路无直接关系。

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

## 2026-07-28：第四层复核轻缓存与候选数控制（D157）

### 本轮目标

- 将第四层候选图片复核纳入现有 5 分钟搜索轻缓存。
- 控制第四层默认复核候选数，避免一次把过多图片送入模型。

### 完成内容

- `SearchCaches` 新增 `candidate_reviews` 缓存桶，沿用 `SEARCH_CACHE_TTL_SECONDS` 和 `SEARCH_CACHE_MAX_ENTRIES`。
- 第四层复核先查缓存，命中后直接应用 cached decisions，并在诊断中标记 `cache_hit=true`。
- 缓存 key 使用原始查询、前三层结构化理解和候选图稳定上下文；动态 score 与 reasons 不进入 key，避免同一候选轻微排序分数变化导致缓存失效。
- 新增 `SEARCH_CANDIDATE_REVIEW_LIMIT=5`，默认只复核 Top 5 候选；其余候选保留原排序。
- Docker Compose、`.env`、`backend/.env` 和 example 环境文件均补充该非敏感配置。
- `skills/INDEX.md` 补充 `search_candidate_review` 第四层运行时模型映射。

### 修改文件

- `backend/app/services/search_cache.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_service.py`
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/tests/test_phase4_search_orchestration.py`
- `.env`
- `backend/.env`
- `.env.docker.example`
- `backend/.env.example`
- `docker-compose.yml`
- `skills/INDEX.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库迁移。
- 缓存仅在后端进程内存中保存，TTL 到期或后端重启即清空，不写数据库、不写文件。

### 测试结果

- 第四层专项：`42 passed`。
- 搜索核心专项：`72 passed`。
- 真实 API 连续搜索“月考期中期末一键划重点”：第一遍 `37.09s`，第四层正常调用模型并复核 3 张；第二遍 `0.26s`，`candidate_review.cacheHit=true`，复用第四层缓存后仍返回 3 张。

### 遗留问题

- 第一次未命中缓存时仍需要完整四层模型调用，耗时仍取决于 provider 响应速度。
- 默认 Top 5 是保守值；如果后续发现第 6～8 张经常需要第四层纠偏，可通过配置调高。

### 下一步

1. 用管理员页面观察连续搜索同一句话时第四层缓存命中情况。
2. 根据真实查询样本评估 Top 5 是否足够；必要时调整 `SEARCH_CANDIDATE_REVIEW_LIMIT`。

---

## 2026-07-28：第四层候选图片复核与 Provider 校验接力（D156）

### 本轮目标

- 先落地第四层“查询话术 ↔ 候选图片”模型复核。
- 让老张和 OhMyGPT 在每一层都能稳定接力：第二层、第三层或第四层如果老张失败，OhMyGPT 在同一层接手。
- 用 10 条真实业务话术验证四层链路、超时情况和候选返回情况。

### 完成内容

- 新增模型任务 `search_candidate_review`，第四层只复核已召回候选，输出 `keep/demote/exclude`，不得新增候选、不得重判体系/卖点/证明点。
- `AiService` 增加 `review_search_candidates`；`SearchExternalBranches` 在召回、概念路由、Reranker 后追加第四层候选复核，并将诊断写入 `candidate_review` 分支。
- 第四层候选上下文包含人工 accepted 业务关系、素材独有话术、标题、摘要、画面事实、场景、主证明点和证据点。
- Provider fallback 改为“生成 + schema 校验”都通过才算成功；HTTP 成功但返回结构无效时，当前 provider 记为 failed 并继续尝试下一个 provider。
- 第四层外层预算增加 provider 接力缓冲，避免第一家耗尽 per-provider 时间后第二家没有执行机会。
- 对“月考/期中/期末/考前 + 划重点/冲刺/重点梳理”这种同步考点强别名增加保护性修复：第一层已路由同步考点且第二层结构不稳定时，补全到 `focused_excellence`。
- 当同卖点已有 accepted 素材但老素材未补证明点字段导致第三层候选被筛空时，保留卖点候选进入第四层复核；明确登记为二期缺口的 `asset_evidence_requirements` 仍保持空结果，不被绕过。

### 修改文件

- `backend/app/ai/contracts.py`
- `backend/app/ai/fallback.py`
- `backend/app/ai/normalizer.py`
- `backend/app/ai/openai_compatible.py`
- `backend/app/ai/skill_loader.py`
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/app/schemas/ai.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/asset_selection_policy_service.py`
- `backend/app/services/query_understanding_service.py`
- `backend/app/services/search_concept_routing_service.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_service.py`
- `backend/tests/test_ai_provider.py`
- `backend/tests/test_phase4_search_orchestration.py`
- `.env.docker.example`
- `backend/.env.example`
- `docker-compose.yml`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 无素材关系写入；未新增体系、卖点、证明点或证据点。
- 运行密钥只在 Git 忽略的环境文件中使用，文档和日志不记录 API key。

### 测试结果

- 后端核心专项：`70 passed`（`tests/test_ai_provider.py`、`tests/test_phase4_search_orchestration.py`、`tests/test_search_service.py`、`tests/test_search_index.py`）。
- `git diff --check` 通过。
- Docker 后端已重建并健康；运行时 search provider 链确认包含 `laozhang/gpt-5.5` 与 `ohmygpt/gpt-5.5` 两个已配置 provider。
- 单条真实搜索“家长可以查看学习结果”：四层均 `ok`，总耗时约 `32.3s`，第四层复核 1 张候选。
- 10 条真实话术首轮复测均请求成功、无整体 API 失败；其中“通过启发式提问，还原思考过程，帮你从解一题到通一类”验证卖点层老张失败后 OhMyGPT 在同层接手成功。
- “月考期中期末一键划重点”从首轮卖点层失败/0 候选修复为三层识别 `同步考点体系 > 专项培优`、证明点 `考试阶段重点梳理`，真实复测返回“考前专项突破、考前突击、高频错题”3 张并进入第四层复核。
- “几分钟讲明白一个知识点”首轮出现第四层 laozhang 失败后外层预算不足，修复预算后单独复测 `candidate_review ok`、无超时，结果收敛为“5-8分钟讲透知识点，学完就练、官方数据规模”2 张。

### 遗留问题

- 四层全模型链路的端到端耗时仍偏高：多数真实话术约 `27s～60s`，需要后续继续做查询理解缓存、候选复核缓存或更细的并发预算优化。
- 第四层复核会增加一次模型调用；候选越多越慢。当前失败时会保留原排序，保证可降级，但精排质量依赖后续更多样本观察。
- 部分老素材缺少 `primary_proof_point_code` / `primary_evidence_point_code`，本轮只在不违背二期缺口规则的前提下让它们进入第四层复核；长期仍建议补标老素材证明点。

### 下一步

1. 在管理员页面继续观察搜索诊断中的四层 Provider attempts，重点记录老张结构漂移、超时和 OhMyGPT 接手次数。
2. 对高频话术建立小型回归集，单独统计第四层前后 Top 结果是否更准。
3. 补标现有老素材的主证明点/证据点，减少第三层候选对标题和素材独有话术的依赖。

---

## 2026-07-28：渠道必填与精确收窄（D159）

### 本轮目标

- 让“用户带渠道搜索就是精确渠道需求”的口径落到工程行为。
- 让设计师上传主图、延展版本和替换主图时必须选择主要使用渠道。
- 避免后续 `PPT/手机端/朋友圈/官网` 搜索因为素材未标渠道而混入其它渠道结果。

### 完成内容

- 主图上传弹窗去掉“暂不标注”，未选择使用渠道时不能发布。
- 素材详情的“添加延展版本/替换正式主图”弹窗改为渠道下拉选择，未选择渠道时不能提交。
- 后端 `/api/images/upload`、`/api/asset-groups/{id}/images` 和 `/api/asset-groups/{id}/primary-image` 增加 `channel_required` 校验，缺渠道返回 `422`。
- 搜索结果后二次筛选从“当前结果中存在匹配渠道才软收窄”改为“存在渠道意图即按候选渠道精确过滤”。
- 更新上传与搜索筛选相关测试。

### 修改文件

- `backend/app/api/v1/images.py`
- `backend/app/api/v1/assets.py`
- `backend/tests/test_security_and_images.py`
- `backend/tests/test_phase5_endpoints.py`
- `backend/tests/test_phase_0_3_rebuild.py`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/pages/ImageDetail/asset/AssetVersionDialog.tsx`
- `client/src/pages/ImageHome/searchResultFilters.ts`
- `client/src/pages/ImageHome/searchResultFilters.test.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 不回填旧素材渠道；新写入入口开始强制要求渠道。

### 测试结果

- `npm test -- channelIntent searchResultFilters`：`2 passed / 13 passed`。
- `npm run typecheck` 通过。
- Docker 后端精确回归：`tests/test_security_and_images.py::test_upload_preview_download_and_phase6_detail_contract`、`tests/test_phase5_endpoints.py::test_phase5_designer_can_upload_primary_add_variant_and_replace_it`、`tests/test_phase5_endpoints.py::test_phase5_asset_version_writes_require_channel`、`tests/test_phase5_endpoints.py::test_phase5_derivative_upload_never_queues_ai_analysis`、`tests/test_phase_0_3_rebuild.py::test_phase2_upload_creates_group_and_derivative_search_is_deduplicated`，`5 passed`。
- `git diff --check` 通过。

### 遗留问题

- 历史素材如果缺渠道，不会被本轮自动补齐；需要设计师在详情中逐步补标或后续做一次人工回填。
- 自定义渠道仍是前端本地词库；多人共享渠道词库仍按 D137 后续方向迁入后端。

### 下一步

1. 用真实搜索验证带渠道话术的结果是否会按渠道精确收窄。
2. 若历史素材存在空渠道，安排一次人工补标。

---

## 2026-07-28：朋友圈渠道意图归手机端（D158）

### 本轮目标

- 明确“PPT/朋友圈”等使用渠道要和业务卖点搜索并行处理。
- 让“能在 PPT 用的拍题精学”自动命中 `PPT` 渠道语境。
- 让“发朋友圈的拍题精学”自动归入手机端，并按大图/小图语境优先推荐对应渠道。

### 完成内容

- 前端渠道意图解析器新增 `朋友圈/微信朋友圈/社媒/社交平台` 手机端家族识别。
- 普通“发朋友圈/朋友圈素材”默认识别为 `手机端大图`；同时出现 `九宫格/列表/入口/小图/缩略图/信息流` 等紧凑位置词时识别为 `手机端小图`。
- 新增测试覆盖用户举例：“我想找一张能在 PPT 用的拍题精学”“找一张能发朋友圈的拍题精学”“朋友圈九宫格入口图”。
- 同步更新 `understand-image-channel-intent` Skill 说明和渠道 taxonomy。
- 保持 D133/D140 边界：渠道意图只用于结果后二次收窄、筛选按钮高亮和推荐说明，不进入卖点主通道、不改变四层模型搜索。

### 修改文件

- `client/src/pages/ImageHome/channelIntent.ts`
- `client/src/pages/ImageHome/channelIntent.test.ts`
- `skills/understand-image-channel-intent/SKILL.md`
- `skills/understand-image-channel-intent/references/channel-taxonomy.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库迁移。
- 无素材关系、渠道字段或本地存储结构变更。

### 测试结果

- `npm test -- channelIntent searchResultFilters`：`2 passed / 13 passed`。
- `npm run typecheck` 通过。

### 遗留问题

- 当前渠道意图仍在前端确定性解析；如后续要多人共享渠道词库，需要按 D137 后续方向迁入后端渠道字典服务。
- 渠道标签是否足够依赖上传/延展版本时的人工标注；未标注渠道的素材不会被凭空推荐为某个渠道。

### 下一步

1. 用真实搜索“PPT 拍题精学”“朋友圈 拍题精学”“朋友圈九宫格 拍题精学”观察结果高亮和收窄是否符合业务预期。
2. 如果业务方常说“小红书、公众号、社群、投放页”等，可继续按同一规则补充渠道词库和测试。

---

## 2026-07-29：测试前收口与证据表达点契约修复（D167）

### 本轮目标

- 修复审查中发现的业务 facets 证据表达点契约漂移。
- 让本地和 Docker 后端关键测试恢复可重复运行。
- 确认搜索用途的老张 + OhMyGPT GPT-5.5 fallback 链路仍在运行环境中生效。
- 修正批量占位素材主关系覆盖不足，方便后续用测试图压测 `expresses/supports` 边界。

### 完成内容

- `/api/business-facets` 恢复返回可见证明点下的 `evidencePoints`、`sourcePaths` 与 `reviewNotes`。
- 上传弹窗和素材详情的“业务表达层级”统一支持“主要表达卖点 / 证明点 / 证据表达点”三级联动；保存时不再把 `evidencePointCode` 固定抹为 `null`。
- 移除 `get_settings()` 的存储目录创建副作用，目录创建继续由 `LocalStorageProvider` 和写文件脚本负责，避免本地 pytest 导入配置时因 `STORAGE_DIR` 权限失败。
- 后端 Ruff 全量清理通过，包括 Provider fallback、normalizer、Skill prompt 和历史脚本长行/导入问题。
- 修复 `backend/scripts/seed_placeholder_assets.py` 的主关系取模逻辑；`seed` 遇到已存在的 `placeholder-seed` 测试素材时，会同步脚本负责的测试元数据和主关系，不触碰正式素材。
- 重建并重启 backend 容器，让新脚本在 Docker 环境生效；当前四个服务均 healthy。
- 重建并重启 web 容器，让上传弹窗和素材详情的前端修复在 `http://127.0.0.1` 生效。
- 脱敏确认运行环境：通用 provider 是单 primary，搜索用途是 2 个已配置 GPT-5.5 provider 的 `FallbackModelProvider`。

### 修改文件

- `backend/app/api/v1/business_facets.py`
- `backend/app/core/config.py`
- `backend/app/ai/fallback.py`
- `backend/app/ai/normalizer.py`
- `backend/app/ai/skill_loader.py`
- `backend/scripts/seed_placeholder_assets.py`
- `backend/scripts/restore_assets_from_sqlite.py`
- `backend/scripts/run_business_novice_fuzzy_eval.py`
- `backend/scripts/run_external_selling_point_review.py`
- `backend/tests/test_business_facets.py`
- `backend/tests/test_search_service.py`
- `client/src/features/assets/BusinessClassificationFields.tsx`
- `client/src/features/assets/BusinessClassificationFields.test.tsx`
- `client/src/pages/ImageDetail/asset/AssetBusinessClassificationPanel.tsx`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 本地测试占位素材同步：仍为 `groups=336, images=336`。
- 占位素材关系分布更新为 `expresses=256`、`supports=144`。

### 测试结果

- `backend/.venv/bin/ruff check backend/app backend/scripts backend/tests`：通过。
- 本地 `pytest backend/tests/test_ai_provider.py backend/tests/test_business_facets.py backend/tests/test_phase5_endpoints.py backend/tests/test_search_service.py -q`：`37 passed`。
- 本地 `pytest backend/tests/test_phase4_search_orchestration.py -q`：`42 passed`。
- Docker `python -m pytest tests/test_ai_provider.py tests/test_business_facets.py tests/test_phase5_endpoints.py tests/test_search_service.py -q`：`37 passed`。
- Docker `python -m pytest tests/test_phase4_search_orchestration.py -q`：`42 passed`。
- `npm run typecheck`：通过。
- `npm run lint`：通过。
- `npm run test -- BusinessClassificationFields.test.tsx`：`1 passed`。
- `docker compose ps`：backend、web、postgres、meilisearch 均 healthy。

### 遗留问题

- 本轮未跑真实外部模型搜索 10 条话术；只确认 provider 链路配置和回归测试。
- 本轮没有用浏览器逐页视觉走查上传弹窗和素材详情，只完成构建、类型、lint 和组件测试。

### 下一步

1. 重建 web 或启动本地前端后，走查上传弹窗、素材详情业务层级保存和搜索结果卡推荐语。
2. 用 10～20 条真实业务话术复测四层搜索耗时、fallback attempt 和 Top 结果。
3. 正式测试前保留当前占位素材，测试结束可用 `seed_placeholder_assets delete --dry-run/delete` 清理。

---

## 2026-08-07：搜索运营看板补强

### 本轮目标

- 在现有搜索运营页补齐“养项目”需要看的运营指标，不新增分散入口。
- 让管理员能直接看到素材资产、源文件健康和模型速度问题。

### 完成内容

- `/api/admin/search-ops/summary` 新增素材资产巡检：素材组数、图片数、当前图片数、缺源文件、单版本、缺业务关系、缺搜索话术、缺风格、未定场景、缺渠道、总下载和未使用素材。
- 新增素材运营问题队列：按缺源文件、缺业务关系、缺搜索话术、单版本、缺风格输出可点击素材项和处理建议。
- 新增源文件健康汇总：源文件链接总数、已记录/未记录素材、链接类型分布和最近源文件列表。
- 新增模型速度汇总：真实搜索样本数、P50/P95/P99、慢查询数和占比、缓存命中率、降级、超时、AI 理解数及最近慢查询。
- 前端 `/admin/search-ops` 增加“素材资产 / 源文件健康 / 模型速度”三个页签，保留原有总览、问题队列、AI 审核池、概念健康度、素材缺口和反馈记录。

### 修改文件

- `backend/app/schemas/search_ops.py`
- `backend/app/repositories/search_ops_repository.py`
- `backend/app/services/search_ops_service.py`
- `backend/tests/test_security_and_images.py`
- `client/src/pages/AdminSearchOps/AdminSearchOps.tsx`
- `client/src/pages/AdminSearchOps/components/SearchOpsSections.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 本轮只读取既有素材组、图片、源文件链接、素材关系、素材话术和搜索日志。

### 测试结果

- `backend/.venv/bin/python -m pytest backend/tests/test_security_and_images.py -q`：`15 passed`。
- `backend/.venv/bin/ruff check backend/app/services/search_ops_service.py backend/app/repositories/search_ops_repository.py backend/app/schemas/search_ops.py backend/tests/test_security_and_images.py`：通过。
- `npm --prefix client run lint`：通过。
- `npm --prefix client run typecheck`：通过。
- `npm --prefix client run generate:api`：通过。
- 浏览器验证 `/admin/search-ops`：三个新页签均可显示；素材资产页显示 40 个素材组及缺源文件问题，源文件健康页显示未记录素材，模型速度页显示 P50/P95/P99 与慢查询；控制台无错误。

### 遗留问题

- 当前源文件健康页只统计“是否记录”和链接类型，未做外链存活探测；后续如要检查 Figma/网盘链接是否失效，需要单独设计外链检测任务。
- “未使用素材”目前按下载数为 0 判断，不代表图片业务价值低，只用于提醒运营观察。

### 下一步

1. 为缺源文件的真实素材批量补充 Figma/网盘链接。
2. 结合模型速度页，把 3 秒以上慢查询按冷启动、模型超时、缓存未命中和 Provider 慢失败继续拆因。
3. 后续可增加“源文件失效检测”和“素材缺尺寸/缺渠道清单”的导出能力。

---

## 2026-08-17：搜索运营 9 项优化第一版

### 本轮目标

- 解决用户提出的前 9 个可优化点：源文件健康、素材生命周期、重复素材、GIF 体验、反馈沉淀、批量导出、项目夹、搜索解释和模型成本控制。
- 保持普通搜索主链路、业务金标准、人工审核边界和 Provider 配置不变。

### 完成内容

- 源文件健康新增 90 天超期复查统计和“源文件待复查”素材问题。
- 素材运营问题新增长期未使用、大 GIF、文件指纹重复和画面近似重复识别。
- 搜索运营页新增“反馈归档”，把反馈归入修业务关系、补搜索话术、补版本尺寸、补素材和补画面表达。
- 模型速度页新增模型工作量和工作量/搜索占比。
- 搜索结果新增本地项目夹，可临时收集素材组并批量导出 ZIP。
- 批量导出接口按角色控制 manifest：设计师/管理员可带源文件，业务端不带源文件链接。
- GIF 列表预览新增开关，默认动画，关闭后使用缩略图。

### 修改文件

- `backend/app/api/v1/assets.py`
- `backend/app/schemas/asset.py`
- `backend/app/schemas/search_ops.py`
- `backend/app/services/asset_service.py`
- `backend/app/services/search_ops_service.py`
- `backend/tests/test_phase5_endpoints.py`
- `client/src/api/asset.ts`
- `client/src/features/assets/useProjectBasket.ts`
- `client/src/features/images/imagePreview.ts`
- `client/src/features/images/useAnimatedGifPreview.ts`
- `client/src/pages/AdminSearchOps/AdminSearchOps.tsx`
- `client/src/pages/AdminSearchOps/components/SearchOpsSections.tsx`
- `client/src/pages/ImageHome/GlobalImageSearch.tsx`
- `client/src/pages/ImageHome/ImageCard.tsx`
- `client/src/pages/ImageHome/ImageGrid.tsx`
- `client/src/pages/ImageHome/ImageHome.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/*`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 项目夹使用浏览器本地存储；后续需要跨设备同步时再升级为数据库能力。

### 测试结果

- `backend/.venv/bin/python -m pytest backend/tests/test_phase5_endpoints.py::test_phase5_source_links_are_editor_only backend/tests/test_phase5_endpoints.py::test_phase5_system_filter_asset_metadata_and_result_feedback`：`2 passed`。
- `backend/.venv/bin/ruff check backend/app/services/search_ops_service.py backend/app/services/asset_service.py backend/app/api/v1/assets.py backend/app/schemas/asset.py backend/app/schemas/search_ops.py backend/tests/test_phase5_endpoints.py`：通过。
- `npm run generate:api`：通过。
- `npm run typecheck`：通过。
- `npm run lint`：通过。
- `npm run test -- imagePreview.test.ts`：`3 passed`。
- `curl -sf http://127.0.0.1:8000/health/ready`：ready。

### 遗留问题

- 源文件“失效”仍未做联网检测；Figma/网盘常需登录，第一版先按超期复查推进。
- 画面近似重复使用轻量平均哈希，只作为提示，仍需人工确认。
- 项目夹当前只在本机浏览器保存，不跨账号同步。

### 下一步

1. 收集真实项目夹使用反馈，再判断是否做服务端收藏夹。
2. 当源文件维护量上来后，设计登录态可用的链接探测任务。
3. 用真实搜索日志校准模型工作量阈值，再考虑 Provider 预算和缓存策略。

---

## 2026-08-25：黑白暖灰视觉规范与原创 Agent 动效

### 本轮目标

- 统一登录页、侧边栏和素材库 Agent 的视觉基调，减少蓝色残留。
- 参考更精细网页产品的交互动效，但不引入许可风险。
- 让素材库 Agent 从普通 Bot 图标升级为更有生命感的原创动效入口。

### 完成内容

- 全局主题变量调整为黑白暖灰主基调，蓝色降级为少量信息状态色。
- 登录页背景、品牌头图标和按钮去蓝化，统一使用暖灰背景和黑色主操作。
- 侧边栏导航图标加入轻微 hover 位移、缩放、转动、点击压感和光扫反馈。
- 左上角品牌位从无业务含义的 M 图标改为同 Agent 体系的平面机器人标识。
- 素材库 Agent 改为项目原创 CSS 暖白光球/表情动效，支持悬浮入口、面板头像和思考状态。
- API 中心“智能调度配置”重排一级/二级层级，把自动/人工开关、主 API、备用池、超时和保存收进同一个紧凑配置面板，移除蓝色原生对勾和过大的独立白框。
- `UX_UI_DESIGN_SYSTEM.md` 更新视觉语言，明确外部开源角色视觉在许可证未允许商用前不得直接使用。

### 修改文件

- `client/src/tailwind-theme.css`
- `client/src/components/PianctonAgentMark.tsx`
- `client/src/components/Layout.tsx`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/pages/Login/Login.tsx`
- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `docs/UX_UI_DESIGN_SYSTEM.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm run build --prefix client`：通过。
- `docker compose up --build -d web`：通过。
- 浏览器走查首页和素材库 Agent 面板：正常。

### 遗留问题

- 这次先完成基础视觉体系统一和重点入口质感升级；后台深层表格、弹窗、搜索运营/API 中心的细节间距和信息密度后续可以继续做第二轮 UI 精修。
- 动效目前为 CSS 原创实现；若以后要使用外部开源动画资源，必须先确认商业授权。

### 下一步

1. 按同一视觉变量继续扫后台页面，把表格、筛选条和数据卡片的间距统一。
2. 如果确认要让“搜索结果动态推荐理由”接模型测试，可在 API 中心给 `搜索结果：动态推荐理由` 单独选择一个现有 API Key，再做缓存/异步增强。
3. 做一次完整设计走查：登录页、素材库、搜索结果、素材详情、API 中心、搜索运营。

---

## 2026-08-25：搜索结果动态推荐理由重构

### 本轮目标

- 让旧“结果推荐语”模块退场，不再要求管理员为每个卖点维护一条固定展示话术。
- 搜索结果卡片改为解释“当前这张图为什么适合本次搜索”，服务市场/运营选图，而不是素材库 Agent 的销售问答场景。
- 预留 API 中心任务位，后续可接低成本多模态模型做异步/批量增强。

### 完成内容

- 后台导航和路由移除“推荐语”入口，旧页面文件和数据库字段保留为兼容历史，不做破坏性删除。
- `ScoredImage` 新增 `result_recommendation_reason`，后端按图片标题、渠道、素材组画面属性、命中卖点关系、证明点/证据点、素材独有话术和召回理由生成动态推荐说明。
- 前端搜索结果卡片优先展示动态推荐说明；没有动态说明时继续退回证明点 claim、素材话术等旧兜底。
- API 中心新增 `search_result_recommendation_reason` 任务槽，当前不在实时搜索中同步调用模型，避免增加搜索延迟和成本。

### 修改文件

- `backend/app/ai/contracts.py`
- `backend/app/ai/openai_compatible.py`
- `backend/app/schemas/api_center.py`
- `backend/app/schemas/image.py`
- `backend/app/services/api_center_service.py`
- `backend/app/services/search_scorer.py`
- `backend/scripts/stress_api_center_scheduler.py`
- `backend/tests/test_search_result_recommendation_reason.py`
- `client/src/app.tsx`
- `client/src/components/Layout.tsx`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/searchConceptPresentation.ts`
- `client/src/pages/ImageHome/SemanticSearchResult/searchConceptPresentation.test.ts`
- `client/src/types/api.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无新增数据库迁移。
- `business_concepts.recommendation_text` 暂时保留为历史兼容字段，不再作为结果卡推荐说明的主来源。

### 测试结果

- `backend/.venv/bin/python -m ruff check ...`：通过。
- `cd backend && .venv/bin/python -m pyright ...`：`0 errors`。
- `cd backend && .venv/bin/python -m pytest tests/test_search_result_recommendation_reason.py tests/test_api_center.py tests/test_search_service.py -q`：`22 passed`。
- `npm test --prefix client -- searchConceptPresentation.test.ts`：`11 passed`。
- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。

### 遗留问题

- 当前动态推荐理由是确定性规则生成，适合实时搜索；更细的图像级营销文案需要后续接入低成本多模态模型池，建议走异步或缓存，不直接拖慢搜索。
- 旧推荐语管理页面文件仍保留但已不在导航和路由暴露；若后续确认彻底废弃，可另起安全清理任务。

### 下一步

1. 走查真实搜索结果卡片，确认推荐理由语气是否符合市场/运营场景。
2. 若需要更强“按图解释”，用 API 中心 `search_result_recommendation_reason` 槽位接便宜多模态模型，并做缓存/批处理。
3. 再进入架构体检和补丁清理，重点确认旧推荐语接口是否还有运行引用。

## 2026-08-25：动态结果推荐理由进入第五层真实调度（D217）

### 本轮目标

- 让搜索结果卡的“为什么这张图适合当前搜索句”真正调用 API 中心任务，而不是只有本地规则文案。
- 在管理员调用链路日志中独立显示第五层动态推荐理由，并保持模型失败时搜索可用。

### 完成内容

- 新增 `search_result_recommendation_reason` 批量模型契约和严格归一化，只接受输入候选中的 `image_id` 与理由。
- 在候选召回、排序、Reranker、第四层候选复核全部完成后新增独立第五层，默认解释前 12 张结果，超时 6 秒，可通过配置调整。
- 模型只读取当前查询、已确认搜索理解、图片事实、人工 accepted 卖点关系、证明点/证据点、素材独有话术和召回理由，不参与召回、排序、候选准入或业务事实写入。
- 未配置、失败、超时或返回不合规时，结果卡继续使用现有本地确定性推荐理由；诊断和 API 中心日志保留第五层 skipped/failed/timed_out 状态，不把解释增强失败当作搜索失败。
- 身份码和分享链接精确查找继续走确定性查询，不调用第五层模型。

### 修改文件

- `backend/app/ai/normalizer.py`
- `backend/app/ai/skill_loader.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/search_result_recommendation_service.py`
- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_diagnostics_service.py`
- `backend/app/services/search_service.py`
- `backend/app/services/search_service_components.py`
- `backend/app/api/dependencies.py`
- `backend/app/core/config.py`
- `backend/app/schemas/ai.py`
- `docker-compose.yml`
- `.env.docker.example`
- `skills/INDEX.md`
- `backend/tests/test_search_result_recommendation_reason.py`
- `backend/tests/test_project_skills.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`

### 数据迁移

- 无新增数据库迁移；复用已有 `model_call_traces` 记录 Provider attempt。

### 验证

- `tests/test_search_result_recommendation_reason.py tests/test_project_skills.py tests/test_api_center.py`：`17 passed`。
- `tests/test_search_service.py tests/test_ai_provider.py tests/test_taxonomy_catalog.py tests/test_documentation_consistency.py`：`39 passed`。
- 定向 Ruff：通过；定向 Pyright：`0 errors`；`git diff --check`：通过。
- 完整 Phase 4 搜索编排回归仍有 3 个既有意图/候选边界失败，与第五层结果解释分支无关；本轮未改动这些上游业务规则。
- 内置浏览器当前没有活动标签页，未完成可视化刷新核验；API 中心现有前端已包含第五层任务标签和调用链路展示。

### 遗留问题

- 当前第五层批量模型调用默认只覆盖最终前 12 张，超过部分保留本地理由；若真实部署结果量更大，应结合延迟和成本再决定是否接缓存或异步刷新。

---

## 2026-08-25：素材库 Agent 气泡、会话菜单与思考态打磨

### 本轮目标

- 让右下角 Agent 小球更像可亲近的助手，而不是不显眼的孤立按钮。
- 修正聊天记录下拉箭头和胶囊控件对不齐的问题。
- 让 Agent 等待回复时展示更明确的“正在思考”过程。

### 完成内容

- Agent 闭合态改为“小球 + 左上角气泡”，气泡文案采用多条短句上下滚动。
- 会话切换从透明原生 `select` 改为自定义弹出菜单，图标、标题、时间和箭头在同一个 flex 胶囊内对齐。
- 回复等待状态改为大白框思考态，展示读取图片上下文、对照卖点话术、组织业务表达三个步骤，并自动滚动到最新消息。
- 会话选择焦点态改成黑灰细环，避免浏览器默认蓝色焦点框破坏整体视觉。
- 设计规范和总纲新增 D204，固化 Agent 入口、会话菜单和思考态的 UI 边界。

### 修改文件

- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `client/src/tailwind-theme.css`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`
- `docs/UX_UI_DESIGN_SYSTEM.md`

### 数据迁移

- 无。

### 测试结果

- `npm run typecheck --prefix client`：通过。
- `npm run lint --prefix client`：通过。
- `npm run build --prefix client`：通过。
- 本地 web 容器静态包已同步，`docker compose ps -a` 显示 backend/web/postgres/meilisearch 均 healthy。
- 浏览器走查首页 Agent 闭合态、会话菜单展开态：正常。

### 遗留问题

- 当前为前端交互打磨，不改变 Agent 后端回答质量、API 调度或聊天记录 24 小时过期策略。

### 下一步

1. 运行前端检查与构建。
2. 重新打开首页，走查闭合气泡、会话菜单展开和发送消息后的思考态。

---

## 2026-08-25：素材库 Agent 正式部署前收口（D206）

### 本轮目标

- 补齐 D205 从测试版本地会话迁移到正式用户私有会话后的残余边界。
- 清理旧版 Agent 可能留在浏览器中的本地聊天记录，避免账号切换时继续显示旧数据。
- 让接口契约、失败降级提示和管理员越权回归完整可验收。

### 完成内容

- 新增 `clearLegacyAssetAgentStorage`，Agent 初始化时定向删除旧版会话键，不触碰搜索、渠道、项目夹等其他浏览器设置。
- 后端会话加载失败时保留当前页面临时记录，但界面明确显示“当前页面临时记录，未写入账号”，避免把未落库内容误称为个人历史。
- 增加管理员更新他人会话图片上下文的越权回归，和读取、发送、删除一样返回 `404`。
- 从当前 FastAPI `/openapi.json` 重新生成前端 `openapi.d.ts`，补齐 Agent 会话接口和其他近期后端接口契约。

### 修改文件

- `client/src/features/assets/assetAgentStorage.ts`
- `client/src/features/assets/assetAgentStorage.test.ts`
- `client/src/pages/ImageHome/AssetAgentWidget.tsx`
- `backend/tests/test_asset_agent_service.py`
- `client/src/types/openapi.d.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无新增迁移。
- 本地 Alembic 当前为 `20260825_0024 (head)`。

### 测试结果

- 后端 Agent 隐私专项：`2 passed`。
- 后端定向 Ruff：通过。
- 后端定向 Pyright：`0 errors`。
- 前端 typecheck、lint、Vitest：`45 passed`。
- 前端 production build：通过。
- `git diff --check`：通过。
- 内置浏览器走查：业务用户页面能加载个人 Agent 会话，显示“个人记录”；会话菜单、删除入口和 Agent 面板正常。

### 遗留问题

- 本地开发服务需要保持运行，浏览器才能继续走查；正式部署时仍需在目标环境执行 `20260825_0024` 迁移并重新生成/发布前端静态包。
- 当前保留 24 小时过期和最近 20 条限制，这是产品边界，不是管理员可见的审计留存。

### 下一步

1. 部署到正式 PostgreSQL 前先备份数据库并执行 Alembic upgrade。
2. 使用两个真实账号各自产生一条 Agent 记录，验证跨浏览器/跨设备只显示各自会话。
3. 发布前确认 SESSION_COOKIE_SECURE、CORS_ORIGINS 和 CSRF 配置与正式域名一致。

---

## 2026-08-25：管理员身份码台账（D216）

### 本轮目标

- 给管理员提供一个正式后台入口，持续查看所有素材组身份码和图片版本码。
- 保持身份码由系统自动分配，不提供手工修改、复用或重新分配能力。
- 新增图片后无需额外同步任务即可出现在后台台账。

### 完成内容

- 新增只读管理员接口 `GET /api/admin/identity-codes`，支持按身份码、素材标题、图片标题和文件名搜索，按素材码/版本码、当前有效/已删除/已退休筛选，并提供分页和统计摘要。
- 新增 `AssetIdentityRepository`、`AssetIdentityAdminService` 和身份码 schema，直接查询永久身份登记表及素材组/图片关联。
- 新增管理员页面 `/admin/identity-codes`，展示素材组数、图片版本数、有效码和历史码统计，支持复制身份码、查看素材详情和刷新台账。
- 新增后台一级导航“身份码管理”；业务用户和设计师不具备接口或页面访问权限。
- 台账不展示数据库 UUID、存储路径、密钥等内部信息，不提供身份码编辑入口。

### 修改文件

- `backend/app/api/v1/asset_identity.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/router.py`
- `backend/app/repositories/asset_identity_repository.py`
- `backend/app/schemas/asset_identity.py`
- `backend/app/services/asset_identity_admin_service.py`
- `backend/tests/test_asset_identity_codes.py`
- `client/src/api/admin.ts`
- `client/src/app.tsx`
- `client/src/components/Layout.tsx`
- `client/src/pages/AdminIdentityCodes/AdminIdentityCodes.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无新增迁移；复用 D210 已建立的 `asset_identity_codes` 永久登记表。

### 测试结果

- 后端身份码专项：`3 passed`。
- 后端 Ruff：通过。
- 后端 Pyright：`0 errors`，保留 1 条既有泛型警告。
- 前端 typecheck：通过。
- 前端 ESLint：通过。
- 前端 Vitest：`45 passed`。
- 前端 production build：通过。
- `git diff --check`：通过。
- 内置浏览器验证：管理员台账显示当前本地库 40 个素材组、40 个图片版本、80 个有效身份码；搜索素材名称可同时定位素材码和版本码，详情跳转正常。

### 遗留问题

- 生产部署前仍需在目标环境执行已有 `20260825_0025_asset_identity_codes` 迁移，并确认历史素材已完成补码。
- 当前页面是只读台账；如未来需要批量导出、审计变更或按组织隔离，需要另行定义权限和数据边界，不在本轮扩大。

### 下一步

1. 正式部署前备份数据库，执行 Alembic upgrade head。
2. 用一张新上传图片验证身份码登记表和管理员台账实时出现。
3. 发布前复核管理员、设计师和业务用户的页面与接口权限。

---

## 2026-08-25：全项目 API 调度统一遥测（D218）

### 本轮目标

- 让 API 中心统一看到项目中所有模型/API 调用的结果，而不是只看到搜索链路。
- 对每次调用明确记录 `OK`、失败、超时和未配置/跳过。
- 保持 API Key、Prompt、图片内容和用户私有 Agent 对话不进入管理员调用日志。

### 完成内容

- `ApiCenterScheduledModelProvider` 在普通模型调用结束时直接写入 `model_call_traces`，覆盖上传主图分析、上传前素材话术、搜索五层、素材库 Agent 和兼容文案卖点匹配。
- 管理员健康检查复用同一调用台账，同时保留原有健康检查表用于 API 健康状态和巡检历史。
- Embedding、Reranker、Meilisearch 搜索增强及索引调用通过统一外部 API 遥测入口写入调用台账。
- 搜索日志不再重复写入调用台账；API 中心页面文案改为“全项目 API 调用链路”，状态展示为 OK、失败、超时、未配置/跳过。
- 遥测只保存任务、层级、Provider、模型、状态、耗时和安全错误摘要，不保存完整密钥、Authorization、Prompt、图片字节、外部响应或私有 Agent 聊天正文。

### 修改文件

- `backend/app/services/api_center_service.py`
- `backend/app/services/search_log_service.py`
- `backend/app/services/semantic_search_clients.py`
- `backend/app/services/meilisearch_recall_service.py`
- `backend/app/services/meilisearch_client.py`
- `backend/app/ai/contracts.py`
- `backend/app/schemas/api_center.py`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无新增迁移，继续复用 `model_call_traces`。

### 测试结果

- API 中心、素材库 Agent、动态推荐理由、Provider 定向回归：`29 passed`。
- Ruff：通过。
- Pyright：`0 errors`。
- 前端 TypeScript typecheck：通过。
- 前端 ESLint：通过。
- `git diff --check`：通过。

### 遗留问题

- 当前外部搜索 API 遥测使用独立数据库会话写入，以保证索引/语义增强失败不会影响主搜索；正式多实例部署时可进一步抽成异步遥测队列。

### 下一步

1. 在内置浏览器刷新 API 中心，确认全项目调用链路文案和状态标签。
2. 正式部署前执行现有 Alembic 迁移并用真实上传、搜索、Agent、健康检查各跑一遍，确认台账都有记录。

---

## 2026-08-29：API 中心调用链路日志升级（D242）

### 本轮目标

- 让调用链路日志可按历史分页查询，不再只能看 summary 最近 100 条。
- 把 Provider 和调度内部已有的稳定错误码持久化到调用台账，避免只能靠中文摘要排查。
- 保持日志安全边界，不保存完整 Key、Prompt、图片字节、私有聊天正文或上游原文。

### 完成内容

- `model_call_traces` 新增 `error_code` 字段并建立索引。
- 健康探测、运行时调度、预算耗尽、容量等待、取消、未配置和外部 API 遥测统一写入 `error_code`。
- 新增管理员接口 `/api/admin/api-center/call-traces`，支持按任务、状态、中转站、API、请求 ID、搜索关键词、错误码或摘要筛选，并返回 `total/limit/offset/hasMore`。
- API 中心“调用链路日志”页升级为筛选 + 分页表，错误摘要旁显示稳定错误码；summary 仍保留轻量最近调用。

### 修改文件

- `backend/alembic/versions/20260829_0032_api_call_trace_error_code.py`
- `backend/app/api/v1/api_center.py`
- `backend/app/models/api_provider.py`
- `backend/app/repositories/api_center_repository.py`
- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_service.py`
- `backend/tests/test_api_center.py`
- `client/src/api/admin.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/API_CENTER_RELIABILITY_REQUIREMENTS.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 新增 Alembic 迁移 `20260829_0032_api_call_trace_error_code.py`。
- Docker Postgres 当前版本：`20260829_0032 (head)`。

### 测试结果

- Docker API Center 专项：`57 passed`。
- Docker 后端全量：`351 passed, 4 skipped`。
- 前端生产构建：通过。
- 前端 ESLint：通过。
- 前端 Vitest：`16 files / 51 tests passed`。
- 容器运行镜像未安装 ruff，未能在容器内执行 `python -m ruff check app tests/test_api_center.py`。

### 遗留问题

- 日志保留期限、归档和清理策略尚未实现，仍属于后续生产化治理。
- 多 backend 共享容量账本和共享遥测队列仍按既有决策延期。

### 下一步

1. 在浏览器刷新 API 中心，进入“调用链路日志”验证筛选、分页和错误码显示。
2. 后续可继续补日志保留策略、错误码分组统计和异常趋势图。

---

## 2026-08-29：API 中心错误码治理与故障分级（D243）

### 本轮目标

- 把错误码从“日志字段”升级为统一治理目录。
- 让健康检查、温度探测和调用链路返回同一套故障分类、严重度、可重试性、系统动作和管理员建议。
- 为下一波自动巡检、自动退避和自动恢复建立可执行的故障语义基础。

### 完成内容

- 新增 `api_center_error_catalog.py`，集中维护配置、鉴权、连接、容量、限流、上游、等待、兼容、响应契约、取消、调度和未知故障分类。
- `ApiHealthCheckRead`、`ApiTemperatureProbeRead`、`ApiCallTraceRead` 新增分类字段：`errorCategory`、`errorSeverity`、`errorRetryable`、`errorSystemAction`、`errorOperatorAction`。
- `model_api_health_checks` 新增 `error_code`，健康探测现在把稳定错误码写入健康快照。
- OpenAI-compatible Provider 的异常 attempt 补写 `error_code`；取消类错误统一为 `request_cancelled`。
- API 中心调用链路页面显示错误码、故障类别、严重度、可重试性、系统动作和管理员建议，不再只显示一段错误摘要。

### 修改文件

- `backend/alembic/versions/20260829_0033_api_health_check_error_code.py`
- `backend/app/ai/contracts.py`
- `backend/app/ai/openai_compatible.py`
- `backend/app/models/api_provider.py`
- `backend/app/schemas/api_center.py`
- `backend/app/services/api_center_error_catalog.py`
- `backend/app/services/api_center_service.py`
- `backend/tests/test_api_center.py`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `docs/API_CENTER_RELIABILITY_REQUIREMENTS.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 新增 Alembic 迁移 `20260829_0033_api_health_check_error_code.py`。
- Docker Postgres 当前版本：`20260829_0033 (head)`。

### 测试结果

- Docker 重建：通过。
- API Center + Provider 定向：`84 passed`。
- 前端 ESLint：通过。

### 遗留问题

- 自动巡检、日志保留、自动退避和自动恢复尚未实现。
- 当前错误分类目录先覆盖已有稳定错误码；未来新增 Provider 适配器时需要把新错误码登记到同一目录。

### 下一步

1. 第八波在错误分类基础上实现服务器定时巡检和日志保留策略。
2. 第九波使用 `errorCategory/errorRetryable/errorSeverity` 做自动退避、隔离和恢复。

---

## 2026-08-30：专项培优公共话术深挖（D245）

### 本轮目标

- 按业务负责人要求，从当前选中卖点 `专项培优 focused_excellence` 开始逐个卖点治理公共话术。
- 这轮追求“更像真实业务会搜索的话”，不是单纯把每个卖点凑到固定数量。
- 在补充命中表达的同时，压住过宽短词，避免泛化搜索被单一卖点硬抢。

### 完成内容

- 新增可幂等执行脚本 `backend/scripts/curate_focused_excellence_phrases.py`。
- 将 `提分`、`突破`、`考前`、`重点`、`高频`、`能力进阶` 等 6 条过宽短词标记为 rejected。
- 新增 70 条 `专项培优` 公共话术，覆盖：
  - 薄弱题型、专项模块、单项强化。
  - 重难点、压轴题、高阶拔高。
  - 考前阶段、临考复习、划重点。
  - 全网/群体高频易错题。
  - 业务端可能输入的长句、口语句、场景句和痛点句。
- 当前 `专项培优` 话术统计：124 条 accepted、6 条 rejected。
- 重建 Meilisearch 图片搜索索引，提交 377 条 image search documents。

### 修改文件

- `backend/scripts/curate_focused_excellence_phrases.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 数据变更来源标记为 `focused_excellence_curation_20260830`。

### 测试结果

- 脚本编译通过。
- 脚本 dry-run 幂等验证通过：再次执行不会重复新增。
- 后端定向测试：`91 passed`。
- Docker 健康检查：`{"status":"ready","environment":"production"}`。
- 真实库搜索冒烟：
  - `针对薄弱题型集中练` 命中 `专项培优`。
  - `全网高频错题集中练` 命中 `专项培优`。
  - `考前只想抓最容易涨分的模块` 命中 `专项培优`。
  - `根据薄弱点推荐内容` 仍归 `AI定制学习方案`。
  - `想给孩子提分` 不会被 `专项培优` 硬抢。

### 遗留问题

- 其余卖点还没有逐个深挖治理；此前阶段性批量补充的话术仍需要按卖点继续人工式审查。
- 当前优化不改变搜索主链路，因此长期能力仍依赖后续持续补充卖点边界、公共话术和素材独有话术。

### 下一步

1. 按同样方法继续治理下一个卖点：先读业务边界，再审现有短词，再补长短句/场景句/痛点句，最后跑边界搜索验证。
2. 对每个卖点保留 rejected 宽泛词记录，防止后续批量导入又把边界冲散。

---

## 2026-08-30：举一反三公共话术深挖（D246）

### 本轮目标

- 继续按“一个卖点一个卖点过”的方式治理 `举一反三 transfer_practice`。
- 补充真实业务搜索里会出现的完整表达，而不是只堆标准短词。
- 保护相邻边界，避免挤占 `万能解法`、`AI拍题精学`、`AI错题本`。

### 完成内容

- 新增可幂等执行脚本 `backend/scripts/curate_transfer_practice_phrases.py`。
- 将 `训练`、`迁移`、`换题` 等 3 条单独使用时证据不足的过宽短词标记为 rejected。
- 保留 `迁移练习`、`换题也会`、`变式题训练`、`同类题训练` 等完整表达。
- 新增 81 条 `举一反三` 公共话术，覆盖：
  - 先理解原理、出题逻辑和题型本质。
  - 讲完一道题后继续练同类题、相似题、变式题。
  - 换数字、换条件、换问法、考试题拐弯后仍能做。
  - 拍题讲解后继续推相似题的支撑表达。
  - 家长、销售、汇报场景里的长句、口语句和痛点句。
- 当前 `举一反三` 话术统计：138 条 accepted、3 条 rejected。
- 重建 Meilisearch 图片搜索索引，提交 377 条 image search documents。

### 修改文件

- `backend/scripts/curate_transfer_practice_phrases.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 数据变更来源标记为 `transfer_practice_curation_20260830`。

### 测试结果

- 脚本编译通过。
- `git diff --check` 通过。
- 后端相邻边界测试：`107 passed`。
- 禁用外部模型的真实库搜索冒烟：
  - `理解原理再做变式题` 命中 `举一反三`。
  - `一题讲完后还能顺着练同一类题` 命中 `举一反三`。
  - `孩子例题会做考试题一绕就懵` 命中 `举一反三`。
  - `同一道题不同方法` 仍归 `万能解法`。
  - `个人错题练会一类题` 仍归 `AI错题本`。
  - `训练` 单独不再硬抢 `举一反三`。

### 遗留问题

- `拍题讲解后继续推相似题` 当前真实库搜索可命中 `举一反三`；如果后续业务希望它必须稳定展示为 `AI拍题精学 + 举一反三` 双卖点，需要单独补充多卖点治理规则或 AI 拍题公共话术。
- 其余卖点仍需继续逐个深挖；此前阶段性批量补充的话术还需要按卖点审查。

### 下一步

1. 继续按相同流程治理下一个卖点。
2. 每个卖点都保留“新增强表达 + 拒绝过宽词 + 相邻边界验证”的记录，避免后续批量补充冲坏边界。

---

## 2026-08-30：学段衔接公共话术深挖（D247）

### 本轮目标

- 继续按“一个卖点一个卖点过”的方式治理 `学段衔接 stage_transition`。
- 强化小升初、初升高、新学段断层、小初高一体化等真实业务搜索表达。
- 保护相邻边界，避免挤占 `同步校内`、`AI定制学习方案`、`专家规划` 和 `极速预习复习`。

### 完成内容

- 新增可幂等执行脚本 `backend/scripts/curate_stage_transition_phrases.py`。
- 将 `升学`、`学段`、`衔接`、`路径`、`过渡`、`适应`、`难度`、`难度突然变大` 等 8 条单独使用时证据不足的过宽短词标记为 rejected。
- 保留 `小升初衔接`、`初升高衔接`、`升学过渡`、`新学段适应慢` 等完整表达。
- 新增 82 条 `学段衔接` 公共话术，覆盖：
  - 小升初、初升高、幼小衔接等关键升学节点。
  - 新学段知识断层、难度跃迁、学习方式变化和平稳过渡。
  - 小初高一体化、从小学到高中、12 年路径和全学段连续覆盖。
  - 衔接期学习建议和同步/拔高/衔接一站式表达。
  - 家长、销售、汇报场景里的长句、口语句和痛点句。
- 当前 `学段衔接` 话术统计：134 条 accepted、8 条 rejected。
- 重建 Meilisearch 图片搜索索引，提交 377 条 image search documents。

### 修改文件

- `backend/scripts/curate_stage_transition_phrases.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 数据变更来源标记为 `stage_transition_curation_20260830`。

### 测试结果

- 脚本编译通过。
- `git diff --check` 通过。
- 脚本 dry-run 幂等验证通过：再次执行不会重复新增。
- Docker 健康检查：`{"status":"ready","environment":"production"}`。
- 后端相邻边界测试：`114 passed`。
- 禁用外部模型的真实库搜索冒烟：
  - `小升初暑期衔接课` 命中 `学段衔接`。
  - `初升高知识断层怎么补` 命中 `学段衔接`。
  - `孩子升学后怕课程难度突然变大` 命中 `学段衔接`。
  - `从小学到高中不用换体系` 命中 `学段衔接`。
  - `教材版本同步` 仍归 `同步校内`。
  - `学习路径自动规划` 仍归 `AI定制学习方案`。
  - `命题专家设计初升高衔接课程` 保持 `学段衔接 + 专家规划` 多卖点。

### 遗留问题

- 当前真实素材库缺少独立的“小初高一体化 / 全学段连续覆盖”强展示图；相关查询已经能识别为 `学段衔接`，但结果会借用已有配套素材承接。
- 后续应补一张或一组专门表达“从小学到高中连续覆盖 / 不用换体系 / 12 年路径”的素材，避免全学段查询看起来不像命中的卖点。
- 其余卖点仍需继续逐个深挖；此前阶段性批量补充的话术还需要按卖点审查。

### 下一步

1. 继续按相同流程治理下一个卖点。
2. 对 `学段衔接` 后续补素材时，优先补全学段连续覆盖图，而不是继续只堆话术。

---

## 2026-08-30：动画精讲公共话术深挖（D248）

### 本轮目标

- 继续按“一个卖点一个卖点过”的方式治理 `动画精讲 animation_explanation`。
- 强化动画讲透知识点、抽象知识可视化、短时动画微课和课堂补位等真实业务搜索表达。
- 保护相邻边界，避免挤占 `AI拍题精学`、`极速预习复习`、`课后小测` 和纯画面动画搜索。

### 完成内容

- 新增可幂等执行脚本 `backend/scripts/curate_animation_explanation_phrases.py`。
- 将 `动画`、`卡住`、`可视化`、`听不懂`、`故事`、`演示`、`直观`、`知识点`、`讲解`、`课程`、`跟不上课` 等 11 条单独使用时证据不足的过宽短词标记为 rejected。
- 保留 `动画精讲`、`动画课程`、`动画讲透知识点`、`抽象知识可视化`、`短时间讲透知识点` 等完整表达。
- 新增 87 条 `动画精讲` 公共话术，覆盖：
  - 动画、故事化、可视化讲透知识点。
  - 5-8 分钟短时动画微课、一节课一个点讲透。
  - 老师讲太快、课堂没听懂、抽象知识听不懂后的补位。
  - 抽象知识动态化、看不见的变化过程变成可见动画。
  - 学科原理动画演示和具体课例入口。
  - 动画课程教研方法论、课程打磨和业务汇报场景。
- 当前 `动画精讲` 话术统计：136 条 accepted、11 条 rejected。
- 重建 Meilisearch 图片搜索索引，提交 377 条 image search documents。

### 修改文件

- `backend/scripts/curate_animation_explanation_phrases.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 数据变更来源标记为 `animation_explanation_curation_20260830`。

### 测试结果

- 脚本编译通过。
- `git diff --check` 通过。
- 后端相邻边界测试：`123 passed`。
- 禁用外部模型的真实库搜索冒烟：
  - `找动画精讲素材能把抽象知识动态讲透` 命中 `动画精讲`。
  - `要一张把看不见的知识变成能动过程的画面` 命中 `动画精讲`。
  - `想要把难概念讲成小故事的画面` 命中 `动画精讲`。
  - `课堂没听懂回家看动画补懂` 命中 `动画精讲`。
  - `不要拍照搜题要动画精讲` 命中 `动画精讲`。
  - `拍题后分步分析思路` 仍不归 `动画精讲`。
  - `课前快速过知识点` 仍归 `极速预习复习`。
  - `动画` 单独不再硬抢 `动画精讲`。

### 遗留问题

- `刚讲完一个知识点想马上练几题确认` 更接近 `课后小测`，但当前本地链路偏向 `极速预习复习`；后续治理 `课后小测` 时应处理。
- 当前优化不新增学校课堂效果实证素材；点名学校案例、成绩提升或课堂落地效果的查询仍应按既有缺口规则处理。

### 下一步

1. 继续按相同流程治理下一个卖点。
2. 后续治理 `课后小测` 时，重点处理“学完/刚讲完知识点后马上练题确认掌握”和极速预习复习的边界。

---

## 2026-08-31：课后小测公共话术深挖（D249）

### 本轮目标

- 继续按“一个卖点一个卖点过”的方式治理 `课后小测 instant_quiz`。
- 强化“学完/刚讲完/看完课/本节课 + 马上测/练几题/确认会不会/本节掌握度”的真实业务搜索表达。
- 保护相邻边界，避免挤占 `极速预习复习`、`学情报告反馈` 和 `AI错题本`。

### 完成内容

- 新增可幂等执行脚本 `backend/scripts/curate_instant_quiz_phrases.py`。
- 将 `分数`、`反馈`、`学习结果看得见`、`学完`、`掌握`、`掌握情况`、`检测`、`正确率`、`测验`、`结果`、`题目`、`日日清` 等 12 条单独使用时证据不足的过宽短词标记为 rejected。
- 保留 `课后小测`、`学完即测`、`学完马上测`、`学练测闭环`、`课后小测反馈正确率` 等完整表达。
- 新增 84 条 `课后小测` 公共话术，覆盖：
  - 学完当前知识点马上小测、看完课立即做题确认掌握。
  - 刚讲完知识点马上练几题、刚学完一段内容就做小测。
  - 本节课掌握度、即时反馈、正确率和配套练习。
  - 孩子说听懂了但不知道真会不会等家长痛点。
  - 销售、汇报、手机端/PPT 素材检索场景里的长句、短句和口语句。
- 收口相邻 `极速预习复习 rapid_preview_review` 的 `知识点`、`课后` 两条过宽公共话术，避免“刚讲完知识点马上练几题确认”被快速复习误抢。
- Skill 公共话术治理规则新增 `instant-quiz-13/14` 校准样例，并补充 `刚讲完/刚学完 + 马上练几题/确认会不会` 组合信号。
- 当前 `课后小测` 话术统计：132 条 accepted、12 条 rejected。
- 重建 Meilisearch 图片搜索索引，提交 387 条 image search documents。

### 修改文件

- `backend/scripts/curate_instant_quiz_phrases.py`
- `backend/tests/test_query_states_and_negation.py`
- `skills/understand-image-search-intent/references/public-phrase-governance.json`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 数据变更来源标记为 `instant_quiz_curation_20260830`。
- 当前真实库状态同步记录：386 个素材组、388 张图片、16 个业务概念、477 条人工 accepted 关系。

### 测试结果

- backend 重建通过。
- 脚本编译通过。
- `git diff --check` 通过。
- 后端相邻边界测试：`124 passed`。
- Docker 健康检查：`{"status":"ready","environment":"production"}`。
- 禁用外部模型的真实库搜索冒烟：
  - `刚讲完一个知识点想马上练几题确认` 只命中 `课后小测`。
  - `刚讲完一个知识点想配个马上练几题确认的素材` 只命中 `课后小测`。
  - `看完课立即做题确认掌握` 命中 `课后小测`。
  - `希望素材能表现学完后马上知道到底会不会` 命中 `课后小测`。
  - `课后小测反馈本节正确率` 命中 `课后小测`。
  - `课前快速过知识点` 仍归 `极速预习复习`。
  - `每周报告汇总正确率`、`反馈`、`正确率` 仍归 `学情报告反馈`。
  - `个人错题以后复习` 仍归 `AI错题本`。

### 遗留问题

- `课后小测` 当前已有重复 `课后小测` accepted 记录，未影响搜索结果；后续可做公共话术去重治理，但本轮不做结构性清洗。
- 当前优化不新增真实素材，只提升现有素材对真实业务检索话术的承接能力。

### 下一步

1. 继续按同样流程治理下一个卖点。
2. 后续可以单独做公共话术去重和宽词审计，把批量补词阶段留下的重复项、同义项和弱证据短词继续收干净。

---

## 后续日志模板

## 2026-09-01：火山 VikingDB 旁路同步接入第一步

### 本轮目标

将火山 VikingDB 作为图片搜索的旁路向量索引接入项目，先支持从当前数据库派生素材搜索文档并批量写入火山测试数据集，不替换现有搜索主链路。

### 完成内容

- 新增 VikingDB REST 客户端，按官方 `data/upsert` 形态提交 `collection_name`、`async` 和 `data`。
- 新增 `image_asset` 向量文档映射：从当前图片、素材组、人工 accepted 卖点关系、公共话术、素材独有话术和图片语义摘要生成 `search_text`。
- 新增旁路同步服务，支持 dry-run 预览、100 条以内分批提交、未配置时自动跳过。
- 上传、替换主图、延展图、回收站恢复、AI 分析完成、素材人工卖点关系和素材独有话术变更后，会在原有索引刷新点上 best-effort 同步火山；默认关闭，不影响现有搜索主链路。
- 新增重建脚本 `backend/scripts/rebuild_vikingdb_index.py`，用于后续把现有素材批量同步到火山。
- 新增环境变量样例，默认 `VIKINGDB_ENABLED=false`，保持不影响现有搜索结果。

### 修改文件

- `backend/app/core/config.py`
- `backend/app/services/vikingdb_client.py`
- `backend/app/services/vikingdb_vector_index.py`
- `backend/scripts/rebuild_vikingdb_index.py`
- `backend/tests/test_search_index.py`
- `backend/.env.example`
- `.env.docker.example`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 火山 VikingDB 当前作为可重建派生索引，不作为业务事实源。

### 测试结果

- `PYTHONPYCACHEPREFIX=/tmp/piancton-pycache backend/.venv/bin/python -m py_compile ...` 通过。
- `backend/.venv/bin/ruff check ...` 通过。
- `git diff --check` 通过。
- 轻量导入检查通过：VikingDB 客户端配置判断、默认数据集名和 disabled sync 均符合预期。
- 当前会话 Docker 权限/用量限制导致容器内 pytest 暂未跑成；本地 pytest 入口会先加载既有 `api_center.py`，在当前 Python 解释器下触发已有类型注解兼容问题，未能用于本轮完整回归。

### 遗留问题

- 当前只同步 `doc_type=image_asset`。卖点卡片、公共话术、证明点作为独立向量文档的同步留到第二步。
- 当前只接入写入同步；搜索主链路仍未读取火山结果，后续应先做后台旁路检索诊断，再决定是否进入正式召回。

### 下一步

1. 配置火山 API Key 后执行 dry-run 和真实小批量 upsert。
2. 增加旁路检索诊断接口，用真实查询对比现有搜索与火山召回。
3. 稳定后再评估是否把火山召回作为主搜索候选之一。

---

## 2026-09-02：火山体系/卖点知识旁路

### 本轮目标

按用户确认的新方向，把火山向量库第一阶段收敛为“体系 + 卖点”两层高质量知识索引。先让向量检索帮助判断用户话术命中哪个体系、哪个卖点；命中后仍回本地数据库按人工 accepted 关系返回素材图。公共话术不自动全量灌入，后续按体系逐轮精修后再补充。

### 完成内容

- 新增 `system` 知识文档生成：每个体系一条，用于第一层体系路由，包含体系名、code、包含卖点和体系边界。
- 新增 `selling_point` 知识文档生成：每个核心卖点一条，用于第二层卖点识别，包含一句话判定、背后意思、边界逻辑、本体定义、对象、动作、目的、正向信号、排除边界、易混卖点和判定规则。
- 新增 `upsert_knowledge_documents` 同步入口，和图片同步入口分离，避免把图片文档、证明点或公共话术一起写入。
- 新增 `backend/scripts/rebuild_vikingdb_knowledge_index.py`，专门重建体系/卖点知识索引。
- 测试约束知识文档固定为 6 条体系 + 16 条卖点，且 `doc_type` 只能是 `system` 和 `selling_point`。

### 修改文件

- `backend/app/services/vikingdb_vector_index.py`
- `backend/scripts/rebuild_vikingdb_knowledge_index.py`
- `backend/tests/test_search_index.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 火山仍是可重建派生索引，不作为业务事实源。
- 本轮不写入公共话术、不写入证明点、不替换现有搜索主链路。

### 测试结果

- `PYTHONPYCACHEPREFIX=/tmp/piancton-pycache backend/.venv/bin/python -m py_compile ...` 通过。
- `backend/.venv/bin/ruff check ...` 通过。
- `git diff --check` 通过。
- 轻量导入和计数检查通过：生成 22 条知识文档，类型为 `system` 与 `selling_point`。
- 本地 pytest 入口仍受当前解释器不支持既有 `task: str | None = Query(...)` 注解影响，未完成执行。
- 当前 Docker backend 容器不是最新代码镜像，容器内无法导入新增 `app.services.vikingdb_vector_index`，因此未把容器 pytest 计入本轮回归结论。

### 遗留问题

- 还没有把火山检索结果接入正式搜索，只完成知识文档写入准备。
- 公共话术需要按体系逐轮精修后再入库，不能从现有数据库全量自动灌入。
- 后续需要增加火山旁路查询诊断接口，用同一批搜索句对比体系/卖点命中结果。

### 下一步

1. 先执行知识文档 dry-run，确认 22 条内容是否符合业务表达。
2. 用户确认后小批量写入火山。
3. 再做只读旁路检索诊断，不影响现有业务端搜索结果。

---

## 2026-09-02：火山知识路由可开关接入

### 本轮目标

在已写入 6 条体系 + 16 条卖点知识文档的基础上，把火山 VikingDB 从“只读旁路诊断”推进为可开关的搜索路由层：开启后优先用火山判断用户话术命中哪个卖点，再回本地数据库按人工 accepted 关系返回素材；旧 Skill/模型链路保留为可关闭备份。

### 完成内容

- 将 VikingDB 检索接口修正为官方 `search/multi_modal` 形态，使用 `text` 触发服务端向量化，携带 `instruction.auto_fill`、`output_fields` 和结构化 `filter`。
- 新增 `VikingDBKnowledgeRouter`，只接受 `doc_type=selling_point` 的知识命中，并把 `concept_code` 映射回本地运行时启用概念。
- 新增 `VIKINGDB_KNOWLEDGE_ROUTER_ENABLED` 实验开关，默认关闭；开启后搜索服务优先尝试火山知识路由。
- 新增 `VIKINGDB_SKILL_BACKUP_ENABLED` 备份开关，默认开启；火山未命中或异常时继续走旧 Skill/模型链路，也可以关闭以观察纯火山效果。
- 火山候选召回默认从 8 个收敛为 5 个；项目最终最多接受 3 个卖点，常规查询应收敛到 1～2 个卖点。
- 多卖点输出增加保守规则：只有向量分数足够接近，且用户原话存在并列、递进或追加表达时，才从单卖点扩成多卖点。
- 新增轻量业务校准：`考前/临考/考试 + 复习/冲刺/抓重点` 优先归 `专项培优`，避免被 `极速预习复习` 的普通复习语义抢走。
- 生成真实探针报告 `docs/VIKINGDB_KNOWLEDGE_SEARCH_PROBE_2026-09-02.md`，用于记录火山检索延迟和命中结果。

### 修改文件

- `backend/app/core/config.py`
- `backend/app/api/dependencies.py`
- `backend/app/services/vikingdb_client.py`
- `backend/app/services/vikingdb_knowledge_router.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_service.py`
- `backend/app/services/search_service_components.py`
- `backend/scripts/probe_vikingdb_knowledge_search.py`
- `backend/tests/test_search_index.py`
- `backend/.env.example`
- `.env.docker.example`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 火山仍是可重建派生索引，不保存完整 API Key，不作为素材事实源。
- 本轮不批量写入公共话术、不写入证明点、不改变 6 大体系、16 个卖点、人工 accepted 关系或图片发布事实。

### 测试结果

- `PYTHONPYCACHEPREFIX=/tmp/piancton-pycache PYTHONPATH=. ./.venv/bin/python -m py_compile ...` 通过。
- `PYTHONPATH=. ./.venv/bin/python -m ruff check ...` 通过。
- 真实火山知识检索探针 8/8 无错误；常见卖点 Top1 正确，延迟约 160～514ms。
- 真实 SearchService 冒烟：
  - `拍题精学之后还能从一道题带到一类题，不只是告诉答案` 返回 `AI拍题精学 + 举一反三`，结果数 2。
  - `动画课程` 返回 `动画精讲`，结果数 1。
- 新增路由单测覆盖最终最多 3 个卖点，以及 `考前复习` 优先归 `专项培优`。
- 本地 pytest 入口仍受当前 `.venv` Python 3.9 与既有 `str | None` 注解不兼容影响，未完成完整执行。
- 当前 Docker backend 容器不是最新源码镜像，未将容器 pytest 作为本轮有效回归结论。

### 遗留问题

- `VIKINGDB_KNOWLEDGE_ROUTER_ENABLED` 默认仍为关闭，正式打开前需要用户确认和一轮业务端真实搜索观察。
- 当前火山知识路由只负责卖点识别；证明点、公共话术向量补充和图片级向量召回仍保留为后续阶段。
- 多卖点排序目前按火山向量分数和本地 accepted 结果共同约束，后续可增加更完整的人工评测集。

### 下一步

1. 在本地 `.env` 或部署环境中打开 `VIKINGDB_KNOWLEDGE_ROUTER_ENABLED=true` 做真实业务端试用。
2. 保持 `VIKINGDB_SKILL_BACKUP_ENABLED=true` 观察一段时间；如果想测试纯火山路径，再临时关闭旧 Skill 备份。
3. 基于真实搜索失败样例，按体系逐批精修公共话术，再决定是否把公共话术作为补充文档写入火山。

---

## 2026-09-02：项目火山向量检索测试模式

### 本轮目标

将项目真实搜索入口切到火山 VikingDB 知识路由测试模式，不再只在火山控制台里测向量召回。目标是：用户输入话术后，项目先用火山判断命中的卖点，再回本地数据库按人工 accepted 关系返回该卖点下的图库。

### 完成内容

- 本地/compose 运行配置开启 `VIKINGDB_KNOWLEDGE_ROUTER_ENABLED=true`。
- 本轮测试关闭 `VIKINGDB_SKILL_BACKUP_ENABLED=false`，避免旧 Skill/模型链路兜底影响测试判断。
- 保持火山候选召回 5 个、项目最终最多保留 3 个卖点。
- 后端搜索候选上限提升到 150，前端搜索请求默认提升到 50 条，方便观察命中卖点下的图库覆盖。
- VikingDB 路由成功时跳过第四层候选图片复核和第五层动态推荐理由，直接返回本地 accepted 素材，避免模型后处理拖慢或污染向量路由测试。
- 重建并重启 Docker backend/web，使配置和前端搜索条数生效。

### 修改文件

- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_orchestrator_helpers.py`
- `client/src/features/images/hooks/useGlobalImageSearch.ts`
- `backend/.env.vikingdb.local`
- `.env`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 未改动火山数据集结构。
- 未写入公共话术或证明点。
- 本地数据库仍是图片、素材状态、人工 accepted 关系和权限的事实源。

### 测试结果

- 后端 `py_compile` 通过。
- 后端 Ruff 通过。
- 前端 `npm run typecheck` 通过。
- 前端 `npm run lint` 通过。
- `git diff --check` 通过。
- Docker backend/web 重建成功，后端 ready。
- 容器内项目 SearchService 真实搜索：
  - `考前复习`：约 2.1s，命中 `专项培优`，返回 28 张。
  - `口前复习`：约 1.6s，命中 `专项培优`，返回 27 张。
  - `洋葱拍题精学可以让孩子解决一道题到一类问题`：约 2.6s，命中 `AI拍题精学 + 举一反三`，返回 23 张。
  - `动画课程`：约 1.6s，命中 `动画精讲`，返回 1 张。

### 遗留问题

- 这是测试模式，不代表生产默认关闭旧 Skill 备份。
- 当前页面最多请求 50 条；如果某个卖点 accepted 图库超过 50，仍需分页或后续扩展接口才能看全量。
- 若后续测试发现火山把相邻卖点混淆，应优先补知识文档边界或轻量业务校准，再考虑补大量公共话术。

### 下一步

1. 用户在项目真实页面用同事/业务话术继续测试。
2. 收集错误样例：搜了什么、期望卖点、实际卖点、返回图片是否缺。
3. 对错误样例按体系精修火山知识文档，再小批量重建火山知识索引。

---

## 2026-09-02：火山主链路与上传话术退休

### 本轮目标

按用户最新决策，把当前项目测试口径从旧四层/五层 Skill 路由收口到火山 VikingDB 卖点向量路由：自由搜索先由火山判断卖点，再返回该卖点下本地 accepted 图库。上传流程不再生成或提交素材话术，只维护图片所属主要卖点。

### 完成内容

- 纯火山测试模式下，搜索自由输入不再使用本地公共话术召回作为候选来源。
- 纯火山测试模式下，旧 Meilisearch 全文召回和旧 Embedding 旁路会跳过，避免混入非卖点路由结果。
- 火山未产出可信卖点且 Skill 备份关闭时，不再回落到本地弱理解或旧公共话术。
- 搜索服务在纯火山模式下不初始化 API Center 调度模型，减少 API 链路干扰。
- 上传弹窗改为只选择主要表达卖点，隐藏证明点和证据表达点。
- 上传弹窗移除上传前素材话术生成、继承公共话术展示和手动话术输入区。
- 前端上传不再提交 `expectedSearchWords`，并显式关闭 `autoAnalyze`。
- 后端上传接口忽略旧 `expectedSearchWords` 字段，不再自动排队图片分析。
- AI 图片分析保存时不再写入 pending 的 AI 素材搜索话术；手动图片分析接口仍保留。

### 修改文件

- `backend/app/api/dependencies.py`
- `backend/app/api/v1/images.py`
- `backend/app/services/asset_relation_service.py`
- `backend/app/services/search_external_branches.py`
- `backend/app/services/search_orchestrator.py`
- `backend/app/services/search_query_context_resolver.py`
- `client/src/api/image.ts`
- `client/src/features/assets/BusinessClassificationFields.tsx`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无数据库 schema 迁移。
- 未物理删除历史公共话术或素材话术数据，避免测试阶段不可逆丢失。
- 当前运行口径只让火山卖点路由和本地人工 accepted 关系决定图库召回。

### 测试结果

- 后端 `py_compile` 通过。
- 后端 Ruff 通过。
- 前端 `npm run typecheck` 通过。
- 前端 `npm run lint` 通过。
- `git diff --check` 通过。
- Docker backend/web 重建成功，后端 ready。
- Docker 后端专项测试 `tests/test_search_index.py tests/test_asset_relation_service.py tests/test_phase5_endpoints.py`：`30 passed`。
- 容器内项目 SearchService 真实搜索确认自由输入链路只走火山知识路由，`local_concepts`、`database`、`meilisearch`、`embedding`、`candidate_review` 和 `result_recommendation_reason` 均为 skipped：
  - `考前复习`：命中 `同步考点体系 > 专项培优`，返回 28 张。
  - `口前复习`：命中 `同步考点体系 > 专项培优`，返回 27 张。
  - `洋葱拍题精学可以让孩子解决一道题到一类问题`：命中 `同步自学体系 > AI拍题精学` 和 `同步考点体系 > 举一反三`，返回 23 张。
  - `动画课程`：命中 `同步校内体系 > 动画精讲`，返回 1 张。

### 遗留问题

- 旧话术管理页面和接口仍作为历史管理能力存在，但不参与当前上传主流程和纯火山自由搜索链路。
- 如果后续确认彻底退休素材话术，需要单独做数据迁移、接口下线和页面删除，不应和本轮测试收口混在一起。

### 下一步

1. 重建并验证本地服务。
2. 用项目页面搜索多条业务话术，确认诊断里只有火山卖点路由参与。
3. 继续收集火山误判样例，优先优化业务知识文档而不是堆公共话术。

---

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

## 2026-09-03：旧话术管理链路退役

### 本轮目标

- 按用户确认，把旧四层/五层 Skill 检索和公共/素材话术管理入口从当前产品形态中移除。
- 保留业务卖点作为图片归属标签和火山向量路由落点。
- 保留历史话术数据表和只读响应，避免为测试收口引入删库迁移风险。

### 完成内容

- API Center 移除 `asset_search_phrase_generation` 默认任务槽、任务枚举、健康检查标签和 Skill 映射。
- 删除上传前素材话术生成服务、Skill 目录、前端生成组件和 `/api/ai/asset-search-phrases` 路由。
- 删除业务概念公共话术新增/编辑接口和前端公共话术管理页面。
- 删除素材组话术新增、审核、删除接口和素材详情话术审核面板。
- 上传服务不再把 `expectedSearchWords` 转成素材组搜索话术；上传弹窗只保留图片、渠道、风格/场景和主要表达卖点。
- 图片分析保存仍可生成业务概念建议，但不再把 AI 素材话术写入 pending 列表。
- OpenAPI 前端类型已用重建后的 backend 容器重新生成。

### 修改文件

- `backend/app/ai/contracts.py`
- `backend/app/ai/normalizer.py`
- `backend/app/ai/skill_loader.py`
- `backend/app/api/dependencies.py`
- `backend/app/api/v1/ai.py`
- `backend/app/api/v1/assets.py`
- `backend/app/api/v1/business_concepts.py`
- `backend/app/repositories/asset_repository.py`
- `backend/app/schemas/ai.py`
- `backend/app/schemas/api_center.py`
- `backend/app/schemas/asset.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/api_center_service.py`
- `backend/app/services/asset_relation_service.py`
- `backend/app/services/business_concept_service.py`
- `backend/app/services/image_service.py`
- `client/src/api/asset.ts`
- `client/src/api/businessConcept.ts`
- `client/src/api/image.ts`
- `client/src/features/assets/useAssetActions.ts`
- `client/src/features/assets/useBusinessConceptActions.ts`
- `client/src/pages/AdminApiCenter/AdminApiCenter.tsx`
- `client/src/pages/AdminConcepts/AdminConcepts.tsx`
- `client/src/pages/AdminConcepts/ConceptList.tsx`
- `client/src/pages/ImageDetail/asset/AssetWorkspacePanel.tsx`
- `client/src/pages/ImageHome/UploadDialog.tsx`
- `client/src/types/api.generated.ts`
- `client/src/types/api.ts`
- `client/src/types/openapi.d.ts`
- `skills/INDEX.md`
- `skills/operate-model-providers/RULES.md`

### 数据迁移

- 无数据库 schema 迁移。
- 未物理删除 `concept_search_phrases` 或 `asset_search_phrases` 历史表。
- 当前新写入路径不再新增公共话术、素材话术或上传前 AI 话术。

### 测试结果

- Docker backend/web 重建成功。
- 前端 `npm run typecheck` 通过。
- 前端 `npm run lint` 通过。
- 后端 py_compile 通过。
- 后端 Ruff 通过。
- 后端重点测试：`119 passed, 4 skipped`。

### 遗留问题

- 历史话术只读字段、旧索引兼容读取和运营统计中的“缺搜索话术”指标仍保留；后续若确认彻底删除历史表，需要单独做迁移和统计口径调整。
- 当前项目搜索仍处于火山向量主链路测试模式，生产默认策略需在更多真实样例后再确认。

### 下一步

1. 在页面上继续用真实同事话术测试火山卖点命中。
2. 收集错例后优先优化火山知识文档，而不是恢复旧公共话术堆叠。
3. 如果新链路稳定，再单独整理搜索运营页中与“话术缺失”相关的历史指标。

## 2026-09-03：结果说明收口

### 本轮目标

- 搜索结果不再为每张图片展示动态推荐理由，避免一个卖点下十几二十张图时页面过重、解释重复、速度被旧链路拖慢。
- 保留“为什么命中这个卖点/渠道”的统一说明，让操作工先理解本次搜索的卖点判断，再从该卖点图库里选图。

### 完成内容

- 搜索结果顶部新增统一说明：命中卖点、渠道/版位收窄、当前返回组数。
- 搜索结果卡片底部从 `推荐点 + 推荐这张...` 改为只显示 `卖点：xxx`。
- 保持 VikingDB clean 数据集不变，仍只保留 22 条体系/卖点知识文档，不写入图片标题、主图、竖版延展等污染数据。
- 保持 VikingDB 路由成功后跳过候选复核和动态推荐理由。
- 已重建 Docker web，让浏览器页面使用最新前端产物。

### 修改文件

- `client/src/pages/ImageHome/SemanticSearchResult/index.tsx`
- `client/src/pages/ImageHome/SemanticSearchResult/ScoredImageCard.tsx`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 测试结果

- `npm test -- channelIntent searchResultFilters searchConceptPresentation --run`：3 files / 30 tests passed。
- `npm run typecheck`：通过。
- `npm run build -- --logLevel error`：通过。
- `git diff --check`：通过。
- Docker web 重建成功。
- 浏览器实测：
  - `运营长图里用的拍题精学`：命中 `AI拍题精学`，按 `手机端` 收窄，10 组。
  - `运营长图大模块里用的拍题精学`：命中 `AI拍题精学`，按 `手机端大图` 收窄，6 组。
  - `运营长图小模块里用的拍题精学`：命中 `AI拍题精学`，按 `手机端小图` 收窄，6 组。
  - `拍题精学功能图`：命中 `AI拍题精学`，按手机端和非场景功能图收窄，3 组。
  - 上述页面均未出现 `推荐这张...` 逐图理由。

### 下一步

- 继续用真实话术看“渠道/场景/卖点”三层是否够用；如真实素材的渠道名不统一，再做渠道别名迁移或映射。

## 2026-09-03：渠道与版位默认收窄

### 本轮目标

- 让搜索在卖点之外继续理解“用在哪个渠道/版位”。
- 支持用户说 `PPT 用的拍题精学`、`手机端小图用的拍题精学`、`运营长图里用的图`。
- 未提及渠道时默认只返手机端大图/小图，避免业务端被 PPT、官网、品牌手册素材冲散。

### 完成内容

- 渠道意图仍与火山卖点路由并行，不写入 VikingDB，不污染 22 条体系/卖点知识文档。
- `运营长图`、`活动长图`、`长图` 归为手机端使用语境。
- `大模块`、`主模块`、`重点模块` 偏 `手机端大图`。
- `小模块`、`次级模块`、`辅助模块` 偏 `手机端小图`。
- 只说运营长图但没说模块大小时，同时保留 `手机端大图`、`手机端小图`。
- 用户没有提及渠道时，前端结果默认只保留 `手机端大图`、`手机端小图`。
- `场景图`、`真实使用`、`使用场景` 会在默认手机渠道内自动收窄到场景图。
- `功能图`、`功能截图`、`功能卡片`、`界面截图` 会在默认手机渠道内自动收窄到非场景功能图。
- 用户手动选择场景筛选时，以手动选择覆盖自动识别。
- 场景图/功能图继续是图片功能维度，不进入火山卖点路由。
- 已重建 Docker web，让浏览器页面使用最新前端产物。

### 修改文件

- `client/src/pages/ImageHome/channelIntent.ts`
- `client/src/pages/ImageHome/searchResultFilters.ts`
- `client/src/pages/ImageHome/channelIntent.test.ts`
- `client/src/pages/ImageHome/searchResultFilters.test.ts`
- `skills/understand-image-channel-intent/SKILL.md`
- `skills/understand-image-channel-intent/references/channel-taxonomy.md`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 测试结果

- `npm test -- channelIntent searchResultFilters --run`：2 files / 19 tests passed。
- `npm run typecheck`：通过。
- `npm run build`：通过。

### 下一步

- 页面上重点测试三类话术：明确渠道、运营长图模块、完全不提渠道。
- 如果真实素材存在旧渠道名，需要再决定是否做一次渠道名迁移或兼容别名。

## 2026-09-03：火山短词入口校准

### 本轮目标

- 解释并修复页面搜索单字 `拍` 返回 0，但火山控制台可命中 `AI拍题精学` 的差异。
- 保持火山 clean 数据集不受泛词污染。

### 完成内容

- 确认当前容器已成功切到 `piancton_search_knowledge_clean` / `piancton_search_knowledge_idx`，并且 `VIKINGDB_KNOWLEDGE_ROUTER_ENABLED=true`、`VIKINGDB_SKILL_BACKUP_ENABLED=false`。
- 真实火山探针显示 `拍` Top1 为 `selling_point:photo_guided_learning`，但分数约 `0.256`，低于项目可信阈值 `0.34`。
- 保持全局阈值不变，新增精确短业务入口白名单：完整输入 `拍` 直接映射到 `photo_guided_learning`。
- 未放开 `图`、`素材`、`标题` 等泛词，避免低分随机卖点进入项目搜索。
- 已重建 Docker backend/web，让页面使用最新代码。

### 修改文件

- `backend/app/services/vikingdb_knowledge_router.py`
- `backend/tests/test_search_index.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 测试结果

- 容器内 `python -m compileall app/services/vikingdb_knowledge_router.py` 通过。
- 容器内 `python -m pytest tests/test_search_index.py -q`：`18 passed`。
- 真实项目 SearchService：
  - `拍`：返回 26 张，理解为 `AI拍题精学`。
  - `拍题`：返回 26 张，理解为 `AI拍题精学`。
  - `复习`：返回 26 张，理解为 `极速预习复习`。
  - `图`、`素材`、`标题`：仍返回 0。

### 下一步

- 页面刷新后继续用真实短词和口语词测试火山卖点命中。
- 后续每发现一个短入口错例，优先判断是否是明确业务入口；只有稳定、唯一、不会泛化污染的短词才进白名单。

## 2026-09-03：火山数据集去污染

### 本轮目标

- 修正火山数据集里出现图片标题、主图/新版主图、竖版延展等派生表达的问题。
- 让 VikingDB 当前只保存六大体系和 16 个卖点知识文档。
- 保持本地图片、素材组、渠道和人工 accepted 卖点关系不变。

### 完成内容

- `VikingDBVectorIndexSync.upsert_images` 改为退休兼容空操作，不再生成或写入图片文档。
- `VikingDBVectorIndexSync.best_effort_upsert_image` 保留调用兼容，但只记录 debug，不再上传图片语义。
- 删除 `image_to_vikingdb_document`，源头移除图片向量文档生成器。
- 删除旧的 `backend/scripts/rebuild_vikingdb_index.py`，避免再次批量写入图片文档。
- 新增 `backend/scripts/reset_vikingdb_knowledge_index.py`，用于清空 VikingDB collection 后只写回 22 条 `system`/`selling_point` 知识文档。
- `VikingDBClient` 新增 `delete_all_documents()`，仅用于可重建的派生向量数据集维护。
- `VikingDBKnowledgeRouter` 和探针脚本请求层改为只过滤 `doc_type=selling_point`，旧图片文档即使暂留 collection 也不会进入当前项目搜索候选。
- 已重新提交 22 条知识文档到当前 VikingDB collection。
- 项目运行配置已切到新建 clean 数据集 `piancton_search_knowledge_clean` 和索引 `piancton_search_knowledge_idx`。
- `backend/app/core/config.py`、`backend/.env.example`、`.env.docker.example` 默认值改为 clean collection/index。
- `backend/.env.vikingdb.local` 加入 `.gitignore`，避免真实 VikingDB Key 被误提交。

### 修改文件

- `backend/app/services/vikingdb_client.py`
- `backend/app/services/vikingdb_vector_index.py`
- `backend/scripts/reset_vikingdb_knowledge_index.py`
- `backend/scripts/rebuild_vikingdb_index.py`
- `backend/tests/test_search_index.py`
- `docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`
- `docs/IMAGE_SEARCH_REBUILD_PROJECT_LOG.md`

### 数据迁移

- 无本地数据库 schema 迁移。
- 本地素材、图片、渠道、素材组、业务概念和人工 accepted 关系不变。
- 当前火山 VikingDB collection 需要执行一次重置：删除旧派生文档后只重建 22 条体系/卖点知识文档。

### 测试结果

- Docker backend 重建成功。
- 容器内 Python 编译通过。
- 本机 Ruff 通过。
- 容器内 `tests/test_search_index.py`：`18 passed`。
- 真实 VikingDB 探针 4 条均无错误，Top 命中均为 `selling_point:*`，无 `image:*`：`拍题精学之后还能从一道题带到一类题`、`题型突破`、`口前复习`、`动画课程`。
- 真实项目 Router 验证：`拍题精学之后还能从一道题带到一类题` 返回 `AI拍题精学 + 举一反三`，`题型突破` 返回 `专项培优`，`口前复习` 返回 `专项培优`，`动画课程` 返回 `动画精讲`。

### 遗留问题

- D256 的图片文档设计保留为历史决策记录，不再代表当前实现。
- 如果未来要做“图片级向量检索”，必须新建独立 collection，不能混入当前卖点知识路由 collection。
- 旧 `piancton_search_assets_test` 数据集内的脏数据尚未在火山后台物理清空，但当前项目已切到 clean 数据集，不再使用旧数据集。

### 下一步

1. 重建 backend 容器。
2. 执行火山 collection 重置脚本。
3. 用探针确认当前检索只返回 `system`/`selling_point` 文档。
# 2026-09-07 D275 公司服务器部署准备

按用户确认采用空库部署：不带图片、旧账号和 API 配置，初始化 6 个体系和 16 个卖点，管理员单独创建；复用现有 VikingDB。补齐 Compose 环境变量和重启策略，Docker 排除本地 `.env.*`。镜像构建、空库迁移和种子幂等通过；前端 54 测试及构建通过，后端 364 passed / 21 failed / 4 skipped，Ruff 与 Pyright 遗留问题未清零。无新增迁移，无本地业务数据写入。服务器尚待拉取、启动、创建管理员及生产验收，详见 `COMPANY_SERVER_DEPLOYMENT_2026-09-07.md`。
