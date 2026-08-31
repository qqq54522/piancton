from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.asset import AssetGroup, AssetSearchPhrase
from app.models.business_concept import BusinessConcept

CONCEPT_CODE = "focused_excellence"

TITLE_PHRASES: tuple[tuple[tuple[str, ...], tuple[tuple[str, float], ...]], ...] = (
    (
        ("重难点", "培优"),
        (
            ("训练拔高", 1.2),
            ("想训练拔高的图", 1.2),
            ("找训练拔高的素材", 1.16),
            ("想找训练拔高素材", 1.16),
            ("能体现训练拔高的图", 1.16),
            ("给高分孩子训练拔高", 1.12),
            ("高阶难题训练拔高", 1.12),
            ("重难点训练拔高", 1.12),
        ),
    ),
    (
        ("专项突破", "考前专项"),
        (
            ("题型突破", 1.18),
            ("找题型突破的图", 1.14),
            ("想找题型突破素材", 1.14),
            ("能体现题型突破的图", 1.14),
            ("按题型做专项突破", 1.12),
            ("薄弱题型突破素材", 1.12),
        ),
    ),
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
        has_focused_link = any(
            link.concept_id == concept.id
            and link.relation_role == "expresses"
            and link.review_status == "accepted"
            for link in group.concept_links
        )
        if has_focused_link:
            result.append(group)
    return result


def phrases_for_title(title: str) -> tuple[tuple[str, float], ...]:
    phrases: list[tuple[str, float]] = []
    for title_terms, group_phrases in TITLE_PHRASES:
        if any(term in title for term in title_terms):
            phrases.extend(group_phrases)
    return tuple(phrases)


def boost(dry_run: bool) -> tuple[int, int, list[str]]:
    with SessionLocal() as db:
        groups = target_groups(db)
        added = 0
        touched: list[str] = []
        for group in groups:
            phrases = phrases_for_title(group.title)
            if not phrases:
                continue
            existing = {
                (phrase.phrase, phrase.origin)
                for phrase in group.search_phrases
            }
            group_added = 0
            for phrase, weight in phrases:
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
        description="Add focused-excellence asset phrases to real non-placeholder assets."
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    count, added, touched = boost(args.dry_run)
    mode = "would add" if args.dry_run else "added"
    print(f"matched {count} focused-excellence asset groups; {mode} {added} phrases")
    for line in touched:
        print(line)


if __name__ == "__main__":
    main()
