# 输出协议与判定规则

## 第一层：体系路由

在线查询先只输出 `route_type`、`candidate_systems` 和 `excluded_systems`。这一层不读取卖点目录、不输出卖点；明确需求通常只有一个主体系，相邻歧义最多增加一个候选。完整协议见 `../SYSTEM_ROUTER_RULES.md`。

第二层完整读取候选体系文件、完整 `RULES.md` 和候选体系内当前启用卖点，再生成下面的卖点理解结果；候选超过一个时才完整读取跨体系校准文件。这里的按需读取只缩小体系范围，不压缩已命中体系的知识。纯画面或无可靠体系在第一层直接结束，不触发第二层。

## 推荐结构化输出

```json
{
  "original_query": "string",
  "normalized_query": "string",
  "search_intent": "string",
  "query_type": "business_intent_search | multi_business_intent_search | exploratory_business_intent_search | ambiguous_business_intent_search | visual_scene_search | no_reliable_intent_search",
  "matched_systems": [
    {"code": "string", "name": "string", "reason": "string"}
  ],
  "matched_business_concepts": [
    {"concept": "stable_code", "relation": "direct|related|fallback", "reason": "string", "weight": 0.7}
  ],
  "matched_proof_points": [
    {"code": "pp_existing_code", "concept_code": "parent_selling_point_code", "name": "string", "reason": "string", "weight": 0.7, "evidence_terms": ["从证明点搜索语言中原样选择的具体线索"]}
  ],
  "matched_evidence_points": [
    {"code": "ep_existing_code", "proof_point_code": "pp_existing_code", "concept_code": "parent_selling_point_code", "name": "string", "reason": "string", "weight": 0.7}
  ],
  "excluded_concepts": ["stable_code"],
  "expanded_terms": [
    {"term": "string", "relation": "exact|strong|medium|weak", "reason": "string", "weight": 0.7}
  ],
  "needs_clarification": false,
  "clarifying_question": null,
  "search_strategy": "string"
}
```

项目后端现有模型协议不要求 `matched_systems`、`needs_clarification` 和 `clarifying_question`；可通过卖点与体系关系推导。复用 Skill 进行人工分析时建议保留这些字段，方便解释。

`matched_proof_points` 是可选精细理解：只有查询明确提出功能流程、方法、案例、数据、证书或具体效果证据时才输出，并且每条证明点的 `concept_code` 必须已经由 `matched_business_concepts` 命中。泛搜体系或卖点时返回空数组；证明点只引用候选体系知识文件中已有的 `pp_` code，不自造、不入库为固定标签。
每条命中的证明点必须在 `evidence_terms` 中从该证明点已有“搜索语言”原样选择 1～3 条最贴近查询细节的线索。该字段用于证明点内素材筛选，不能填写父卖点名称、用户原句或该证明点下全部词条；模型返回的非目录词会在规范化阶段丢弃。

`matched_evidence_points` 是证明点下的可选最细粒度。它只能引用候选体系“证据表达点目录”中的稳定 `ep_` code；父证明点和父卖点必须同时命中。它可以通过语义近义表达命中，不要求用户逐字复述原脑图绿色制作文字。该层是作图依据和搜索表达，不自动证明产品事实或素材存在。

## 查询状态

| 状态 | `query_type` | 判断标准 |
|---|---|---|
| 明确单卖点 | `business_intent_search` | 有一个卖点得到独立且充分的话术证据 |
| 明确多卖点 | `multi_business_intent_search` | 原话同时提出多个需求，每个卖点各有独立证据 |
| 探索型 | `exploratory_business_intent_search` | 只输入体系名或共享入口词，候选存在但用户尚未选择 |
| 待消歧 | `ambiguous_business_intent_search` | 存在相邻候选，但原话不足以区分 |
| 纯画面 | `visual_scene_search` | 只有颜色、构图、人物、场景、尺寸等视觉条件 |
| 无可靠卖点 | `no_reliable_intent_search` | 只有“提分、学习好”等宽泛诉求，或没有可信业务证据 |

## 多卖点与否定

- “既要、还要、同时、并且”等连接词可帮助识别多需求，但每个卖点仍需有自己的语义证据。
- 同一个模糊词同时关联多个卖点时属于探索或待消歧，不是真多卖点。
- 显式否定的卖点进入 `excluded_concepts`，不进入正向概念。
- 如果同一卖点在另一子句又被明确正向要求，保留上下文并说明冲突，不做机械否定。

## 关系强度

- `direct` / 1.0：原话直接表达核心能力、典型痛点或明确结果场景。
- `related` / 0.7：相邻卖点有合理联系，但缺少独立强证据。
- `fallback` / 0.35：只能作为弱候选或消歧备选，不能据此硬路由图片。

## 从意图到图片

1. 先根据当前启用业务概念归一化卖点 code。
2. 明确单卖点、明确多卖点和探索型进入可信卖点主通道。
3. 只召回与任一查询卖点存在 accepted `expresses`/`supports` 关系的素材。
4. 第三层在可信关系集合内先识别用户的主对象和主动作/产品入口，再核对目的结果，最后可选输出证明点，并用查询原话与证明点语义共同匹配素材。
5. 探索型和真多卖点结果先保证每个候选卖点至少有一张最直接素材，再追加同卖点的证明图，避免一个卖点的多张细节图挤掉另一个候选卖点。
6. 只表达特定方法或证明细节的素材属于条件素材；用户没有明确提出该方法时不得仅凭通用结果词进入结果。条件触发规则保存在可版本化搜索策略中，不写死到总编排器。
7. 标题和已采纳的素材独有话术只在可信关系集合内帮助选图；AI 待审核关系和待审核话术不得作为第三层准入事实。
8. 可信卖点没有关联素材时返回空结果；待消歧、纯画面和无可靠卖点才允许全局弱兜底。
9. 已采纳素材独有话术是第三层的主筛选依据，标题、语义总结、V3 画面事实和场景只作辅助。明确命中证明点时，同卖点素材还必须与该证明点的素材线索、搜索语言或查询原话达到门槛，否则退出；没有对应素材时返回空。某卖点已有 `expresses` 直接素材时，只有 `supports` 的证明图必须命中 accepted 图片话术，或被查询明确点名其标题/画面证据才可进入；该卖点没有 `expresses` 时允许 accepted `supports` 作为可信保底。

第三层不新增一次生成式图片裁判。它使用人工 accepted 卖点关系划定候选，再由可配置条件门槛、本地排序和至多一次 Reranker 完成选图。这样可以分别表达：

- **必须覆盖**：直接展示主动作/入口且代表当前候选卖点的素材；
- **可以补充**：展示结果、案例或通用证明的素材；
- **条件命中**：只有用户明确提出某个方法、证书、数据或具体证明时才能出现的素材；
- **排除**：与查询显式否定冲突，或只有条件细节而缺少对应查询证据的素材。
