from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

CONCEPT_CODE = "instant_quiz"
SOURCE_REF = "instant_quiz_curation_20260830"
NEIGHBOR_CONCEPT_CODE = "rapid_preview_review"

# These words are useful inside complete phrases, but alone they often mean
# learning reports, normal exercises, generic results or score data. Keep
# precise expressions such as "课后小测", "学完即测" and "课后小测反馈正确率".
BROAD_PHRASES_TO_REJECT = {
    "分数",
    "反馈",
    "学习结果看得见",
    "学完",
    "掌握",
    "掌握情况",
    "检测",
    "正确率",
    "测验",
    "结果",
    "题目",
    "日日清",
}

# These rapid review phrases are too broad in the database runtime catalog:
# "知识点" and "课后" can mean animation lessons, instant quizzes, reports or
# ordinary after-class scenes. Keeping them accepted lets rapid review steal
# "刚讲完知识点马上练几题确认" from instant_quiz.
NEIGHBOR_BROAD_PHRASES_TO_REJECT = {
    "知识点",
    "课后",
}

CURATED_PHRASES: list[tuple[str, str, float]] = [
    ("学完当前知识点马上小测", "official", 1.0),
    ("看完课立即做题确认掌握", "official", 1.0),
    ("本节课学完即练即测", "official", 1.0),
    ("课程结束自动进入配套练习", "official", 0.98),
    ("学练测闭环看掌握情况", "official", 0.98),
    ("刚讲完知识点马上练几题", "alias", 0.94),
    ("刚学完一段内容就做小测", "alias", 0.94),
    ("看完动画课马上测一测", "alias", 0.92),
    ("每节课后自动小测", "alias", 0.94),
    ("本节知识点配套小测", "alias", 0.94),
    ("当前知识点随堂测验", "alias", 0.92),
    ("学完马上做几道题", "alias", 0.94),
    ("学完马上检测掌握情况", "alias", 0.94),
    ("看完知识点立刻小测", "alias", 0.92),
    ("一节课结束马上练习", "alias", 0.9),
    ("课后马上知道会不会", "alias", 0.92),
    ("学完以后到底会没会", "alias", 0.94),
    ("马上看看孩子是不是真会", "alias", 0.92),
    ("本节掌握度即时反馈", "alias", 0.92),
    ("本节课掌握情况反馈", "alias", 0.92),
    ("学完就有本节测试题", "alias", 0.92),
    ("学一小块练一小块", "alias", 0.9),
    ("学一段练一段不用攒到最后", "alias", 0.9),
    ("讲完一个点马上配练习", "alias", 0.9),
    ("5道题一组确认掌握", "alias", 0.88),
    ("配套随堂测试习题", "alias", 0.9),
    ("课程播放结束弹出小测", "alias", 0.9),
    ("学完自动跳转做题", "alias", 0.9),
    ("无需切换入口直接练", "alias", 0.86),
    ("做题后立刻看到本节掌握度", "alias", 0.9),
    ("孩子说听懂了但不知道真会不会", "pain", 0.94),
    ("听懂了但一做题就露馅", "pain", 0.9),
    ("不想只看孩子点头说会了", "pain", 0.9),
    ("学完没有小测家长心里没底", "pain", 0.9),
    ("孩子听完课容易自以为会", "pain", 0.9),
    ("学完马上测才知道漏洞", "pain", 0.9),
    ("只听课不做题不知道掌握没掌握", "pain", 0.9),
    ("家长想立刻确认孩子会不会", "pain", 0.9),
    ("刚学内容有没有漏洞马上看出来", "pain", 0.88),
    ("学完就忘需要马上巩固一下", "pain", 0.88),
    ("孩子学过但不会用题目验证", "pain", 0.86),
    ("不想等考试才发现没掌握", "pain", 0.88),
    ("想找课后小测的图", "scenario", 0.86),
    ("我想要课后小测的图学完马上检测掌握情况", "scenario", 0.88),
    ("刚讲完一个知识点想配个马上练几题确认的素材", "scenario", 0.9),
    ("刚讲完一个知识点想马上练几题确认", "scenario", 0.9),
    ("希望素材能表现学完后马上知道到底会不会", "scenario", 0.88),
    ("找手机端小图用的课后小测结果素材", "scenario", 0.86),
    ("想展示看完课马上做题的流程", "scenario", 0.86),
    ("想找学完即测页面素材", "scenario", 0.86),
    ("想突出每节课都有配套练习", "scenario", 0.86),
    ("想表达学习效果当场看得见", "scenario", 0.86),
    ("想找本节掌握度反馈图", "scenario", 0.86),
    ("想展示学完立刻检测不是只看视频", "scenario", 0.86),
    ("想表达课后小测有底气", "scenario", 0.86),
    ("想找小测正确率反馈素材", "scenario", 0.86),
    ("想找学完马上知道掌握没掌握的图", "scenario", 0.86),
    ("给家长讲学完就测不是盲目听课", "colloquial", 0.84),
    ("给家长说明孩子说会了还要测一下", "colloquial", 0.84),
    ("销售想讲学完马上练马上反馈", "colloquial", 0.84),
    ("销售想讲每节课都有即时小测", "colloquial", 0.84),
    ("汇报里突出学练测闭环", "scenario", 0.84),
    ("汇报里突出本节掌握度即时反馈", "scenario", 0.84),
    ("不是长期周报而是本节课后立刻反馈", "colloquial", 0.86),
    ("不是错题本长期复习而是学完马上测", "colloquial", 0.86),
    ("不是课前预习而是学完后立即测", "colloquial", 0.86),
    ("不是只快速过知识点而是马上做题确认", "colloquial", 0.86),
    ("学完动画课后接小测", "alias", 0.9),
    ("讲完知识点后自动练当前知识点", "alias", 0.9),
    ("当前知识点学完马上确认掌握", "alias", 0.92),
    ("每节课学完检测掌握情况", "alias", 0.92),
    ("课堂学完立即测试", "alias", 0.9),
    ("看完课马上测", "alias", 0.92),
    ("学完立即做题", "alias", 0.92),
    ("学完即练流程", "alias", 0.92),
    ("学完即测几题确认掌握", "alias", 0.92),
    ("课后小测反馈本节正确率", "alias", 0.9),
    ("本节课正确率即时显示", "alias", 0.88),
    ("做完小测看到哪里没掌握", "alias", 0.88),
    ("做错题自动沉淀到本节错题", "alias", 0.86),
    ("本节错题自动记录方便回看", "alias", 0.84),
    ("做题后生成本节掌握报告", "alias", 0.86),
    ("课后小测连接错题和学情反馈", "alias", 0.84),
    ("学完小测让正反馈不断线", "alias", 0.84),
    ("孩子学完有题做家长更踏实", "pain", 0.86),
]


def curate(dry_run: bool) -> tuple[int, int, int, int]:
    with SessionLocal() as db:
        concept = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == CONCEPT_CODE)
        )
        if concept is None:
            raise RuntimeError(f"Missing concept: {CONCEPT_CODE}")
        neighbor = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == NEIGHBOR_CONCEPT_CODE)
        )
        if neighbor is None:
            raise RuntimeError(f"Missing concept: {NEIGHBOR_CONCEPT_CODE}")

        accepted_before = sum(
            1
            for phrase in concept.search_phrases
            if phrase.review_status == "accepted"
        )
        rejected = 0
        for phrase in concept.search_phrases:
            if phrase.phrase in BROAD_PHRASES_TO_REJECT and phrase.review_status != "rejected":
                rejected += 1
                if not dry_run:
                    phrase.review_status = "rejected"
        neighbor_rejected = 0
        for phrase in neighbor.search_phrases:
            if (
                phrase.phrase in NEIGHBOR_BROAD_PHRASES_TO_REJECT
                and phrase.review_status != "rejected"
            ):
                neighbor_rejected += 1
                if not dry_run:
                    phrase.review_status = "rejected"

        existing = {phrase.phrase for phrase in concept.search_phrases}
        added = 0
        for phrase, phrase_type, weight in CURATED_PHRASES:
            if phrase in existing:
                continue
            added += 1
            existing.add(phrase)
            if dry_run:
                continue
            db.add(
                ConceptSearchPhrase(
                    concept_id=concept.id,
                    phrase=phrase,
                    phrase_type=phrase_type,
                    origin="manual",
                    review_status="accepted",
                    weight=weight,
                    source_ref=SOURCE_REF,
                )
            )

        if not dry_run and (added or rejected):
            concept.version += 1
            concept.updated_at = utcnow()
        if not dry_run and neighbor_rejected:
            neighbor.version += 1
            neighbor.updated_at = utcnow()
        if not dry_run and (added or rejected or neighbor_rejected):
            db.commit()
            accepted_after = int(
                db.scalar(
                    select(func.count(ConceptSearchPhrase.id))
                    .join(BusinessConcept)
                    .where(
                        BusinessConcept.code == CONCEPT_CODE,
                        ConceptSearchPhrase.review_status == "accepted",
                    )
                )
                or 0
            )
        else:
            accepted_after = accepted_before - rejected + added
        return rejected, added, accepted_after, neighbor_rejected


def rollback(dry_run: bool) -> tuple[int, int, int]:
    with SessionLocal() as db:
        concept = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == CONCEPT_CODE)
        )
        if concept is None:
            raise RuntimeError(f"Missing concept: {CONCEPT_CODE}")
        neighbor = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == NEIGHBOR_CONCEPT_CODE)
        )
        if neighbor is None:
            raise RuntimeError(f"Missing concept: {NEIGHBOR_CONCEPT_CODE}")

        restored = 0
        for phrase in concept.search_phrases:
            if phrase.phrase in BROAD_PHRASES_TO_REJECT and phrase.review_status == "rejected":
                restored += 1
                if not dry_run:
                    phrase.review_status = "accepted"
        neighbor_restored = 0
        for phrase in neighbor.search_phrases:
            if (
                phrase.phrase in NEIGHBOR_BROAD_PHRASES_TO_REJECT
                and phrase.review_status == "rejected"
            ):
                neighbor_restored += 1
                if not dry_run:
                    phrase.review_status = "accepted"

        removed = 0
        for phrase in concept.search_phrases:
            if phrase.source_ref == SOURCE_REF and phrase.review_status != "rejected":
                removed += 1
                if not dry_run:
                    phrase.review_status = "rejected"

        if not dry_run and (restored or removed):
            concept.version += 1
            concept.updated_at = utcnow()
        if not dry_run and neighbor_restored:
            neighbor.version += 1
            neighbor.updated_at = utcnow()
        if not dry_run and (restored or removed or neighbor_restored):
            db.commit()
        return restored, removed, neighbor_restored


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate instant_quiz phrases.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    if args.rollback:
        restored, removed, neighbor_restored = rollback(args.dry_run)
        mode = "would restore/reject" if args.dry_run else "restored/rejected"
        print(
            f"{mode}: restored_broad={restored}, rejected_curated={removed}, "
            f"neighbor_restored_broad={neighbor_restored}"
        )
        return

    rejected, added, accepted_after, neighbor_rejected = curate(args.dry_run)
    mode = "would curate" if args.dry_run else "curated"
    print(
        f"{mode}: rejected_broad={rejected}, added={added}, "
        f"accepted_after={accepted_after}, neighbor_rejected_broad={neighbor_rejected}"
    )


if __name__ == "__main__":
    main()
