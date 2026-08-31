from __future__ import annotations

import argparse

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase, utcnow

CONCEPT_CODE = "stage_transition"
SOURCE_REF = "stage_transition_curation_20260830"

# These words are useful in full phrases, but alone they can mean curriculum,
# planning, exam difficulty or generic adaptation. Keep explicit stage phrases
# such as "小升初衔接", "升学过渡" and "新学段适应慢" accepted.
BROAD_PHRASES_TO_REJECT = {
    "升学",
    "学段",
    "衔接",
    "路径",
    "过渡",
    "适应",
    "难度",
    "难度突然变大",
}

CURATED_PHRASES: list[tuple[str, str, float]] = [
    ("小初高一体化与学段衔接", "official", 1.0),
    ("关键升学阶段衔接课程", "official", 1.0),
    ("小升初初升高过渡课程", "official", 0.98),
    ("从小学到高中连续培养", "official", 0.98),
    ("新学段知识断层衔接", "official", 0.98),
    ("小升初暑期衔接课", "alias", 0.94),
    ("初升高暑期衔接课", "alias", 0.94),
    ("升初中前提前适应", "alias", 0.92),
    ("升高中前提前适应", "alias", 0.92),
    ("小学到初中平稳过渡", "alias", 0.94),
    ("初中到高中平稳过渡", "alias", 0.94),
    ("小升初知识断层怎么补", "alias", 0.94),
    ("初升高知识断层怎么补", "alias", 0.94),
    ("新学段学习方式适应", "alias", 0.92),
    ("新学段节奏提前适应", "alias", 0.92),
    ("升学后课程难度接不上", "pain", 0.92),
    ("升学后学习节奏跟不上", "pain", 0.92),
    ("衔接期专门课程", "alias", 0.9),
    ("过渡期专门课程", "alias", 0.9),
    ("学段过渡不掉队", "alias", 0.9),
    ("提前补齐新学段基础", "alias", 0.9),
    ("提前熟悉初中学习方式", "alias", 0.9),
    ("提前熟悉高中学习节奏", "alias", 0.9),
    ("小升初不想一开学就掉队", "pain", 0.9),
    ("初升高不想一开学就掉队", "pain", 0.9),
    ("小学成绩好升初中后怕掉下来", "pain", 0.88),
    ("初中成绩好升高中后怕掉下来", "pain", 0.88),
    ("以前第一名升学后变中游", "pain", 0.9),
    ("孩子新学段适应慢", "pain", 0.9),
    ("孩子刚进初中有点吃力", "pain", 0.9),
    ("孩子刚进高中压力变大", "pain", 0.88),
    ("孩子升学后自信心受挫", "pain", 0.88),
    ("怕孩子跨学段跟不上", "pain", 0.9),
    ("怕新学段知识坡度太陡", "pain", 0.9),
    ("从小学到初中学习方法要换", "pain", 0.88),
    ("从初中到高中思维难度跃迁", "pain", 0.88),
    ("六年级暑假提前衔接初中", "scenario", 0.9),
    ("初三暑假提前衔接高中", "scenario", 0.9),
    ("升学前补知识空白", "scenario", 0.88),
    ("新初一入学前衔接", "scenario", 0.9),
    ("新高一入学前衔接", "scenario", 0.9),
    ("小升初家长想找过渡课素材", "scenario", 0.86),
    ("初升高家长想找衔接课素材", "scenario", 0.86),
    ("想找表达平稳跨过新学段的图", "scenario", 0.86),
    ("想找孩子升学不掉队的素材", "scenario", 0.86),
    ("想表达升学断层提前补", "scenario", 0.86),
    ("想展示小升初和初升高都有课", "scenario", 0.86),
    ("想讲衔接期不是临时补丁", "colloquial", 0.86),
    ("给家长说明升学前要提前衔接", "colloquial", 0.84),
    ("销售想讲新学段平稳过渡", "colloquial", 0.84),
    ("汇报里突出学段衔接能力", "scenario", 0.84),
    ("小初高连续课程体系", "alias", 0.94),
    ("小学初中高中一套体系", "alias", 0.92),
    ("从小学一路学到高中", "alias", 0.92),
    ("从小学到高中不用换体系", "alias", 0.92),
    ("全学段连续学习路径", "alias", 0.92),
    ("12年基础教育连续覆盖", "alias", 0.9),
    ("小初高全学段课程覆盖", "alias", 0.92),
    ("一站式覆盖小学初中高中", "alias", 0.9),
    ("长期课程体系不只看眼前", "alias", 0.88),
    ("小学为初中铺垫", "alias", 0.9),
    ("初中为高中蓄能", "alias", 0.9),
    ("低年级到高年级连续培养", "alias", 0.9),
    ("同步跟进拔高衔接一站式", "alias", 0.88),
    ("不用每个阶段重新找课程", "pain", 0.88),
    ("家长不想小升初初升高反复换体系", "pain", 0.88),
    ("想找小初高一体化路径图", "scenario", 0.86),
    ("想表达从小学到高中是一套连续培养", "scenario", 0.86),
    ("想展示全学段持续覆盖", "scenario", 0.86),
    ("给家长讲一个体系持续学到高中", "colloquial", 0.84),
    ("销售想讲小初高一体化不换体系", "colloquial", 0.84),
    ("汇报里突出从低年级到高年级全包", "scenario", 0.84),
    ("升学过渡期学习建议", "alias", 0.88),
    ("小升初按年级水平做衔接建议", "alias", 0.88),
    ("初升高按基础做衔接建议", "alias", 0.88),
    ("衔接期怎么安排学习内容", "scenario", 0.86),
    ("新学段前先知道该补什么", "scenario", 0.86),
    ("不是单独每日计划而是升学衔接安排", "colloquial", 0.84),
    ("衔接课也能兼顾同步和拔高", "alias", 0.86),
    ("升学节点同步基础和拔高都要接上", "alias", 0.86),
    ("小升初初升高都有专家设计的衔接课", "alias", 0.86),
    ("想找专家做学段衔接课程的素材", "scenario", 0.84),
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
    parser = argparse.ArgumentParser(description="Curate stage_transition phrases.")
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
