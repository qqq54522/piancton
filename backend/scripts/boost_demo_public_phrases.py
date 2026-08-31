from __future__ import annotations

import argparse
from collections.abc import Iterable

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

TARGET_ACCEPTED_COUNT = 60
SOURCE_REF = "demo_public_phrase_boost_20260830"


PHRASE_FRAGMENTS: dict[str, list[tuple[str, str]]] = {
    "school_sync": [
        ("按孩子学校正在学的教材版本找对应课程", "pain"),
        ("课堂学到哪洋葱课程就跟到哪", "alias"),
        ("课外学习不再和学校章节脱节", "pain"),
        ("回家复习当天课堂刚讲过的知识点", "scenario"),
        ("提前预习明天学校要讲的章节", "scenario"),
        ("不同地区教材版本都能对应学习", "alias"),
        ("家长想确认课程和学校教材是不是一致", "pain"),
        ("孩子用的课本章节能在洋葱里找到对应内容", "scenario"),
        ("同步学校进度做预习和复习", "alias"),
        ("不另起一套课程而是跟着校内学", "pain"),
    ],
    "animation_explanation": [
        ("用动画把抽象知识点讲清楚", "alias"),
        ("几分钟把一个知识点讲透", "alias"),
        ("老师讲太快孩子回家用动画补懂", "pain"),
        ("把看不见的变化过程做成动画演示", "alias"),
        ("用故事化动画降低理解门槛", "alias"),
        ("孩子课堂没听懂需要动画重新拆解", "pain"),
        ("把枯燥难懂的知识变成直观画面", "alias"),
        ("短时微课聚焦一个核心知识点", "alias"),
        ("动画演示帮助孩子理解底层原理", "scenario"),
        ("想表达动画课不是普通录播课", "scenario"),
    ],
    "instant_quiz": [
        ("每节课学完马上做题检测掌握情况", "alias"),
        ("看完知识点立刻小测确认会不会", "alias"),
        ("家长想知道孩子是不是真的听懂了", "pain"),
        ("课程结束自动进入本节配套练习", "scenario"),
        ("学完一个知识点马上获得练习反馈", "alias"),
        ("用课后小测发现刚学内容的漏洞", "scenario"),
        ("孩子说会了但需要题目验证", "pain"),
        ("学练测连在一起不只看视频", "alias"),
        ("当天知识当天测当天巩固", "scenario"),
        ("通过小测看到本节课掌握度", "alias"),
    ],
    "new_curriculum_prediction": [
        ("围绕新课标变化拆解考试怎么考", "alias"),
        ("针对新中考新题型做专项准备", "alias"),
        ("练跨学科情境题和开放探究题", "alias"),
        ("家长担心考试改革后孩子不会做新题", "pain"),
        ("把新旧题型差异讲清楚", "scenario"),
        ("提前理解新考法和命题趋势", "alias"),
        ("新课标下的新情境题训练", "alias"),
        ("孩子遇到灵活题不知道从哪下手", "pain"),
        ("给销售讲新中考题型变化的应对方案", "scenario"),
        ("想找新课标新考法相关宣传素材", "scenario"),
    ],
    "focused_excellence": [
        ("考前按薄弱题型做专项突破", "alias"),
        ("月考期末前集中抓重点难点", "scenario"),
        ("孩子想从基础分往高分段冲", "pain"),
        ("针对压轴题和重难点做拔高训练", "alias"),
        ("时间有限先练最该提分的模块", "pain"),
        ("哪里薄弱就集中练哪里", "alias"),
        ("考试前快速定位高频考点", "scenario"),
        ("高分孩子继续做难题提升", "scenario"),
        ("按题型模块做精准补弱", "alias"),
        ("考前宣传想突出重难点突破能力", "scenario"),
    ],
    "transfer_practice": [
        ("一道题讲完还能继续练同类题", "alias"),
        ("换数字换条件换问法也会做", "alias"),
        ("孩子不是只会原题而是会一类题", "pain"),
        ("通过变式题训练举一反三能力", "alias"),
        ("讲完例题后推荐相似题巩固迁移", "scenario"),
        ("理解出题逻辑后陌生题也有思路", "alias"),
        ("从这一题迁移到同类题型", "scenario"),
        ("不背答案也能应对题目变化", "pain"),
        ("做一道题掌握一类题的方法", "alias"),
        ("考试题稍微变形孩子也能反应过来", "pain"),
    ],
    "expert_planning": [
        ("命题专家和教材编者参与课程设计", "alias"),
        ("用出题人视角规划学习路径", "alias"),
        ("课程体系由教研专家把关", "alias"),
        ("不是盲目补课而是有专家规划", "pain"),
        ("家长想知道课程背后是谁设计的", "pain"),
        ("真正懂考试和教材的人设计课程", "alias"),
        ("长期学习路径有专家教研支撑", "scenario"),
        ("每一步课程顺序都有教研依据", "scenario"),
        ("销售想突出专家背书和课程可信度", "scenario"),
        ("给家长讲课程体系不是随便拼的", "colloquial"),
    ],
    "stage_transition": [
        ("小升初阶段提前补知识断层", "alias"),
        ("初升高前适应新学段难度", "alias"),
        ("孩子升学后怕课程难度突然变大", "pain"),
        ("用衔接课程平稳过渡到新阶段", "scenario"),
        ("从小学到初中学习方式需要过渡", "scenario"),
        ("初中到高中知识坡度提前适应", "alias"),
        ("家长担心孩子新学段接不上", "pain"),
        ("小初高课程体系连续不换路径", "alias"),
        ("升学节点有专门衔接安排", "scenario"),
        ("想找体现学段过渡和长期覆盖的素材", "scenario"),
    ],
    "universal_method": [
        ("同一道题可以拆出不同解法", "alias"),
        ("培养孩子从条件推结论的思维", "alias"),
        ("不靠死记硬背而是理解底层逻辑", "pain"),
        ("一道题看出多种方法路径", "alias"),
        ("孩子遇到陌生题也能自己分析", "pain"),
        ("建立理科思维和通用解题方法", "alias"),
        ("不是套公式而是理解为什么这样做", "pain"),
        ("用底层方法拆解复杂题目", "alias"),
        ("长期培养学科思维后劲", "scenario"),
        ("想突出万能解法背后的通用思路", "scenario"),
    ],
    "ai_learning_plan": [
        ("根据孩子水平自动安排每天学什么", "alias"),
        ("按成绩目标和可用时间生成学习计划", "alias"),
        ("每个孩子匹配不同的课程路径", "alias"),
        ("家长不知道先学什么让系统来排", "pain"),
        ("根据薄弱点推荐下一步学习内容", "alias"),
        ("不是所有孩子都学同一套课程", "pain"),
        ("AI动态调整专属学习节奏", "alias"),
        ("把学习目标拆成每天可执行任务", "scenario"),
        ("孩子基础不同系统自动匹配内容", "scenario"),
        ("想表达千人千面的个性化学习方案", "scenario"),
    ],
    "ai_tutor_qa": [
        ("孩子学习中遇到问题可以随时问AI", "alias"),
        ("晚上写作业卡住也有人讲", "pain"),
        ("家长不会辅导时AI可以即时答疑", "pain"),
        ("用文字或语音和AI互动提问", "alias"),
        ("不会的问题不用等到第二天问老师", "pain"),
        ("AI像私教一样随时解释知识点", "alias"),
        ("孩子不好意思问老师也能自己提问", "pain"),
        ("学习过程里随时获得点拨和讲解", "scenario"),
        ("题目卡住时先让AI讲思路", "scenario"),
        ("想找体现AI互动辅导的素材", "scenario"),
    ],
    "photo_guided_learning": [
        ("拍题后不要直接给答案而是讲思路", "alias"),
        ("用拍照入口一步步引导孩子解题", "alias"),
        ("家长怕孩子拍题只抄答案", "pain"),
        ("AI先问步骤再带孩子还原思考过程", "alias"),
        ("拍完题先点拨关键思路", "scenario"),
        ("不会题拍一下但不能变成偷懒工具", "pain"),
        ("通过启发式提问让孩子自己想出来", "alias"),
        ("拍题讲解重视过程不是只给结果", "alias"),
        ("孩子看答案会了换题还是不会", "pain"),
        ("想突出拍题精学区别于搜答案", "scenario"),
    ],
    "rapid_preview_review": [
        ("课前拍课本快速预习明天内容", "alias"),
        ("课后拍笔记快速复习今天知识", "alias"),
        ("几分钟先把新课重点过一遍", "scenario"),
        ("上课前没时间也能快速建立认知", "pain"),
        ("作业前先回顾当天课堂知识点", "scenario"),
        ("碎片时间完成轻量预习复习", "alias"),
        ("课前带着问题去听老师讲课", "scenario"),
        ("课后快速查漏补缺巩固重点", "alias"),
        ("拍教材目录生成预习重点", "scenario"),
        ("想表达极速预习复习适合短时间使用", "scenario"),
    ],
    "ai_error_book": [
        ("把个人错题自动归档到错题本", "alias"),
        ("错题后自动推荐同类题复练", "alias"),
        ("练习册错题不用手抄也能整理", "pain"),
        ("根据错因分析薄弱知识点", "alias"),
        ("孩子同一类题反复错需要复盘", "pain"),
        ("从历史错题出发做针对复习", "scenario"),
        ("考前优先复习自己真正错过的题", "scenario"),
        ("拍照上传错题并沉淀复练记录", "alias"),
        ("错题整理费时间系统自动帮忙归纳", "pain"),
        ("想找体现个人错题闭环的素材", "scenario"),
    ],
    "human_teacher_supervision": [
        ("真人老师定期提醒孩子学习打卡", "alias"),
        ("伴学老师持续跟进学习执行情况", "alias"),
        ("家长不想每天催作业催到吵架", "pain"),
        ("孩子自律差需要真人督促", "pain"),
        ("老师根据学情做阶段规划和回访", "alias"),
        ("有人帮家长盯学习过程", "scenario"),
        ("真人老师发现问题后持续跟进", "alias"),
        ("每天学习任务有人提醒和监督", "scenario"),
        ("家长希望把催学这件事交给老师", "pain"),
        ("想突出真人伴学带来的执行保障", "scenario"),
    ],
    "learning_report": [
        ("每周汇总孩子学了什么学了多久", "alias"),
        ("家长通过微信查看学习周报", "alias"),
        ("报告里看到正确率和薄弱知识点", "alias"),
        ("不用天天盯屏幕也能了解学习过程", "pain"),
        ("学习时长课程完成情况一目了然", "scenario"),
        ("家长想知道孩子到底有没有认真学", "pain"),
        ("每周推送学习成果和进步情况", "alias"),
        ("从学情报告看到高频错题和薄弱点", "scenario"),
        ("把学习过程从黑盒变成可查看数据", "pain"),
        ("想找体现家长端学习反馈的素材", "scenario"),
    ],
}

PREFIX_TEMPLATES: tuple[tuple[str, str, float], ...] = (
    ("{}", "", 0.86),
    ("想找一张体现{}的素材", "scenario", 0.78),
    ("销售想讲{}", "colloquial", 0.8),
    ("给家长说明{}", "colloquial", 0.8),
    ("做汇报时想突出{}", "scenario", 0.78),
)


def _candidate_phrases(code: str) -> Iterable[tuple[str, str, float]]:
    for fragment, phrase_type in PHRASE_FRAGMENTS[code]:
        for template, override_type, weight in PREFIX_TEMPLATES:
            yield template.format(fragment), override_type or phrase_type, weight


def _accepted_count(concept: BusinessConcept) -> int:
    return sum(1 for item in concept.search_phrases if item.review_status == "accepted")


def boost(target: int, dry_run: bool) -> dict[str, tuple[int, int]]:
    report: dict[str, tuple[int, int]] = {}
    with SessionLocal() as db:
        concepts = {
            item.code: item
            for item in db.scalars(
                select(BusinessConcept).where(BusinessConcept.status == "active")
            )
        }
        missing = sorted(set(PHRASE_FRAGMENTS) - set(concepts))
        if missing:
            raise RuntimeError(f"Missing active business concepts: {', '.join(missing)}")

        for code in PHRASE_FRAGMENTS:
            concept = concepts[code]
            before = _accepted_count(concept)
            existing = {item.phrase.strip() for item in concept.search_phrases}
            added = 0
            for phrase, phrase_type, weight in _candidate_phrases(code):
                normalized = phrase.strip()
                if not normalized or normalized in existing:
                    continue
                if before + added >= target:
                    break
                existing.add(normalized)
                added += 1
                if dry_run:
                    continue
                db.add(
                    ConceptSearchPhrase(
                        concept_id=concept.id,
                        phrase=normalized,
                        phrase_type=phrase_type,
                        origin="manual",
                        review_status="accepted",
                        weight=weight,
                        source_ref=SOURCE_REF,
                    )
                )
            if before + added < target:
                raise RuntimeError(
                    f"{code} only reaches {before + added}; add more candidates first"
                )
            if added and not dry_run:
                concept.version += 1
                concept.updated_at = utcnow()
            report[code] = (before, added)
        if not dry_run:
            db.commit()
    return report


def rollback(dry_run: bool) -> int:
    with SessionLocal() as db:
        phrases = db.scalars(
            select(ConceptSearchPhrase).where(ConceptSearchPhrase.source_ref == SOURCE_REF)
        ).all()
        changed = 0
        for phrase in phrases:
            if phrase.review_status == "rejected":
                continue
            changed += 1
            if not dry_run:
                phrase.review_status = "rejected"
                if phrase.concept:
                    phrase.concept.version += 1
                    phrase.concept.updated_at = utcnow()
        if not dry_run:
            db.commit()
        return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add low-ambiguity demo public phrases up to a target count."
    )
    parser.add_argument("--target", type=int, default=TARGET_ACCEPTED_COUNT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    if args.rollback:
        changed = rollback(args.dry_run)
        mode = "would reject" if args.dry_run else "rejected"
        print(f"{mode} {changed} phrases from {SOURCE_REF}")
        return

    report = boost(max(args.target, 1), args.dry_run)
    for code, (before, added) in report.items():
        action = "would add" if args.dry_run else "added"
        print(f"{code}: before={before}, {action}={added}, after={before + added}")


if __name__ == "__main__":
    main()
