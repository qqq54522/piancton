from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

CONCEPT_CODE = "transfer_practice"
SOURCE_REF = "transfer_practice_curation_20260830"

# These words can appear in the right context, but alone they are too broad for
# a high-confidence public phrase. Keep complete expressions such as "迁移练习",
# "变式题训练" and "换题也会" as accepted phrases.
BROAD_PHRASES_TO_REJECT = {
    "训练",
    "迁移",
    "换题",
}

CURATED_PHRASES: list[tuple[str, str, float]] = [
    ("理解原理再做变式题", "official", 1.0),
    ("一道题讲透一类题", "official", 1.0),
    ("先讲出题原理再练同类题", "official", 1.0),
    ("从解一题到通一类", "official", 0.98),
    ("变式与同类题迁移训练", "official", 0.98),
    ("讲完例题再练变式题", "alias", 0.94),
    ("当前题讲完推荐同类题", "alias", 0.94),
    ("一题讲透再做相似题", "alias", 0.94),
    ("同考点变式巩固", "alias", 0.92),
    ("换数字换条件专项训练", "alias", 0.92),
    ("换问法也能抓住思路", "alias", 0.92),
    ("一题带多道同类题", "alias", 0.94),
    ("做完这道题继续练同类题", "alias", 0.92),
    ("相似题巩固迁移", "alias", 0.92),
    ("变式题巩固迁移", "alias", 0.92),
    ("通过一题掌握一类题", "alias", 0.94),
    ("从例题迁移到考试题", "alias", 0.92),
    ("由一道题拓展到一类题", "alias", 0.92),
    ("对照原题练换问法题", "alias", 0.9),
    ("例题后自动推送相似题", "alias", 0.9),
    ("不是背模板而是理解原理", "alias", 0.94),
    ("先看懂题型本质再训练", "alias", 0.9),
    ("理解出题逻辑再解题", "alias", 0.92),
    ("看懂底层逻辑再做新题", "alias", 0.9),
    ("不是只记结论而是会迁移", "alias", 0.9),
    ("把解题思路迁移到陌生题", "alias", 0.92),
    ("通过原理看穿题目变化", "alias", 0.9),
    ("学会方法后换题也会", "alias", 0.92),
    ("掌握题目背后的出题逻辑", "alias", 0.9),
    ("会做原题还要会做变式", "alias", 0.92),
    ("孩子例题会做考试题一绕就懵", "pain", 0.9),
    ("题目条件一调整就卡住", "pain", 0.88),
    ("换了问法孩子就没思路", "pain", 0.9),
    ("只会套公式不懂为什么", "pain", 0.88),
    ("孩子一遇到变式题就卡住", "pain", 0.9),
    ("题目稍微综合一点就不会", "pain", 0.88),
    ("老师讲过原题换题又错", "pain", 0.88),
    ("只会背步骤不会迁移", "pain", 0.9),
    ("会听懂但换个题还是错", "pain", 0.9),
    ("考试题稍微拐弯就不会下笔", "pain", 0.9),
    ("不想孩子只会做一模一样的题", "pain", 0.88),
    ("孩子做题靠记套路不稳定", "pain", 0.86),
    ("想找一张一道题带一类题的图", "scenario", 0.86),
    ("想表达孩子不是会原题而是真会一类题", "scenario", 0.86),
    ("想展示从解一题到通一类", "scenario", 0.86),
    ("想找换条件也会的课程素材", "scenario", 0.86),
    ("给家长讲为什么不是死记硬背", "colloquial", 0.84),
    ("销售想讲例题后相似题巩固", "colloquial", 0.84),
    ("汇报里突出原理迁移能力", "scenario", 0.84),
    ("想找考试题拐弯也不慌的素材", "scenario", 0.86),
    ("想讲会做陌生题的底层能力", "scenario", 0.86),
    ("想表达题目变化也能抓住本质", "scenario", 0.86),
    ("需要洋葱举一反三的图", "scenario", 0.86),
    ("体现一道题带一类题", "scenario", 0.86),
    ("一题讲完后还能顺着练同一类题", "scenario", 0.88),
    ("想表达从一道题的方法迁移到变式题", "scenario", 0.88),
    ("孩子只记住解法换个场景就不会", "pain", 0.88),
    ("数学题条件一调整就卡住想看练法", "scenario", 0.86),
    ("想搜能教孩子把一个方法用到更多题里的图片", "scenario", 0.86),
    ("考题一绕就想找理解思路的课", "scenario", 0.86),
    ("拍题讲解后继续推相似题", "alias", 0.9),
    ("AI讲完题后再出同类题", "alias", 0.9),
    ("不只是拍题解答还要相似题巩固", "colloquial", 0.88),
    ("拍完题不是给答案而是带着做变式", "colloquial", 0.88),
    ("从当前不会题延伸到同类题", "alias", 0.9),
    ("拍题后用变式确认有没有真会", "alias", 0.9),
    ("讲完当前题再推荐几道相似题", "alias", 0.9),
    ("不会这道题时顺带学会这一类", "colloquial", 0.88),
    ("相似题不是刷量而是确认迁移", "colloquial", 0.86),
    ("同类题训练不是个人错题本复练", "colloquial", 0.84),
    ("不是同一道题换解法而是换题也会", "colloquial", 0.86),
    ("不是只看动画听懂而是能做变式", "colloquial", 0.84),
    ("讲清原理后再做条件变化题", "alias", 0.9),
    ("题目换数字也能沿着同一思路做", "alias", 0.9),
    ("题干换场景还能识别同一类题", "alias", 0.9),
    ("从题目套路看到出题本质", "alias", 0.88),
    ("把一道例题拆成可迁移的方法", "alias", 0.88),
    ("通过变式练出迁移能力", "alias", 0.9),
    ("相似题推荐帮助巩固一类题", "alias", 0.88),
    ("讲解之后马上接同考点变式", "alias", 0.9),
    ("例题不是终点后面还有同类训练", "colloquial", 0.86),
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
    parser = argparse.ArgumentParser(description="Curate transfer_practice phrases.")
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
