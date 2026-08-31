from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

CONCEPT_CODE = "focused_excellence"
SOURCE_REF = "focused_excellence_curation_20260830"

# These are real words, but too broad as high-confidence public phrases for this
# selling point. Keeping a rejected row makes runtime catalog merging suppress the
# static seed too, so generic "提分" does not hijack unrelated searches.
BROAD_PHRASES_TO_REJECT = {
    "提分",
    "突破",
    "考前",
    "重点",
    "高频",
    "能力进阶",
}

CURATED_PHRASES: list[tuple[str, str, float]] = [
    ("分学科重难点专项训练", "official", 1.0),
    ("按题型专项突破", "official", 1.0),
    ("题型突破", "alias", 0.96),
    ("压轴题专项提升", "official", 1.0),
    ("考前一键划重点", "official", 1.0),
    ("全网高频易错题训练", "official", 1.0),
    ("按薄弱章节做专项突破", "alias", 0.94),
    ("针对薄弱题型集中练", "alias", 0.94),
    ("选择填空计算解答分题型训练", "alias", 0.92),
    ("数学压轴题集中突破", "alias", 0.94),
    ("物理重难点专项突破", "alias", 0.92),
    ("初中新中考重难点培优", "alias", 0.9),
    ("高中压轴专题培优", "alias", 0.92),
    ("小学思维培优专项", "alias", 0.88),
    ("单项题型强化训练", "alias", 0.92),
    ("哪里丢分就练哪里", "alias", 0.9),
    ("薄弱章节集中突破", "alias", 0.92),
    ("核心题型专项强化", "alias", 0.92),
    ("把容易失分的模块单独拎出来练", "colloquial", 0.86),
    ("不整套刷题而是按模块突破", "colloquial", 0.86),
    ("想找按题型拆分训练的素材", "scenario", 0.84),
    ("给家长讲专项培优不是漫无目的刷题", "colloquial", 0.84),
    ("孩子某一类题反复丢分需要集中练", "pain", 0.9),
    ("做了很多题但关键题型还是错", "pain", 0.88),
    ("天天刷题但没抓到薄弱环节", "pain", 0.88),
    ("多科压力大不知道先突破哪一块", "pain", 0.86),
    ("苦学没结果需要先锁定得分短板", "pain", 0.86),
    ("时间有限不想继续无效刷题", "pain", 0.86),
    ("全网高频错题集中练", "alias", 0.94),
    ("群体共性易错题训练", "alias", 0.92),
    ("大家容易错的题先练", "colloquial", 0.9),
    ("错误率高的题型重点训练", "alias", 0.9),
    ("常见失分点专项突破", "alias", 0.92),
    ("高频失分题优先练", "alias", 0.9),
    ("全网题库里多数学生容易错的题", "scenario", 0.86),
    ("不是孩子个人错题而是群体高频错题", "colloquial", 0.9),
    ("想找体现共性易错题整理的素材", "scenario", 0.84),
    ("考前按高频易错点复习", "alias", 0.9),
    ("减少盲刷题先看高频失分点", "pain", 0.86),
    ("月考前快速划重点", "alias", 0.94),
    ("期中考试前集中抓重点", "alias", 0.92),
    ("期末冲刺前梳理关键考点", "alias", 0.92),
    ("模考前抓高频考点", "alias", 0.9),
    ("临考几天先练关键得分项", "scenario", 0.9),
    ("中考前按重点题型冲刺", "scenario", 0.9),
    ("开学考前快速过重点", "scenario", 0.86),
    ("最后阶段快速补薄弱点", "scenario", 0.88),
    ("短时间把考试重点梳理出来", "alias", 0.9),
    ("考试前不知道复习什么先划重点", "pain", 0.88),
    ("考前不盲刷先练重点模块", "colloquial", 0.88),
    ("销售想讲考前有限时间练关键项", "colloquial", 0.84),
    ("训练拔高", "alias", 0.94),
    ("想训练拔高的图", "alias", 0.96),
    ("找训练拔高的素材", "alias", 0.94),
    ("想找训练拔高素材", "alias", 0.94),
    ("能体现训练拔高的图", "alias", 0.94),
    ("给高分孩子训练拔高", "colloquial", 0.88),
    ("优生继续拔高训练", "alias", 0.9),
    ("高分段冲刺满分", "alias", 0.9),
    ("成绩不错但压轴题总丢分", "pain", 0.88),
    ("学有余力还想继续提升", "pain", 0.86),
    ("不是只教基础还要做高阶突破", "colloquial", 0.88),
    ("从90分往满分冲刺", "alias", 0.9),
    ("高阶能力专项训练", "alias", 0.88),
    ("难题拔高专项模块", "alias", 0.9),
    ("想找体现高分孩子继续拔高的图", "scenario", 0.84),
    ("给家长说明培优课能覆盖高阶难题", "colloquial", 0.84),
    ("销售想讲专项培优锁定考试失分点", "colloquial", 0.84),
    ("汇报专项培优如何抓重难点和薄弱项", "scenario", 0.84),
    ("想表达有限时间练最关键的得分项", "scenario", 0.86),
    ("需要展示从薄弱点到专项练习的路径", "scenario", 0.86),
    ("想找一张不是普通课程而是专项训练的图", "scenario", 0.86),
    ("家长问孩子到底该先补哪类题", "pain", 0.86),
    ("孩子基础题会但难题和压轴题卡住", "pain", 0.88),
    ("考前只想抓最容易涨分的模块", "pain", 0.88),
    ("想突出题型模块化训练", "scenario", 0.84),
    ("想突出重难点不是平均用力", "scenario", 0.84),
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
        by_phrase = {phrase.phrase: phrase for phrase in concept.search_phrases}
        added = 0
        updated = 0
        for phrase, phrase_type, weight in CURATED_PHRASES:
            if phrase in existing:
                current = by_phrase[phrase]
                if (
                    current.review_status != "accepted"
                    or current.phrase_type != phrase_type
                    or current.weight != weight
                ):
                    updated += 1
                    if not dry_run:
                        current.review_status = "accepted"
                        current.phrase_type = phrase_type
                        current.weight = weight
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

        if not dry_run and (added or updated or rejected):
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
        return rejected, added + updated, accepted_after


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
    parser = argparse.ArgumentParser(description="Curate focused_excellence phrases.")
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
