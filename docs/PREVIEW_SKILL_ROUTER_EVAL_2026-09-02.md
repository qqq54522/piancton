# 业务文档版 Skill 路由小样本测试

运行时间：2026-09-02T03:19:14+00:00
模式：`api_center_external`
知识文档：`docs/VIKINGDB_KNOWLEDGE_PREVIEW_2026-09-02.md`

## 汇总

- 用例数：12
- 体系命中：12/12
- 卖点命中：12/12
- 错误数：0

## 明细

| ID | 话术 | 预期卖点 | 实际卖点 | 状态 | 耗时 | 结论 |
|---|---|---|---|---|---:|---|
| DOC001 | 洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做 | photo_guided_learning | photo_guided_learning | precise | 13677ms | OK |
| DOC002 | 我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做 | transfer_practice | transfer_practice | precise | 11101ms | OK |
| DOC003 | 拍题精学之后还能从一道题带到一类题，不只是告诉答案 | photo_guided_learning、transfer_practice | photo_guided_learning、transfer_practice | multi | 39489ms | OK |
| DOC004 | 动画课程 | animation_explanation | animation_explanation | ambiguous_or_exploratory | 16708ms | OK |
| DOC005 | 孩子刚看完这节课，想马上做几道题看看是不是真的会了 | instant_quiz | instant_quiz | precise | 27443ms | OK |
| DOC006 | 我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材 | learning_report | learning_report | precise | 10572ms | OK |
| DOC007 | 想找训练拔高、题型突破、压轴题专项提升的图 | focused_excellence | focused_excellence | precise | 15092ms | OK |
| DOC008 | 孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课 | rapid_preview_review | rapid_preview_review | precise | 13149ms | OK |
| DOC009 | 希望课程内容能和学校教材版本、章节进度对得上 | school_sync | school_sync | precise | 8236ms | OK |
| DOC010 | 我想体现这套课是命题专家和教材编者一起规划出来的 | expert_planning | expert_planning | precise | 14648ms | OK |
| DOC011 | 小升初之前怕知识断层，想找能表达平稳衔接的素材 | stage_transition | stage_transition | precise | 12228ms | OK |
| DOC012 | 同一道题可以用好几种方法拆开，不是死记一个公式 | universal_method | universal_method | precise | 14195ms | OK |

## 模型解释

### DOC001

- 话术：洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做
- 预期体系：sync_self_study
- 实际体系：sync_self_study
- 预期卖点：photo_guided_learning
- 实际卖点：photo_guided_learning
- 判断状态：precise
- 模型解释：用户话术直接指向AI拍题精学卖点，属于同步自学体系
- 错误：—

### DOC002

- 话术：我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做
- 预期体系：sync_exam
- 实际体系：sync_exam
- 预期卖点：transfer_practice
- 实际卖点：transfer_practice
- 判断状态：precise
- 模型解释：用户明确要表达一道题会了之后同类题、变条件题也会的迁移能力，精确命中举一反三
- 错误：—

### DOC003

- 话术：拍题精学之后还能从一道题带到一类题，不只是告诉答案
- 预期体系：sync_self_study, sync_exam
- 实际体系：sync_self_study, sync_exam
- 预期卖点：photo_guided_learning, transfer_practice
- 实际卖点：photo_guided_learning, transfer_practice
- 判断状态：multi
- 模型解释：用户以拍题精学为入口，同时强调一道题迁移到一类题，两个卖点均明确命中，按原话顺序取图。
- 错误：—

### DOC004

- 话术：动画课程
- 预期体系：sync_school
- 实际体系：sync_school
- 预期卖点：animation_explanation
- 实际卖点：animation_explanation
- 判断状态：ambiguous_or_exploratory
- 模型解释：用户只说了“动画课程”这一宽泛概念，指向动画精讲但缺少讲透知识点或课堂补位的具体证据，按探索处理、confidence 不虚高
- 错误：—

### DOC005

- 话术：孩子刚看完这节课，想马上做几道题看看是不是真的会了
- 预期体系：sync_school
- 实际体系：sync_school
- 预期卖点：instant_quiz
- 实际卖点：instant_quiz
- 判断状态：precise
- 模型解释：用户意图明确指向课后即时练习检测掌握情况
- 错误：—

### DOC006

- 话术：我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材
- 预期体系：sync_companion
- 实际体系：sync_companion
- 预期卖点：learning_report
- 实际卖点：learning_report
- 判断状态：precise
- 模型解释：用户话术明确对应学情报告反馈卖点
- 错误：—

### DOC007

- 话术：想找训练拔高、题型突破、压轴题专项提升的图
- 预期体系：sync_exam
- 实际体系：sync_exam
- 预期卖点：focused_excellence
- 实际卖点：focused_excellence
- 判断状态：precise
- 模型解释：用户明确寻找专项培优相关图像，命中同步考点体系下的专项培优卖点。
- 错误：—

### DOC008

- 话术：孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课
- 预期体系：sync_self_study
- 实际体系：sync_self_study
- 预期卖点：rapid_preview_review
- 实际卖点：rapid_preview_review
- 判断状态：precise
- 模型解释：用户重点是课前几分钟快速预习当天内容，应命中极速预习复习卖点。
- 错误：—

### DOC009

- 话术：希望课程内容能和学校教材版本、章节进度对得上
- 预期体系：sync_school
- 实际体系：sync_school
- 预期卖点：school_sync
- 实际卖点：school_sync
- 判断状态：precise
- 模型解释：用户明确要求课程内容与学校教材版本和章节进度对得上，精准命中同步校内卖点。
- 错误：—

### DOC010

- 话术：我想体现这套课是命题专家和教材编者一起规划出来的
- 预期体系：sync_cultivation
- 实际体系：sync_cultivation
- 预期卖点：expert_planning
- 实际卖点：expert_planning
- 判断状态：precise
- 模型解释：用户明确强调课程由命题专家和教材编者共同规划，命中专家规划卖点
- 错误：—

### DOC011

- 话术：小升初之前怕知识断层，想找能表达平稳衔接的素材
- 预期体系：sync_cultivation
- 实际体系：sync_cultivation
- 预期卖点：stage_transition
- 实际卖点：stage_transition
- 判断状态：precise
- 模型解释：用户直接表达小升初知识断层和平稳衔接需求，明确命中同步培养体系下的学段衔接卖点。
- 错误：—

### DOC012

- 话术：同一道题可以用好几种方法拆开，不是死记一个公式
- 预期体系：sync_cultivation
- 实际体系：sync_cultivation
- 预期卖点：universal_method
- 实际卖点：universal_method
- 判断状态：precise
- 模型解释：强命中万能解法：同一道题多种方法拆开，反对死记公式。
- 错误：—
