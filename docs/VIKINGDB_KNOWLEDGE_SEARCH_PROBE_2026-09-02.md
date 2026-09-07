# 火山体系/卖点知识检索探针

运行时间：2026-09-02T12:37:30+08:00

## 汇总

| 话术 | 耗时 | 错误 | Top 命中 |
|---|---:|---|---|
| 洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做 | 514ms | — | selling_point:photo_guided_learning、selling_point:transfer_practice、selling_point:ai_tutor_qa、selling_point:universal_method、selling_point:animation_explanation |
| 我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做 | 190ms | — | selling_point:transfer_practice、selling_point:universal_method、system:sync_exam、selling_point:focused_excellence、selling_point:photo_guided_learning |
| 拍题精学之后还能从一道题带到一类题，不只是告诉答案 | 197ms | — | selling_point:photo_guided_learning、selling_point:transfer_practice、selling_point:ai_tutor_qa、selling_point:universal_method、selling_point:ai_error_book |
| 动画课程 | 163ms | — | selling_point:animation_explanation、system:sync_school、selling_point:school_sync、selling_point:universal_method、selling_point:ai_learning_plan |
| 孩子刚看完这节课，想马上做几道题看看是不是真的会了 | 198ms | — | selling_point:instant_quiz、selling_point:transfer_practice、selling_point:photo_guided_learning、selling_point:learning_report、selling_point:animation_explanation |
| 我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材 | 177ms | — | selling_point:learning_report、selling_point:instant_quiz、selling_point:ai_learning_plan、selling_point:human_teacher_supervision、selling_point:ai_tutor_qa |
| 想找训练拔高、题型突破、压轴题专项提升的图 | 300ms | — | selling_point:focused_excellence、system:sync_exam、selling_point:new_curriculum_prediction、selling_point:stage_transition、selling_point:transfer_practice |
| 孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课 | 198ms | — | selling_point:rapid_preview_review、selling_point:school_sync、selling_point:photo_guided_learning、selling_point:instant_quiz、selling_point:ai_error_book |

## 原始响应摘录

### Q1

- 话术：洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做
- 耗时：514.27ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384886900000000000000000000ffff0a005f0341f8cc", "result": {"data": [{"id": "selling_point:photo_guided_learning", "fields": {"channel": "all", "concept_code": "photo_guided_learning", "doc_id": "selling_point:photo_guided_learning", "doc_type": "selling_point", "search_text": "卖点：AI拍题精学\n卖点 code：photo_guided_learning\n所属体系：同步自学体系(sync_self_study)\nSkill 名称：AI 拍题精学\n一句话判定：如果用户重点在“拍当前不会的一道题，AI 识别后一步步引导理解思路”，判 AI 拍题精学；如果只是泛问知识点或学习疑问，判 AI 私教答疑。\n背后意思：这个卖点背后解决的是拍照搜题容易变成抄答案的问题：孩子遇到当前不会的题时，AI 不是直接给答案，而是识别题目、拆知识点、追问思路，引导孩子真正学会。\n边界逻辑：它判断的是一道当前题的拍题学习流程，不判断所有 AI 问答。泛问知识点归 AI 私教答疑；拍错题为了长期归档归 AI 错题本；拍课本笔记做短时梳理归极速预习复习；讲完题后继续同类变式可同时触发举一反三。\n本体定义：孩子遇到当前不会的题时拍题进入学习流程，AI 识别题目和知识点，通过追问、提示和分步引导帮助孩子理解思路，而不是直接给答案。\n核心对象：当前不会的题；拍题；题目；知识点；解题步骤；苏格拉底式提问\n主动作：拍照讲题；识别题目；分步引导；追问思路；不直接给答案；关联讲解\n用户目的：解决当前题；理解解题思路；避免抄答案；把搜答案变成学会\n正向信号：AI 拍题精学；拍题讲解；拍一道不会题；不要直接答案；一步步点拨；启发式提问；还原思考过程；从答案到思路\n排除边界：拍课本/笔记做课前课后短时梳理归极速预习复习；拍错题为了长期归档归 AI 错题本；泛问知识点、概念或学习疑问且不以一道题解题为对象时归 AI 私教答疑；讲完当前题后继续同类/变式训练可同时触发举一反三；独立动画讲透知识点归动画精讲\n易混卖点：ai_tutor_qa；rapid_preview_review；ai_error_book；transfer_practice；animation_explanation\n判定规则：拍题或启发式引导是主入口；...
```

### Q2

- 话术：我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做
- 耗时：189.83ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384907000000000000000000000ffff0a005bef26199b", "result": {"data": [{"id": "selling_point:transfer_practice", "fields": {"channel": "all", "concept_code": "transfer_practice", "doc_id": "selling_point:transfer_practice", "doc_type": "selling_point", "search_text": "卖点：举一反三\n卖点 code：transfer_practice\n所属体系：同步考点体系(sync_exam)\nSkill 名称：理解原理，举一反三\n一句话判定：如果用户重点在“这道题会了以后，同类题、相似题、变式题也会”，判举一反三；同一道题多种解法判万能解法。\n背后意思：这个卖点背后解决的是孩子只会眼前这道题、考试换个问法就不会的问题：从当前题或当前原理抽出规律，再迁移到同类、相似、变式题，形成一题到一类的能力。\n边界逻辑：它判断的是从一道题走向一类题的迁移，不是同一道题内部换方法。多种方法解同一道题是万能解法；当前题拍照分步讲清楚但没有同类迁移是 AI 拍题精学；个人错题长期复练是 AI 错题本。\n本体定义：先理解题目或知识背后的原理，再通过同类题、相似题、变式题迁移，做到一道题带一类题。\n核心对象：一道题；当前题；例题；同类题；相似题；变式题；出题原理\n主动作：讲完后再练；换数字/条件/问法；迁移训练；理解原理；练一类题\n用户目的：避免只会这道题；换题也会；掌握一类题思路\n正向信号：举一反三；一道题会一类题；解决一道题到一类问题；换题也会；变式题训练；讲完题推相似题\n排除边界：同一道题用不同方法归万能解法；个人历史错题后的同类复练归 AI 错题本；只有当前题拍照讲解且没有迁移训练时归 AI 拍题精学；理解原理单独出现时需要结合迁移目的判断\n易混卖点：photo_guided_learning；universal_method；ai_error_book；focused_excellence\n判定规则：必须看到从当前题/原理走向同类、相似、变式或一类题的迁移目的；不要把同题多解判成举一反三。\n使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。", "source_id": "transfer_practice", "status":...
```

### Q3

- 话术：拍题精学之后还能从一道题带到一类题，不只是告诉答案
- 耗时：197.09ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384922900000000000000000000ffff0a005629ad748a", "result": {"data": [{"id": "selling_point:photo_guided_learning", "fields": {"channel": "all", "concept_code": "photo_guided_learning", "doc_id": "selling_point:photo_guided_learning", "doc_type": "selling_point", "search_text": "卖点：AI拍题精学\n卖点 code：photo_guided_learning\n所属体系：同步自学体系(sync_self_study)\nSkill 名称：AI 拍题精学\n一句话判定：如果用户重点在“拍当前不会的一道题，AI 识别后一步步引导理解思路”，判 AI 拍题精学；如果只是泛问知识点或学习疑问，判 AI 私教答疑。\n背后意思：这个卖点背后解决的是拍照搜题容易变成抄答案的问题：孩子遇到当前不会的题时，AI 不是直接给答案，而是识别题目、拆知识点、追问思路，引导孩子真正学会。\n边界逻辑：它判断的是一道当前题的拍题学习流程，不判断所有 AI 问答。泛问知识点归 AI 私教答疑；拍错题为了长期归档归 AI 错题本；拍课本笔记做短时梳理归极速预习复习；讲完题后继续同类变式可同时触发举一反三。\n本体定义：孩子遇到当前不会的题时拍题进入学习流程，AI 识别题目和知识点，通过追问、提示和分步引导帮助孩子理解思路，而不是直接给答案。\n核心对象：当前不会的题；拍题；题目；知识点；解题步骤；苏格拉底式提问\n主动作：拍照讲题；识别题目；分步引导；追问思路；不直接给答案；关联讲解\n用户目的：解决当前题；理解解题思路；避免抄答案；把搜答案变成学会\n正向信号：AI 拍题精学；拍题讲解；拍一道不会题；不要直接答案；一步步点拨；启发式提问；还原思考过程；从答案到思路\n排除边界：拍课本/笔记做课前课后短时梳理归极速预习复习；拍错题为了长期归档归 AI 错题本；泛问知识点、概念或学习疑问且不以一道题解题为对象时归 AI 私教答疑；讲完当前题后继续同类/变式训练可同时触发举一反三；独立动画讲透知识点归动画精讲\n易混卖点：ai_tutor_qa；rapid_preview_review；ai_error_book；transfer_practice；animation_explanation\n判定规则：拍题或启发式引导是主入口；...
```

### Q4

- 话术：动画课程
- 耗时：162.76ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384943300000000000000000000ffff0a005b63376bea", "result": {"data": [{"id": "selling_point:animation_explanation", "fields": {"channel": "all", "concept_code": "animation_explanation", "doc_id": "selling_point:animation_explanation", "doc_type": "selling_point", "search_text": "卖点：动画精讲\n卖点 code：animation_explanation\n所属体系：同步校内体系(sync_school)\nSkill 名称：动画讲透知识点\n一句话判定：如果用户重点在“用动画/故事/可视化把抽象知识点讲懂”，判动画精讲；只说动画课程这类大概念时应保留探索，不要独占全部结果。\n背后意思：这个卖点背后解决的是抽象知识难懂、课堂讲得快或讲得枯燥的问题：把看不见的过程、难想象的原理和孩子听不进去的概念，转成可视化、故事化、短时可理解的动画课程。\n边界逻辑：它的核心不是“画面里有动画”，而是“动画服务于讲懂知识”。只说动画课程是宽概念，应保持探索；拍一道题分步引导是 AI 拍题精学；考前重难点突破是专项培优；纯视觉风格或动效不算业务卖点。\n本体定义：用动画、故事化和可视化方式拆解抽象知识点，补位课堂听不懂、讲得快、讲得枯燥的问题。\n核心对象：抽象知识点；学科原理；课堂没听懂的内容；难理解的概念；动画课程\n主动作：动画讲解；可视化演示；故事化拆解；几分钟讲透；把看不见的过程讲清楚\n用户目的：让难点变直观；补位课堂；让孩子真正听懂知识点\n正向信号：动画精讲；动画课程；抽象知识可视化；老师讲太快没听懂；几分钟讲明白一个知识点；把枯燥变秒懂\n排除边界：拍不会的题并分步引导优先归 AI 拍题精学；考前重难点/压轴题归专项培优；短时间不能单独触发，必须和动画/知识点/讲透组合；纯视觉动效或动画风格不是本卖点；只说动画课程、动画课等概念词但没有讲懂抽象知识或课堂补位证据时，作为探索入口而非强单一卖点\n易混卖点：photo_guided_learning；focused_excellence；rapid_preview_review；school_sync\n判定规则：核心是动画或可视化讲透知识点；如果动画只是拍题流程里的后续兜底，不作为独立动画精讲卖点。\n使用方式：第二层卖点路由。命中一个卖点就回本...
```

### Q5

- 话术：孩子刚看完这节课，想马上做几道题看看是不是真的会了
- 耗时：198.07ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384959500000000000000000000ffff0a005e9cb0ae59", "result": {"data": [{"id": "selling_point:instant_quiz", "fields": {"channel": "all", "concept_code": "instant_quiz", "doc_id": "selling_point:instant_quiz", "doc_type": "selling_point", "search_text": "卖点：课后小测\n卖点 code：instant_quiz\n所属体系：同步校内体系(sync_school)\nSkill 名称：学练测闭环\n一句话判定：如果用户重点在“刚学完这一课/这个知识点，马上练几题确认会不会”，判课后小测；如果是日周汇总或长期错题，不判课后小测。\n背后意思：这个卖点背后解决的是孩子说听懂了但不一定真的会：每节课或知识点学完后立刻练几题，用当场反馈判断有没有掌握，避免学习停在看课或听懂的错觉。\n边界逻辑：它判断的是当前课后的即时练测闭环，不判断长期复盘。按日周汇总正确率是学情报告；把错题长期保存以后复练是 AI 错题本；围绕考点集中刷题是专项培优。\n本体定义：课程或知识点学完后马上衔接练习、测试和掌握反馈，形成学、练、测闭环。\n核心对象：当前课；本节知识点；看完课后的内容；随堂练习；本节掌握度\n主动作：马上测；立即练；做几道题；检测掌握；反馈会不会\n用户目的：确认是否听懂；及时发现漏洞；让学习效果当场可见\n正向信号：课后小测；学完即练；看完课马上做题；本节课掌握度；孩子说听懂了想看看会不会\n排除边界：按日/周给家长汇总正确率和薄弱点归学情报告；长期个人错题归 AI 错题本；专项考点刷题归专项培优；只说反馈/正确率但没有当前课练测动作时不能硬命中\n易混卖点：learning_report；ai_error_book；focused_excellence\n判定规则：必须看到学完当前内容后的立即练测或确认掌握；周期报告和长期错题不属于本卖点。\n使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。", "source_id": "instant_quiz", "status": "active"}, "score": 0.48568618297576904, "ann_score": 0.48568618297576904}, {"id": "selling_...
```

### Q6

- 话术：我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材
- 耗时：177.44ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832384978800000000000000000000ffff0a005dfe82d849", "result": {"data": [{"id": "selling_point:learning_report", "fields": {"channel": "all", "concept_code": "learning_report", "doc_id": "selling_point:learning_report", "doc_type": "selling_point", "search_text": "卖点：学情报告反馈\n卖点 code：learning_report\n所属体系：同步伴学体系(sync_companion)\nSkill 名称：学情报告反馈\n一句话判定：如果用户重点在“家长查看过去一段时间学了什么、效果如何、哪里薄弱”，判学情报告反馈；接下来怎么学归 AI 定制学习方案。\n背后意思：这个卖点背后解决的是家长不知道孩子到底学没学、学得怎么样的问题：通过日周报告把学习内容、时长、正确率、薄弱点和行为线索反馈给家长，降低黑盒焦虑。\n边界逻辑：它判断的是过去一段时间的结果和过程反馈，不判断未来计划，也不判断当前课即时检测。接下来每天学什么归 AI 定制学习方案；当前一课马上测归课后小测；真人提醒执行归真人老师督学。\n本体定义：按日或周汇总孩子已经学了什么、学了多久、正确率、薄弱点和行为线索，给家长查看学习结果和过程透明度。\n核心对象：学习报告；学习周报；家长端；学习内容；学习时长；正确率；薄弱点；行为记录\n主动作：汇总；统计；推送；查看；反馈；透明化\n用户目的：让家长知道过去学得怎样；减少黑盒焦虑；不用一直盯屏幕也能看结果\n正向信号：学情报告；学习周报；家长看学习结果；学了什么学了多久；正确率和薄弱点；微信报告；有没有快进或开小差\n排除边界：学完当前一课马上做题确认掌握归课后小测；个人错题长期归档复练归 AI 错题本；接下来每天学什么归 AI 定制学习方案；真人提醒/管理过程归真人老师督学\n易混卖点：instant_quiz；ai_error_book；ai_learning_plan；human_teacher_supervision\n判定规则：它回答过去一段时间学得怎么样；如果用户说的是当前一节课马上测，不能归报告。\n使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。", "source_id": "learning_report", "s...
```

### Q7

- 话术：想找训练拔高、题型突破、压轴题专项提升的图
- 耗时：299.72ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832385006500000000000000000000ffff0a005b6316b01e", "result": {"data": [{"id": "selling_point:focused_excellence", "fields": {"channel": "all", "concept_code": "focused_excellence", "doc_id": "selling_point:focused_excellence", "doc_type": "selling_point", "search_text": "卖点：专项培优\n卖点 code：focused_excellence\n所属体系：同步考点体系(sync_exam)\nSkill 名称：分学科重难点专项培优\n一句话判定：如果用户重点在“某类题型、重难点、压轴题、考前重点或群体高频错题的定向突破/拔高”，判专项培优；个人历史错题和一题到一类题不要抢到这里。\n背后意思：这个卖点背后解决的是有限时间内抓关键涨分点：孩子不是泛泛学习，而是要针对薄弱题型、重难点、压轴题、考前重点或高频易错点集中突破，完成拔高或补弱。\n边界逻辑：它判断的是一类考试/训练对象的定向突破，不判断个人错题资产，也不判断解题迁移。这个学生自己的历史错题归 AI 错题本；一道题讲完后练同类题归举一反三；按个人情况安排每日学习归 AI 定制学习方案。\n本体定义：围绕学科重难点、薄弱题型、压轴题、考前阶段和群体高频易错题做定向突破与拔高训练。\n核心对象：薄弱题型；专项模块；重难点；压轴题；考前重点；群体高频错题；高阶拔高\n主动作：专项训练；集中突破；考前划重点；拔高冲分；练高频易错题\n用户目的：把有限时间用在关键得分项；补薄弱项；冲高分或解决考试失分点\n正向信号：题型突破；专项突破；训练拔高；重难点培优；压轴题专项；考前突击；全网高频错题\n排除边界：这个学生自己的历史错题归 AI 错题本；当前题讲完后的同类/变式迁移归举一反三；根据个人情况排每天任务归 AI 定制学习方案；只说提分或薄弱但没有对象和训练动作时不能硬命中\n易混卖点：transfer_practice；ai_error_book；ai_learning_plan；new_curriculum_prediction\n判定规则：看对象是否是考试题型、重难点、压轴或群体易错；看动作是否是专项突破、拔高或考前冲刺。\n使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。", ...
```

### Q8

- 话术：孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课
- 耗时：198.36ms
- 错误：—

```json
{"code": "Success", "message": "The API call was executed successfully.", "request_id": "02178832385029900000000000000000000ffff0a005da86a614d", "result": {"data": [{"id": "selling_point:rapid_preview_review", "fields": {"channel": "all", "concept_code": "rapid_preview_review", "doc_id": "selling_point:rapid_preview_review", "doc_type": "selling_point", "search_text": "卖点：极速预习复习\n卖点 code：rapid_preview_review\n所属体系：同步自学体系(sync_self_study)\nSkill 名称：极速预习复习\n一句话判定：如果用户重点在“课前/课后用几分钟快速预习或回顾当前内容”，判极速预习复习；如果重点是和学校章节进度严格对齐，判同步校内。\n背后意思：这个卖点背后解决的是孩子课前没概念、课后没及时回顾的问题：用很短时间拍课本、笔记或当天内容，快速建立认知、扫盲区、带着问题进课堂或写作业。\n边界逻辑：它判断的是课前课后短时梳理，不判断校内体系对齐。明确强调学校章节、教材版本和进度对应时归同步校内；考试节点冲刺归专项培优；当前不会题解题归 AI 拍题精学；长期错题复盘归 AI 错题本。\n本体定义：课前拍课本快速预习新课，课后拍笔记或学习内容快速回顾当天重点和盲区。\n核心对象：课本；笔记；课前内容；课后内容；当天知识；明天课程\n主动作：快速预习；极速复习；几分钟过一遍；拍课本；拍笔记；短时梳理\n用户目的：上课前建立认知；提高听课效率；写作业前快速回顾；扫清当天盲区\n正向信号：极速预习；快速复习；课前拍课本；课后拍笔记；五分钟预习；当天知识快速回顾；带着问题进课堂\n排除边界：考试节点前冲刺复习归专项培优；当前不会题解题归 AI 拍题精学；个人历史错题长期复盘归 AI 错题本；明确强调教材版本/学校章节/校内进度对齐时归同步校内；只说快速复习但没有对象和场景时待消歧\n易混卖点：school_sync；focused_excellence；photo_guided_learning；ai_error_book\n判定规则：必须看到课前/课后/当天/明天课程等时间场景，以及短时间梳理目的；拍照本身不能决定卖点。\n使用方式：第二层卖点路由。命中一个卖点就回本地数据库取该卖点 accepted 素材；命中多个卖点就按用户原话重点顺序分别取图。", "sour...
```
