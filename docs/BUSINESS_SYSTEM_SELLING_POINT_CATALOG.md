# 六大体系、核心卖点与证明点工作目录

版本：1.5
更新时间：2026-07-21
状态：六大体系 Skill 已接入项目实际搜索；共 16 个核心卖点，全部复用项目现有稳定 code；六个体系均已按“论断 + 搜索语言 + 证据样例 + 边界 + 当前素材线索”完成证明点第一版结构化，已确认素材缺口已登记为版本化第三层门槛
事实来源：`docs/source/six-systems/` 中的业务原版截图
Skill 入口：`skills/understand-image-search-intent/SKILL.md`
总纲：`docs/IMAGE_SEARCH_REBUILD_MASTER_PLAN.md`

> 本文档只保存治理原则、进度和文件入口。每个体系的业务原文、核心卖点、证明点、搜索语言、边界与用例分别保存在 Skill 的六个独立知识文件中，避免一份巨型文档和聊天上下文成为隐性事实来源。

---

## 1. 固定知识层级

```text
稳定体系
  └─ 核心卖点
       └─ 证明点
            └─ 已审核素材关系
```

- 第一层是六大稳定体系。
- 第二层是业务原版明确提出的核心卖点，不因搜索优化随意新增或替换。
- 第三层是产品功能、教研逻辑、案例、数据、证书或效果证据；证明点可以跨卖点、跨体系复用。
- 证明点是可复用的“凭什么成立”论断；具体课例、数字、学校和案例是其下可增删的证据样例，不单独升格为证明点。结构化证明点使用 `pp_` 前缀草拟 code，属于治理层标识，未经业务确认和新决策不进入数据库运行时。
- 已审核图片通过 `expresses`、`supports`、`visual_related`、`excludes` 等关系连接卖点或证明点，不恢复固定二级标签树。
- 原版截图中的绿色文字是未来待制作、待补充或待寻找的图片建议，不作为已有卖点、证明事实、搜索标签或现有素材。

## 2. 允许扩展与禁止事项

可扩展：管理简称、标准表达、别名、痛点、结果、场景、口语、相邻边界，以及单卖点、多卖点、探索、待消歧和否定查询用例。

不可扩展：未经业务确认的新核心卖点，以及未经核验的产品能力、数字、学校、媒体、证书、奖项和效果结论。搜索语言不能反向篡改业务原文。

## 3. 六个体系知识文件

| 顺序 | 体系 | 状态 | 独立知识文件 | 原始资料 |
|---:|---|---|---|---|
| 1 | 同步校内体系 | 第一版已落盘；证明点已结构化 | `skills/understand-image-search-intent/references/sync-school.md` | `docs/source/six-systems/01-sync-school.png` |
| 2 | 同步考点体系 | 证明点已结构化 | `skills/understand-image-search-intent/references/sync-exam.md` | `docs/source/six-systems/02-sync-exam-a.png`、`03-sync-exam-b.png` |
| 3 | 同步培养体系 | 证明点已结构化 | `skills/understand-image-search-intent/references/sync-cultivation.md` | `docs/source/six-systems/04-sync-cultivation.png` |
| 4 | 同步规划体系 | 证明点已结构化 | `skills/understand-image-search-intent/references/sync-planning.md` | `docs/source/six-systems/05-sync-planning.png` |
| 5 | 同步自学体系 | 证明点已结构化 | `skills/understand-image-search-intent/references/sync-self-study.md` | `docs/source/six-systems/06-sync-self-study.png` |
| 6 | 同步伴学体系 | 证明点已结构化 | `skills/understand-image-search-intent/references/sync-companion.md` | `docs/source/six-systems/07-sync-companion.png` |

结构化输出、查询状态和从意图到图片的路由规则见 `skills/understand-image-search-intent/references/output-contract.md`。

页面精简目录与 Skill 完整业务名称的 16 项稳定映射见 `skills/understand-image-search-intent/references/selling-point-map.json`。精简名称只用于展示，稳定 code 是唯一连接键；自动化测试会阻止漏项、重复项、错主体系或名称漂移。

跨体系共享入口、相邻边界和统一判别维度见 `skills/understand-image-search-intent/references/cross-system-calibration.md`。当前按对象、动作、时间尺度、目的和执行主体五个维度判别，不能再用“拍题、反馈、规划、省心、理解原理”等共享词直接硬路由。

第一版合计 16 个核心卖点：同步校内 3 个、同步考点 3 个、同步培养 3 个、同步规划 1 个、同步自学 4 个、同步伴学 2 个。它们与项目当前 16 个稳定业务概念逐一对应，没有为了整理体系新增重复概念。

## 4. Skill 与当前项目的关系

同一目录支持两种使用方式：

1. **跨任务复用**：`SKILL.md` 声明何时调用、阅读哪些体系文件和如何输出判断。
2. **当前项目运行时**：`backend/app/ai/skill_loader.py` 加载 `RULES.md`，并只抽取跨体系校准文件与六个体系文件中经过审核的“运行时意图摘要”；数据库当前启用卖点、名称、定义及采纳/拒绝话术仍是项目运行时权威。

项目的完整路径是：

```text
业务输入话术
  → 本地高置信意图识别
  → 歧义/未识别时调用模型 Skill
  → 归一化为一个或多个当前启用卖点
  → 按人工确认的 accepted expresses/supports 关系匹配图片
  → 没有可信关联图则返回空结果
```

这保证了 Skill 提高语言理解和复用能力，但不代替数据库状态管理，也不绕过业务负责人确认的图片关系。

## 5. 下一步入口

首轮跨体系校准、三方对比和实际搜索接入均已完成，第 5 批新增 28 条自动化意图评测，累计 103 条。对比与实施结果见 `docs/BUSINESS_INTENT_DATABASE_COMPARISON_2026-07-17.md`，机器动作与回滚键见 `docs/BUSINESS_INTENT_DATABASE_SYNC_PROPOSAL_2026-07-17.json`。当前 95 条带目标业务卖点的用例全部保留正确候选；下一步用真实业务话术和已审核图片关系验证“意图 → 卖点 → 证明点 → 图片”完整链路，并建立证明材料的来源、时间、口径与核验状态。
