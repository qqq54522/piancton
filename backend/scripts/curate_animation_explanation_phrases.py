from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

CONCEPT_CODE = "animation_explanation"
SOURCE_REF = "animation_explanation_curation_20260830"

# These are useful ingredients, but alone they are ambiguous: they can mean a
# visual style, a normal course, a photo-question explanation, preview/review or
# even an unrelated design asset. Complete phrases keep the intended meaning.
BROAD_PHRASES_TO_REJECT = {
    "动画",
    "卡住",
    "可视化",
    "听不懂",
    "故事",
    "演示",
    "直观",
    "知识点",
    "讲解",
    "课程",
    "跟不上课",
}

CURATED_PHRASES: list[tuple[str, str, float]] = [
    ("动画讲透课堂知识点", "official", 1.0),
    ("情境动画分层拆解知识点", "official", 1.0),
    ("5-8分钟动画微课", "official", 1.0),
    ("把抽象知识变成动画讲解", "official", 0.98),
    ("用动画把枯燥知识讲成秒懂", "official", 0.98),
    ("一节动画课讲透一个小知识点", "alias", 0.94),
    ("短时动画微课讲清难点", "alias", 0.94),
    ("几分钟动画讲明白一个知识点", "alias", 0.94),
    ("动画课把难点分层拆开讲", "alias", 0.94),
    ("动画课不是普通视频课", "alias", 0.9),
    ("动画课把复杂概念讲简单", "alias", 0.94),
    ("动画课像讲故事一样讲知识", "alias", 0.92),
    ("故事化动画讲解知识点", "alias", 0.92),
    ("可视化动画拆解抽象原理", "alias", 0.94),
    ("动态演示知识点变化过程", "alias", 0.92),
    ("看不见的知识变成看得见", "alias", 0.94),
    ("把看不见的变化过程做成动画", "alias", 0.92),
    ("抽象原理用动画演示出来", "alias", 0.92),
    ("学科难点动画可视化", "alias", 0.9),
    ("理科抽象概念动画演示", "alias", 0.9),
    ("数学知识点动画讲解", "alias", 0.9),
    ("物理原理动画演示", "alias", 0.9),
    ("地理现象故事化动画", "alias", 0.9),
    ("电磁感应动画演示", "alias", 0.88),
    ("导数瞬时变化率动画讲解", "alias", 0.88),
    ("锋面雨形成过程动画", "alias", 0.88),
    ("等高线立体动画演示", "alias", 0.88),
    ("剥洋葱式分层拆解知识点", "alias", 0.9),
    ("先用情境再讲定义", "alias", 0.88),
    ("不直接灌输定义而是动画拆解", "alias", 0.9),
    ("把公式背后的原理演出来", "alias", 0.9),
    ("课堂没听懂回家看动画补懂", "pain", 0.9),
    ("老师讲太快孩子回家用动画补", "pain", 0.9),
    ("老师讲得太深孩子听不懂", "pain", 0.88),
    ("孩子觉得知识点太抽象", "pain", 0.9),
    ("孩子一听抽象概念就懵", "pain", 0.88),
    ("课堂内容枯燥孩子坐不住", "pain", 0.86),
    ("听老师讲没画面感理解不了", "pain", 0.88),
    ("知识点太抽象需要看过程", "pain", 0.9),
    ("复杂概念孩子听完还是糊", "pain", 0.88),
    ("上课没跟上需要动画补位", "pain", 0.9),
    ("孩子不是不学是没听懂", "pain", 0.86),
    ("家长讲不清想找动画课", "pain", 0.86),
    ("想找动画精讲素材", "scenario", 0.86),
    ("想找动画讲透知识点的图", "scenario", 0.86),
    ("找动画精讲素材能把抽象知识动态讲透", "scenario", 0.88),
    ("要一张把看不见的知识变成能动过程的画面", "scenario", 0.88),
    ("想要把难概念讲成小故事的画面", "scenario", 0.88),
    ("想展示动画课为什么孩子更容易懂", "scenario", 0.86),
    ("想表达抽象知识被动画拆开", "scenario", 0.86),
    ("想突出动画课不是只放视频", "scenario", 0.86),
    ("想找一节课一个点讲透的素材", "scenario", 0.86),
    ("想找几分钟讲明白一个知识点的图", "scenario", 0.86),
    ("想表达课堂没懂回家还能补懂", "scenario", 0.86),
    ("想找老师讲太快的补位课程图", "scenario", 0.84),
    ("想展示抽象变直观的教学方式", "scenario", 0.86),
    ("想找动态演示知识形成过程的图", "scenario", 0.86),
    ("给家长讲动画课怎么把难点讲透", "colloquial", 0.84),
    ("给家长说明动画不是娱乐而是讲知识", "colloquial", 0.84),
    ("销售想讲动画课降低理解门槛", "colloquial", 0.84),
    ("销售想讲几分钟聚焦一个知识点", "colloquial", 0.84),
    ("汇报里突出动画课分层拆解", "scenario", 0.84),
    ("汇报里突出抽象知识可视化", "scenario", 0.84),
    ("需要证明动画课程有教研设计", "scenario", 0.84),
    ("想找动画课制作和教研逻辑", "scenario", 0.84),
    ("动画微课研发打磨过程", "alias", 0.86),
    ("动画课程教研方法论", "alias", 0.86),
    ("认知理论支持的动画课程", "alias", 0.84),
    ("学科教研和动画编剧一起打磨", "alias", 0.84),
    ("动画课程不是直接给答案", "colloquial", 0.82),
    ("不用孩子硬背先让他看懂过程", "colloquial", 0.86),
    ("用动画还原知识发生过程", "alias", 0.9),
    ("把静态知识变成动态过程", "alias", 0.9),
    ("抽象知识动态化表达", "alias", 0.9),
    ("难点被拆成孩子能理解的步骤", "alias", 0.88),
    ("孩子愿意看的知识点动画", "alias", 0.88),
    ("像故事一样进入知识点", "alias", 0.88),
    ("课程短但能讲清一个点", "alias", 0.9),
    ("不是长课而是一个点讲透", "alias", 0.9),
    ("每节动画微课只聚焦一个知识点", "alias", 0.9),
    ("短时间把知识点讲明白", "alias", 0.88),
    ("动画帮孩子补上课堂没听懂的部分", "pain", 0.88),
    ("孩子跟不上老师节奏用动画重听", "pain", 0.88),
    ("抽象知识没有画面孩子很难懂", "pain", 0.88),
    ("想要动画讲解的每回只消化一个小点", "scenario", 0.86),
    ("想要动画讲解每次聚焦一个小问题", "scenario", 0.86),
    ("不要拍照搜题要动画精讲", "scenario", 0.86),
]


def curate(dry_run: bool) -> tuple[int, int, int]:
    with SessionLocal() as db:
        concept = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == CONCEPT_CODE)
        )
        if concept is None:
            raise RuntimeError(f"Missing concept: {CONCEPT_CODE}")

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
        return rejected, added, accepted_after


def rollback(dry_run: bool) -> tuple[int, int]:
    with SessionLocal() as db:
        concept = db.scalar(
            select(BusinessConcept)
            .options(selectinload(BusinessConcept.search_phrases))
            .where(BusinessConcept.code == CONCEPT_CODE)
        )
        if concept is None:
            raise RuntimeError(f"Missing concept: {CONCEPT_CODE}")

        restored = 0
        for phrase in concept.search_phrases:
            if phrase.phrase in BROAD_PHRASES_TO_REJECT and phrase.review_status == "rejected":
                restored += 1
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
            db.commit()
        return restored, removed


def main() -> None:
    parser = argparse.ArgumentParser(description="Curate animation_explanation phrases.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    if args.rollback:
        restored, removed = rollback(args.dry_run)
        mode = "would restore/reject" if args.dry_run else "restored/rejected"
        print(f"{mode}: restored_broad={restored}, rejected_curated={removed}")
        return

    rejected, added, accepted_after = curate(args.dry_run)
    mode = "would curate" if args.dry_run else "curated"
    print(f"{mode}: rejected_broad={rejected}, added={added}, accepted_after={accepted_after}")


if __name__ == "__main__":
    main()
