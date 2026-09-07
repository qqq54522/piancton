from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = ROOT / "datasets" / "model_finetune"

SOURCE_FILES = (
    DATASET_DIR / "piancton_six_system_selling_point_intent_v1_all_upload.jsonl",
    DATASET_DIR / "piancton_six_system_selling_point_intent_v2_boundary_all_upload.jsonl",
)
EVAL_CASES_FILE = ROOT / "taxonomy" / "search_eval_cases.json"

TRAIN_OUTPUT = DATASET_DIR / "piancton_six_system_selling_point_intent_v3_compact_train_upload.jsonl"
VALIDATION_OUTPUT = DATASET_DIR / "piancton_six_system_selling_point_intent_v3_compact_validation_upload.jsonl"
SMOKE_OUTPUT = DATASET_DIR / "piancton_six_system_selling_point_intent_v3_compact_smoke_eval.jsonl"

ALLOWED_QUERY_TYPES = {
    "business_intent_search",
    "multi_business_intent_search",
    "exploratory_business_intent_search",
    "ambiguous_business_intent_search",
    "visual_scene_search",
    "no_reliable_intent_search",
}

CODE_DEFINITIONS = {
    "school_sync": "教材版本、课程目录或章节进度与学校对应",
    "animation_explanation": "用动画、故事或可视化讲透抽象知识点",
    "instant_quiz": "学完当前内容立即练测并确认掌握",
    "new_curriculum_prediction": "新课标或新中高考带来的新题型、新情境和新考法",
    "focused_excellence": "重难点、压轴题、高频失分点或考前专项突破",
    "transfer_practice": "当前题讲完后继续练相似题、同类题或变式题，做到一题会一类",
    "expert_planning": "专家背书、专家介绍、命题专家或教材编者参与课程体系设计",
    "stage_transition": "小升初、初升高、全学段连续覆盖或知识断层过渡",
    "universal_method": "同一道题使用不同方法或路径求解，培养底层方法思维",
    "ai_learning_plan": "结合个人成绩、目标和时间生成学习路径或每日任务",
    "ai_tutor_qa": "学习中随时用文字、语音或图片与 AI 互动答疑",
    "photo_guided_learning": "拍当前不会的题，由 AI 分步引导推导而非只给答案",
    "rapid_preview_review": "课前课后拍课本或笔记做短时预习、复习和重点梳理",
    "ai_error_book": "把个人错题长期归档、分析并从错题出发复练",
    "human_teacher_supervision": "真人老师持续诊断、提醒、打卡、回访并跟进执行",
    "learning_report": "按日或周汇总学习内容、时长、行为、正确率和薄弱点",
}
ALLOWED_CODES = set(CODE_DEFINITIONS)

SYSTEM_PROMPT = """你是 Piancton 图片搜索卖点分类器。只判断用户话术命中的既有卖点，不回答问题，不解释产品，不创造 code。
允许的 query_type 只有：business_intent_search、multi_business_intent_search、exploratory_business_intent_search、ambiguous_business_intent_search、visual_scene_search、no_reliable_intent_search。
允许的卖点 code 及边界：
school_sync=教材版本、课程目录或章节进度与学校对应；
animation_explanation=用动画、故事或可视化讲透抽象知识点；
instant_quiz=学完当前内容立即练测并确认掌握；
new_curriculum_prediction=新课标或新中高考带来的新题型、新情境和新考法；
focused_excellence=重难点、压轴题、高频失分点或考前专项突破；
transfer_practice=当前题讲完后继续练相似题、同类题或变式题，做到一题会一类；
expert_planning=专家背书、专家介绍、命题专家或教材编者参与课程体系设计；
stage_transition=小升初、初升高、全学段连续覆盖或知识断层过渡；
universal_method=同一道题使用不同方法或路径求解，培养底层方法思维；
ai_learning_plan=结合个人成绩、目标和时间生成学习路径或每日任务；
ai_tutor_qa=学习中随时用文字、语音或图片与 AI 互动答疑；
photo_guided_learning=拍当前不会的题，由 AI 分步引导推导而非只给答案；
rapid_preview_review=课前课后拍课本或笔记做短时预习、复习和重点梳理；
ai_error_book=把个人错题长期归档、分析并从错题出发复练；
human_teacher_supervision=真人老师持续诊断、提醒、打卡、回访并跟进执行；
learning_report=按日或周汇总学习内容、时长、行为、正确率和薄弱点。
规则：每个正向卖点必须有独立语义证据；一句话有几个独立卖点就按原文顺序全部返回，最多4个。共享短词属于探索或待消歧，不是假多卖点。纯人物、颜色、版式、尺寸等需求为 visual_scene_search；只有提分、好用、省心等宽泛结果且无业务动作时为 no_reliable_intent_search。明确否定只进入 excluded_codes，不得同时正向命中。王玉龙老师、专家图片、专家背书等已确认业务入口归 expert_planning。
只输出单行合法 JSON，字段必须且只能是 query_type、matched_codes、excluded_codes。matched_codes 和 excluded_codes 只能使用上述16个 code。"""


def sample(query: str, query_type: str, codes: list[str], excluded: list[str] | None = None) -> dict[str, Any]:
    return {
        "query": query,
        "answer": {
            "query_type": query_type,
            "matched_codes": codes,
            "excluded_codes": excluded or [],
        },
    }


HARD_TRAIN_SAMPLES = [
    sample("王玉龙老师参与洋葱课程体系设计", "business_intent_search", ["expert_planning"]),
    sample("想找王玉龙老师的专家介绍素材", "business_intent_search", ["expert_planning"]),
    sample("王玉龙专家背书的课程规划", "business_intent_search", ["expert_planning"]),
    sample("找一张能体现专家团队背书的图", "business_intent_search", ["expert_planning"]),
    sample("教材编者和命题专家共同设计课程路径", "business_intent_search", ["expert_planning"]),
    sample("专家介绍页和教研团队合影", "business_intent_search", ["expert_planning"]),
    sample("名师讲了一节普通直播课", "ambiguous_business_intent_search", ["expert_planning"]),
    sample("不要专家背书，只要系统按孩子情况排每天任务", "business_intent_search", ["ai_learning_plan"], ["expert_planning"]),
    sample("拍下不会的题，AI分步讲完以后再推三道同类题", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("先拍题看思路，再练几道变式题做到一题会一类", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("拍题不是只看答案，讲懂后还要推荐相似题", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("AI拍题一步步引导，随后用同类题检查能不能迁移", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("孩子拍一道难题学会思路，再换一道同类型题练习", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("拍题精学加举一反三的素材", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("拍题后分步点拨，再自动推送变式训练", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("拍完当前错题先讲思路，再把错题存入个人错题本", "multi_business_intent_search", ["photo_guided_learning", "ai_error_book"]),
    sample("拍课本预习明天内容，遇到不会的地方随时问AI", "multi_business_intent_search", ["rapid_preview_review", "ai_tutor_qa"]),
    sample("学完动画课马上做几道小测题", "multi_business_intent_search", ["animation_explanation", "instant_quiz"]),
    sample("系统安排每天任务，真人老师再监督打卡", "multi_business_intent_search", ["ai_learning_plan", "human_teacher_supervision"]),
    sample("真人老师每天督学，每周给家长发学情报告", "multi_business_intent_search", ["human_teacher_supervision", "learning_report"]),
    sample("教材跟学校同步，学完一课马上测掌握情况", "multi_business_intent_search", ["school_sync", "instant_quiz"]),
    sample("专家设计小初高长期课程，并做好初升高衔接", "multi_business_intent_search", ["expert_planning", "stage_transition"]),
    sample("针对压轴题专项突破，练完再做同类变式题", "multi_business_intent_search", ["focused_excellence", "transfer_practice"]),
    sample("新中考新题型训练和考前薄弱题型专项突破", "multi_business_intent_search", ["new_curriculum_prediction", "focused_excellence"]),
    sample("只拍当前不会的题让AI分步提示", "business_intent_search", ["photo_guided_learning"]),
    sample("拍题后告诉孩子下一步怎么想，不要直接报答案", "business_intent_search", ["photo_guided_learning"]),
    sample("这道题讲完以后再给几道相似题", "business_intent_search", ["transfer_practice"]),
    sample("希望学会一道题以后同类型都会做", "business_intent_search", ["transfer_practice"]),
    sample("同一道数学题展示三种不同解法", "business_intent_search", ["universal_method"]),
    sample("培养不套公式也能分析陌生题的底层思维", "business_intent_search", ["universal_method"]),
    sample("换一道同类题继续练，不需要看同一道题的多种解法", "business_intent_search", ["transfer_practice"], ["universal_method"]),
    sample("同一道题看不同解法，不需要再推相似题", "business_intent_search", ["universal_method"], ["transfer_practice"]),
    sample("我想拍一下", "exploratory_business_intent_search", ["rapid_preview_review", "photo_guided_learning", "ai_error_book", "ai_tutor_qa"]),
    sample("专家", "business_intent_search", ["expert_planning"]),
    sample("想让家长省心", "exploratory_business_intent_search", ["ai_learning_plan", "human_teacher_supervision", "learning_report"]),
    sample("随时看到成果", "exploratory_business_intent_search", ["instant_quiz", "learning_report"]),
    sample("老师反馈孩子情况", "ambiguous_business_intent_search", ["human_teacher_supervision", "learning_report"]),
    sample("理解原理以后换题也会", "ambiguous_business_intent_search", ["transfer_practice", "universal_method"]),
    sample("给我一张红色科技感背景图", "visual_scene_search", []),
    sample("找一个老师坐在办公室里的横版人物图", "visual_scene_search", []),
    sample("要一张适合PPT封面的蓝色大图", "visual_scene_search", []),
    sample("找一张手机端竖版小图", "visual_scene_search", []),
    sample("想看往年真实成绩数据的图片", "visual_scene_search", []),
    sample("随便找张好看的图", "visual_scene_search", []),
    sample("这个产品挺好用的", "no_reliable_intent_search", []),
    sample("想让孩子成绩更好", "no_reliable_intent_search", []),
    sample("有没有能快速提分的", "no_reliable_intent_search", []),
    sample("给家长一个放心的感觉", "no_reliable_intent_search", []),
    sample("今天天气怎么样", "no_reliable_intent_search", []),
    sample("帮我写一首歌", "no_reliable_intent_search", []),
]


SMOKE_SAMPLES = [
    sample("王玉龙专家是什么卖点", "business_intent_search", ["expert_planning"]),
    sample("我想找一张王玉龙老师的图片", "business_intent_search", ["expert_planning"]),
    sample("洋葱的拍题精学能让孩子学一题会一类", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("拍题精学是什么卖点", "business_intent_search", ["photo_guided_learning"]),
    sample("孩子学会一道题以后会做一类题", "business_intent_search", ["transfer_practice"]),
    sample("同一道题既看公式法也看图形法", "business_intent_search", ["universal_method"]),
    sample("拍完题讲解后自动推送几道相似题", "multi_business_intent_search", ["photo_guided_learning", "transfer_practice"]),
    sample("专家设计课程，AI再根据孩子成绩安排每天任务", "multi_business_intent_search", ["expert_planning", "ai_learning_plan"]),
    sample("只要真人老师督学，不要AI自动排计划", "business_intent_search", ["human_teacher_supervision"], ["ai_learning_plan"]),
    sample("学完就测，周末再给家长一份学习报告", "multi_business_intent_search", ["instant_quiz", "learning_report"]),
    sample("拍课本五分钟预习，不是拍题搜答案", "business_intent_search", ["rapid_preview_review"], ["photo_guided_learning"]),
    sample("把孩子做错的纸质题保存下来以后反复练", "business_intent_search", ["ai_error_book"]),
    sample("新高考跨学科情境题怎么准备", "business_intent_search", ["new_curriculum_prediction"]),
    sample("小升初课程和学校教材版本都要衔接", "multi_business_intent_search", ["stage_transition", "school_sync"]),
    sample("想要一张橙色的专家人物照片", "business_intent_search", ["expert_planning"]),
    sample("王玉龙老师照片要横版", "business_intent_search", ["expert_planning"]),
    sample("要一张绿色渐变背景", "visual_scene_search", []),
    sample("覆盖真实成绩的数据截图", "visual_scene_search", []),
    sample("孩子最近状态不好", "no_reliable_intent_search", []),
    sample("效果好而且省心", "no_reliable_intent_search", []),
]


def load_source_samples() -> list[dict[str, Any]]:
    by_query: dict[str, dict[str, Any]] = {}
    for path in SOURCE_FILES:
        for line in path.read_text(encoding="utf-8").splitlines():
            payload = json.loads(line)
            query = payload["messages"][1]["content"].strip()
            old_answer = json.loads(payload["messages"][2]["content"])
            answer = {
                "query_type": old_answer["query_type"],
                "matched_codes": [item["concept"] for item in old_answer["matched_business_concepts"]],
                "excluded_codes": old_answer["excluded_concepts"],
            }
            previous = by_query.get(query)
            if previous and previous["answer"] != answer:
                previous_codes = set(previous["answer"]["matched_codes"])
                current_codes = set(answer["matched_codes"])
                if previous_codes != current_codes or previous["answer"]["query_type"] != answer["query_type"]:
                    raise ValueError(f"Conflicting labels for duplicate query: {query}")
                previous["answer"]["matched_codes"] = sorted(previous_codes)
                continue
            by_query[query] = sample(query, answer["query_type"], answer["matched_codes"], answer["excluded_codes"])
    return list(by_query.values())


def to_messages(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": record["query"]},
            {
                "role": "assistant",
                "content": json.dumps(record["answer"], ensure_ascii=False, separators=(",", ":")),
            },
        ]
    }


def validate(records: list[dict[str, Any]], name: str) -> None:
    seen: set[str] = set()
    for record in records:
        query = record["query"]
        answer = record["answer"]
        if not query or query in seen:
            raise ValueError(f"{name}: empty or duplicate query: {query!r}")
        seen.add(query)
        if set(answer) != {"query_type", "matched_codes", "excluded_codes"}:
            raise ValueError(f"{name}: invalid answer keys for {query}")
        query_type = answer["query_type"]
        codes = answer["matched_codes"]
        excluded = answer["excluded_codes"]
        if query_type not in ALLOWED_QUERY_TYPES:
            raise ValueError(f"{name}: invalid query_type for {query}")
        if len(codes) != len(set(codes)) or len(codes) > 4:
            raise ValueError(f"{name}: invalid matched_codes for {query}")
        if not set(codes).issubset(ALLOWED_CODES) or not set(excluded).issubset(ALLOWED_CODES):
            raise ValueError(f"{name}: unknown code for {query}")
        if set(codes) & set(excluded):
            raise ValueError(f"{name}: positive/excluded conflict for {query}")
        if query_type == "business_intent_search" and len(codes) != 1:
            raise ValueError(f"{name}: single-intent sample must have exactly one code: {query}")
        if query_type == "multi_business_intent_search" and len(codes) < 2:
            raise ValueError(f"{name}: multi-intent sample must have at least two codes: {query}")
        if query_type in {"visual_scene_search", "no_reliable_intent_search"} and codes:
            raise ValueError(f"{name}: non-business sample cannot have matched codes: {query}")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    content = "\n".join(
        json.dumps(to_messages(record), ensure_ascii=False, separators=(",", ":")) for record in records
    )
    path.write_text(content + "\n", encoding="utf-8")


def main() -> None:
    source = load_source_samples()
    eval_payload = json.loads(EVAL_CASES_FILE.read_text(encoding="utf-8"))
    validation_queries = {item["query"].strip() for item in eval_payload["cases"]}
    smoke_queries = {record["query"] for record in SMOKE_SAMPLES}

    validation = [record for record in source if record["query"] in validation_queries]
    train = [
        record
        for record in source
        if record["query"] not in validation_queries and record["query"] not in smoke_queries
    ]

    train_queries = {record["query"] for record in train}
    for record in HARD_TRAIN_SAMPLES:
        if record["query"] in train_queries or record["query"] in validation_queries:
            raise ValueError(f"Hard sample duplicates an existing sample: {record['query']}")
        train.append(record)
        train_queries.add(record["query"])

    overlap = smoke_queries & (train_queries | validation_queries)
    if overlap:
        raise ValueError(f"Smoke set leaks into train/validation: {sorted(overlap)}")

    train.sort(key=lambda item: item["query"])
    validation.sort(key=lambda item: item["query"])

    validate(train, "train")
    validate(validation, "validation")
    validate(SMOKE_SAMPLES, "smoke")

    write_jsonl(TRAIN_OUTPUT, train)
    write_jsonl(VALIDATION_OUTPUT, validation)
    write_jsonl(SMOKE_OUTPUT, SMOKE_SAMPLES)

    print(
        json.dumps(
            {
                "train": len(train),
                "validation": len(validation),
                "smoke": len(SMOKE_SAMPLES),
                "train_output": str(TRAIN_OUTPUT),
                "validation_output": str(VALIDATION_OUTPUT),
                "smoke_output": str(SMOKE_OUTPUT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
