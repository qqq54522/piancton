from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.asset import AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept

CONCEPT_CODE = "expert_planning"

CURATED_PHRASES: tuple[tuple[str, float], ...] = (
    ("专家背书", 1.2),
    ("权威专家背书", 1.15),
    ("专家团队背书", 1.15),
    ("教研专家背书", 1.12),
    ("多位专家共同背书", 1.1),
    ("课程专家背书", 1.08),
    ("命题专家背书", 1.08),
    ("教材专家背书", 1.08),
    ("专家共同打磨课程", 1.08),
    ("专家团队打磨课程", 1.08),
    ("能体现我们背书的图", 1.12),
    ("能体现我们这个背书的图", 1.14),
    ("体现专家背书的素材", 1.12),
    ("我们的专家背书", 1.1),
    ("专家阵容背书", 1.1),
    ("专业团队背书", 1.06),
)


def target_groups(db) -> list[AssetGroup]:
    concept = db.scalar(
        select(BusinessConcept).where(BusinessConcept.code == CONCEPT_CODE)
    )
    if concept is None:
        raise RuntimeError(f"Missing concept: {CONCEPT_CODE}")

    groups = db.scalars(
        select(AssetGroup)
        .options(
            selectinload(AssetGroup.concept_links),
            selectinload(AssetGroup.search_phrases),
        )
        .where(
            AssetGroup.approval_status == "approved",
            AssetGroup.publish_status == "published",
        )
        .order_by(AssetGroup.created_at.desc())
    ).unique()
    result: list[AssetGroup] = []
    for group in groups:
        if group.title.startswith("测试占位"):
            continue
        has_expert_link = any(
            link.concept_id == concept.id
            and link.relation_role == "expresses"
            and link.review_status == "accepted"
            for link in group.concept_links
        )
        if has_expert_link:
            result.append(group)
    return result


def boost(dry_run: bool) -> tuple[int, int, list[str]]:
    with SessionLocal() as db:
        groups = target_groups(db)
        added = 0
        touched: list[str] = []
        for group in groups:
            existing = {
                (phrase.phrase, phrase.origin)
                for phrase in group.search_phrases
            }
            group_added = 0
            for phrase, weight in CURATED_PHRASES:
                if (phrase, "manual") in existing:
                    continue
                group_added += 1
                added += 1
                if dry_run:
                    continue
                db.add(
                    AssetSearchPhrase(
                        asset_group_id=group.id,
                        phrase=phrase,
                        origin="manual",
                        review_status="accepted",
                        weight=weight,
                    )
                )
            if group_added:
                touched.append(f"{group.title} ({group.id}) +{group_added}")
        if not dry_run and added:
            db.commit()
        return len(groups), added, touched


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add expert-backing asset phrases to real expert-planning assets."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    count, added, touched = boost(args.dry_run)
    mode = "would add" if args.dry_run else "added"
    print(f"matched {count} expert asset groups; {mode} {added} phrases")
    for line in touched:
        print(line)


if __name__ == "__main__":
    main()
