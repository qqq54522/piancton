from collections import defaultdict

from sqlalchemy import or_, select

from app.db.session import SessionLocal
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.image import ImageBusinessLabel, ImageCategory, ImageTag
from app.models.tag import Tag


def seed_taxonomy() -> tuple[int, int, int]:
    catalog = load_taxonomy_catalog()
    created = 0
    updated = 0
    with SessionLocal() as db:
        tag_by_code: dict[str, Tag] = {
            tag.code: tag
            for tag in db.scalars(select(Tag).where(Tag.code.is_not(None))).all()
            if tag.code
        }
        parent_by_code: dict[str, Tag] = {}

        for sort_order, node in enumerate(catalog.nodes):
            parent = parent_by_code.get(node.parent_code) if node.parent_code else None
            tag = tag_by_code.get(node.code)
            if tag is None:
                query = select(Tag).where(Tag.name == node.name)
                query = (
                    query.where(Tag.parent_id == parent.id)
                    if parent
                    else query.where(Tag.parent_id.is_(None))
                )
                tag = db.scalar(query)
            values = {
                "code": node.code,
                "name": node.name,
                "color": node.color,
                "parent_id": parent.id if parent else None,
                "is_secondary": parent is not None,
                "node_type": node.node_type,
                "assignable": node.assignable,
                "status": "active",
                "taxonomy_version": catalog.version,
                "sort_order": sort_order,
            }
            if tag is None:
                tag = Tag(**values)
                db.add(tag)
                db.flush()
                created += 1
            else:
                changed = False
                for key, value in values.items():
                    if getattr(tag, key) != value:
                        setattr(tag, key, value)
                        changed = True
                if changed:
                    updated += 1
            tag_by_code[node.code] = tag
            parent_by_code[node.code] = tag
        db.flush()
        backfilled = backfill_manual_business_labels(db)
        category_backfilled = backfill_legacy_image_categories(db)
        db.commit()
    return created, updated, backfilled, category_backfilled


def backfill_manual_business_labels(db) -> int:
    invalid_labels = list(
        db.scalars(
            select(ImageBusinessLabel)
            .join(Tag, Tag.id == ImageBusinessLabel.tag_id)
            .where(
                ImageBusinessLabel.origin == "manual",
                or_(
                    Tag.assignable.is_(False),
                    Tag.status != "active",
                    Tag.node_type == "system",
                ),
            )
        ).all()
    )
    for label in invalid_labels:
        db.delete(label)
    db.flush()

    existing_labels = {
        (label.image_id, label.tag_id): label
        for label in db.scalars(
            select(ImageBusinessLabel).where(ImageBusinessLabel.origin == "manual")
        ).all()
    }
    primary_images = {
        label.image_id
        for label in existing_labels.values()
        if label.role == "primary"
    }
    rows = db.execute(
        select(
            ImageTag.image_id,
            ImageTag.tag_id,
            Tag.code,
            Tag.sort_order,
            Tag.name,
        )
        .join(Tag, Tag.id == ImageTag.tag_id)
        .where(
            Tag.assignable.is_(True),
            Tag.status == "active",
            Tag.node_type != "system",
        )
        .order_by(ImageTag.image_id, Tag.sort_order, Tag.name, Tag.id)
    ).all()
    rows_by_image: dict[str, list] = defaultdict(list)
    for row in rows:
        rows_by_image[row.image_id].append(row)

    backfilled = 0
    for image_id, image_rows in rows_by_image.items():
        for row in image_rows:
            label_code = row.code or row.tag_id
            existing_label = existing_labels.get((row.image_id, row.tag_id))
            if existing_label:
                if existing_label.label_code != label_code:
                    existing_label.label_code = label_code
                continue
            role = "primary" if image_id not in primary_images else "additional"
            if role == "primary":
                primary_images.add(image_id)
            label = ImageBusinessLabel(
                image_id=image_id,
                tag_id=row.tag_id,
                label_code=label_code,
                origin="manual",
                role=role,
                review_status="accepted",
                confidence=1.0,
            )
            db.add(label)
            existing_labels[(row.image_id, row.tag_id)] = label
            backfilled += 1
    db.flush()
    return backfilled


def backfill_legacy_image_categories(db) -> int:
    """Give legacy tagged images a default precise-filter category.

    Older deployments allowed images to keep manual/business labels while having
    no scene/function category. The precise finder combines selected tags with
    the category filter, so those otherwise valid assets disappeared when users
    chose "功能". New uploads already write categories explicitly; this backfill
    only touches images that have search labels but no category rows.
    """

    image_ids_with_categories = set(db.scalars(select(ImageCategory.image_id)).all())
    tagged_image_ids = set(
        db.scalars(
            select(ImageTag.image_id)
            .join(Tag, Tag.id == ImageTag.tag_id)
            .where(
                Tag.assignable.is_(True),
                Tag.status == "active",
                Tag.node_type != "system",
            )
        ).all()
    )
    business_labeled_image_ids = set(
        db.scalars(
            select(ImageBusinessLabel.image_id)
            .where(ImageBusinessLabel.review_status != "rejected")
        ).all()
    )
    candidate_ids = sorted(
        (tagged_image_ids | business_labeled_image_ids) - image_ids_with_categories
    )
    for image_id in candidate_ids:
        db.add(ImageCategory(image_id=image_id, name="function"))
    db.flush()
    return len(candidate_ids)


def main() -> None:
    created, updated, backfilled, category_backfilled = seed_taxonomy()
    print(
        "Seeded taxonomy: "
        f"created={created}, updated={updated}, "
        f"manual_business_labels={backfilled}, "
        f"legacy_image_categories={category_backfilled}"
    )


if __name__ == "__main__":
    main()
