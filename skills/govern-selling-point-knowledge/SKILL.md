---
name: govern-selling-point-knowledge
description: "治理卖点智库的六大体系、16个稳定核心卖点、公共搜索话术、证明材料、跨体系边界和数据库映射。用于新增或调整卖点知识、审核公共话术、处理Skill与数据库差异或固化业务校准；不得未经业务确认改变稳定code、主体系和人工素材关系。"
---

# 治理卖点知识

把六大体系和16个核心卖点视为冻结业务地图，把公共话术、证明材料和自然语言用例视为受控可变层。

## 使用顺序

1. 完整阅读项目 `AGENTS.md`、`docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`、`docs/DEVELOPMENT_GUARDRAILS.md` 和 `docs/BUSINESS_SYSTEM_SELLING_POINT_CATALOG.md`。
2. 完整阅读 `skills/understand-image-search-intent/SKILL.md`、`references/selling-point-map.json` 和 `references/public-phrase-governance.json`。
3. 如果涉及某个体系，完整阅读对应 `references/sync-*.md`；涉及多个候选体系时再完整阅读 `references/cross-system-calibration.md`。
4. 先做 Skill、静态种子与数据库 active 概念/话术的只读差异，再提出变更。
5. 区分稳定核心卖点、证明点、公共话术、图片独有话术和评测样例，不跨层写入。
6. 变更业务边界时新增总纲决策，不覆盖历史；更新映射、治理文件、相关体系文件和回归用例。
7. 数据库同步必须可回滚，先 dry-run；不得批量覆盖人工名称、定义、审核状态或素材关系。

## 准入规则

- 稳定 code、主体系和16项一一映射只能在业务方明确确认后修改。
- 公共话术必须稳定、可复用、边界唯一；共享短词只允许探索或待消歧。
- 小白长句优先进入理解样例和评测，不逐条复制到公共词库。
- 数据、学校、媒体、证书、专家身份和效果结论必须保留来源、时间、口径与核验状态。
- AI 可以提出候选，最终 accepted 状态必须来自有权限的人工审核。

## 验证

- 运行卖点映射、种子幂等、查询状态、文档一致性和103条搜索评测。
- 任何优化不得降低现有本地基线，也不得让 pending/rejected 关系或话术进入正式搜索。

