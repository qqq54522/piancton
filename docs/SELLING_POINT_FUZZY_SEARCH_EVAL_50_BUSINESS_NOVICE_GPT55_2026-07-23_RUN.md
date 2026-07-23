# 50 条业务小白模糊搜索测评结果（GPT-5.5）

运行时间：2026-07-23T23:56:43+08:00

## 汇总

- Provider：primary
- 模型：gpt-5.5
- 说明：按用户授权外发 50 条测评话术及当前搜索理解上下文；运行日志中出现过 primary 调用失败后由 Provider 包装器尝试后备的提示，因此本文以“当前 GPT-5.5 主判断链路实测结果”保存，不作为纯模型离线基准。
- 完成：50/50
- 模型调用成功：46/50
- 明确单卖点含预期：39/48
- 查询状态匹配：40/50
- 探索型用例：2 条，需人工看是否合理保留候选

## 逐条对照表

| # | 测试话术 | 预期状态 | 预期卖点 | 实际查询状态 | GPT-5.5 实际识别卖点 | 实际 code | 自动检查 | 耗时 | 错误 | 人工判断 |
|---:|---|---|---|---|---|---|---|---:|---|---|
| 1 | 想找一张能说明课外也跟学校一样走的图 | 明确单卖点 | 同步校内 | business_intent_search | 同步校内体系 > 同步校内 | school_sync | 含预期 | 25604ms |  |  |
| 2 | 课本版本别乱，最好能对上 | 明确单卖点 | 同步校内 | business_intent_search | 同步校内体系 > 同步校内 | school_sync | 含预期 | 17139ms |  |  |
| 3 | 学校讲到哪儿，它也讲到哪儿 | 明确单卖点 | 同步校内 | business_intent_search | 同步校内体系 > 同步校内 | school_sync | 含预期 | 16340ms |  |  |
| 4 | 一张把难知识变成动画的 | 明确单卖点 | 动画精讲 | visual_scene_search | — | — | 不含预期 | 9649ms |  |  |
| 5 | 抽象的东西，孩子能看见那种 | 明确单卖点 | 动画精讲 | visual_scene_search | — | — | 不含预期 | 9386ms |  |  |
| 6 | 几分钟把一个知识点讲明白 | 明确单卖点 | 动画精讲 | business_intent_search | 同步校内体系 > 动画精讲 | animation_explanation | 含预期 | 27437ms |  |  |
| 7 | 学完马上做几题的图 | 明确单卖点 | 课后小测 | — | — | — | 不含预期 | 28492ms | model_response_invalid: 模型返回内容不符合项目结构要求 |  |
| 8 | 看完课能不能立刻测一下 | 明确单卖点 | 课后小测 | business_intent_search | 同步校内体系 > 课后小测 | instant_quiz | 含预期 | 26511ms |  |  |
| 9 | 学完就知道会没会 | 明确单卖点 | 课后小测 | business_intent_search | 同步校内体系 > 课后小测 | instant_quiz | 含预期 | 22290ms |  |  |
| 10 | 新课标新题型那种图 | 明确单卖点 | 新课标新考法预测 | business_intent_search | 同步考点体系 > 新课标新考法预测 | new_curriculum_prediction | 含预期 | 31025ms |  |  |
| 11 | 现在考试变活了，想体现这个 | 明确单卖点 | 新课标新考法预测 | business_intent_search | 同步考点体系 > 新课标新考法预测 | new_curriculum_prediction | 含预期 | 33403ms |  |  |
| 12 | 跨学科情境题这类 | 明确单卖点 | 新课标新考法预测 | business_intent_search | 同步考点体系 > 新课标新考法预测 | new_curriculum_prediction | 含预期 | 21892ms |  |  |
| 13 | 把容易丢分的点拎出来练 | 明确单卖点 | 专项培优 | business_intent_search | 同步考点体系 > 专项培优 | focused_excellence | 含预期 | 39432ms |  |  |
| 14 | 大家都容易错的题，集中练 | 明确单卖点 | 专项培优 | business_intent_search | 同步考点体系 > 专项培优 | focused_excellence | 含预期 | 32725ms |  |  |
| 15 | 压轴题专门突破一下 | 明确单卖点 | 专项培优 | business_intent_search | 同步考点体系 > 专项培优 | focused_excellence | 含预期 | 22086ms |  |  |
| 16 | 一道题后面带几道差不多的 | 明确单卖点 | 举一反三 | business_intent_search | 同步考点体系 > 举一反三 | transfer_practice | 含预期 | 34313ms |  |  |
| 17 | 换个数字孩子也能做 | 明确单卖点 | 举一反三 | business_intent_search | 同步考点体系 > 举一反三 | transfer_practice | 含预期 | 31642ms |  |  |
| 18 | 讲完原题再练同类题 | 明确单卖点 | 举一反三 | ambiguous_business_intent_search | 同步自学体系 > AI拍题精学、同步自学体系 > AI错题本 | photo_guided_learning、ai_error_book | 不含预期 | 58443ms |  |  |
| 19 | 出题人做课程这种背书 | 明确单卖点 | 专家规划 | business_intent_search | 同步考点体系 > 新课标新考法预测 | new_curriculum_prediction | 不含预期 | 32194ms |  |  |
| 20 | 教材编者把关的课 | 明确单卖点 | 专家规划 | no_reliable_intent_search | — | — | 不含预期 | 29123ms |  |  |
| 21 | 有专家提前规划长期路线 | 明确单卖点 | 专家规划 | business_intent_search | 同步培养体系 > 专家规划 | expert_planning | 含预期 | 25440ms |  |  |
| 22 | 小升初过渡别断层 | 明确单卖点 | 学段衔接 | business_intent_search | 同步培养体系 > 学段衔接 | stage_transition | 含预期 | 24390ms |  |  |
| 23 | 初升高别一开学就掉队 | 明确单卖点 | 学段衔接 | business_intent_search | 同步培养体系 > 学段衔接 | stage_transition | 含预期 | 19015ms |  |  |
| 24 | 小学到高中一套走 | 明确单卖点 | 学段衔接 | business_intent_search | 同步培养体系 > 学段衔接 | stage_transition | 含预期 | 23447ms |  |  |
| 25 | 同一道题有不同解法 | 明确单卖点 | 万能解法 | no_reliable_intent_search | — | — | 不含预期 | 30579ms |  |  |
| 26 | 别死背公式，讲方法 | 明确单卖点 | 万能解法 | business_intent_search | 同步培养体系 > 万能解法 | universal_method | 含预期 | 36906ms |  |  |
| 27 | 一题多解培养思维 | 明确单卖点 | 万能解法 | business_intent_search | 同步培养体系 > 万能解法 | universal_method | 含预期 | 21286ms |  |  |
| 28 | 按孩子成绩排计划 | 明确单卖点 | AI定制学习方案 | business_intent_search | 同步规划体系 > AI定制学习方案 | ai_learning_plan | 含预期 | 35313ms |  |  |
| 29 | 每天学什么，系统给安排 | 明确单卖点 | AI定制学习方案 | business_intent_search | 同步规划体系 > AI定制学习方案 | ai_learning_plan | 含预期 | 36032ms |  |  |
| 30 | 家长不用想先学啥后学啥 | 明确单卖点 | AI定制学习方案 | business_intent_search | 同步规划体系 > AI定制学习方案 | ai_learning_plan | 含预期 | 23373ms |  |  |
| 31 | 孩子卡住能问 AI | 明确单卖点 | AI私教答疑 | business_intent_search | 同步自学体系 > AI私教答疑 | ai_tutor_qa | 含预期 | 29896ms |  |  |
| 32 | 晚上没人辅导，有个 AI 老师 | 明确单卖点 | AI私教答疑 | business_intent_search | 同步自学体系 > AI私教答疑 | ai_tutor_qa | 含预期 | 20713ms |  |  |
| 33 | 打字语音都能问那种 | 明确单卖点 | AI私教答疑 | business_intent_search | 同步自学体系 > AI私教答疑 | ai_tutor_qa | 含预期 | 21041ms |  |  |
| 34 | 拍不会的题，别直接给答案 | 明确单卖点 | AI拍题精学 | business_intent_search | 同步自学体系 > AI拍题精学 | photo_guided_learning | 含预期 | 25071ms |  |  |
| 35 | 拍题后一步步提示孩子 | 明确单卖点 | AI拍题精学 | business_intent_search | 同步自学体系 > AI拍题精学 | photo_guided_learning | 含预期 | 37714ms |  |  |
| 36 | AI 先问思路再讲题 | 明确单卖点 | AI拍题精学 | business_intent_search | 同步自学体系 > AI拍题精学 | photo_guided_learning | 含预期 | 26571ms |  |  |
| 37 | 课前拍课本，五分钟预习 | 明确单卖点 | 极速预习复习 | business_intent_search | 同步自学体系 > 极速预习复习 | rapid_preview_review | 含预期 | 20002ms |  |  |
| 38 | 课后拍笔记，快速复习 | 明确单卖点 | 极速预习复习 | business_intent_search | 同步自学体系 > 极速预习复习 | rapid_preview_review | 含预期 | 21018ms |  |  |
| 39 | 写作业前快点过今天重点 | 明确单卖点 | 极速预习复习 | — | — | — | 不含预期 | 28054ms | model_response_invalid: 模型返回内容不符合项目结构要求 |  |
| 40 | 纸质错题拍进错题本 | 明确单卖点 | AI错题本 | — | — | — | 不含预期 | 22229ms | model_response_invalid: 模型返回内容不符合项目结构要求 |  |
| 41 | 自己错过的题以后再练 | 明确单卖点 | AI错题本 | business_intent_search | 同步自学体系 > AI错题本 | ai_error_book | 含预期 | 27184ms |  |  |
| 42 | 错题后推几道同类题 | 明确单卖点 | AI错题本 | business_intent_search | 同步自学体系 > AI错题本 | ai_error_book | 含预期 | 36114ms |  |  |
| 43 | 真人老师盯着学 | 明确单卖点 | 真人老师督学 | business_intent_search | 同步伴学体系 > 真人老师督学 | human_teacher_supervision | 含预期 | 22907ms |  |  |
| 44 | 不想天天催，有老师管 | 明确单卖点 | 真人老师督学 | business_intent_search | 同步伴学体系 > 真人老师督学 | human_teacher_supervision | 含预期 | 23367ms |  |  |
| 45 | 老师分析问题再做计划 | 明确单卖点 | 真人老师督学 | business_intent_search | 同步伴学体系 > 真人老师督学 | human_teacher_supervision | 含预期 | 22200ms |  |  |
| 46 | 家长看周报，知道学了多久 | 明确单卖点 | 学情报告反馈 | business_intent_search | 同步伴学体系 > 学情报告反馈 | learning_report | 含预期 | 22208ms |  |  |
| 47 | 一张能看学习结果的报告 | 明确单卖点 | 学情报告反馈 | business_intent_search | 同步伴学体系 > 学情报告反馈 | learning_report | 含预期 | 31749ms |  |  |
| 48 | 看正确率和薄弱点 | 明确单卖点 | 学情报告反馈 | ambiguous_business_intent_search | 同步伴学体系 > 学情报告反馈、同步校内体系 > 课后小测 | learning_report、instant_quiz | 含预期 | 53275ms |  |  |
| 49 | 想找一张体现学习效果看得见的图 | 探索型 | 课后小测 / 学情报告反馈 | — | — | — | 探索待人工看 | 16513ms | model_response_invalid: 模型返回内容不符合项目结构要求 |  |
| 50 | 拍一下马上讲讲 | 探索型 | AI拍题精学 / 极速预习复习 | exploratory_business_intent_search | 同步自学体系 > AI拍题精学、同步自学体系 > 极速预习复习 | photo_guided_learning、rapid_preview_review | 探索待人工看 | 21354ms |  |  |

## 使用说明

- “明确单卖点含预期”只看模型实际识别卖点是否包含预期 code，不替代业务人工审批。
- 探索型话术本来就不应该强行猜唯一卖点；人工重点看候选是否合理、是否过度扩散。
- 本报告只评 GPT-5.5 的卖点理解，不评最终图片排序质量。
