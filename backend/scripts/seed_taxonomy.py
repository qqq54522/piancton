from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.tag import Tag
from scripts.seed_business_concepts import sync_business_concepts


def seed_taxonomy() -> tuple[int, int, tuple[int, int, int, int]]:
    catalog = load_taxonomy_catalog()
    created = 0
    updated = 0
    with SessionLocal() as db:
        tag_by_code: dict[str, Tag] = {
            tag.code: tag
            for tag in db.scalars(select(Tag).where(Tag.code.is_not(None))).all()
            if tag.code
        }
        for sort_order, node in enumerate(catalog.system_nodes):
            tag = tag_by_code.get(node.code)
            if tag is None:
                tag = db.scalar(
                    select(Tag).where(
                        Tag.name == node.name,
                        Tag.parent_id.is_(None),
                    )
                )
            values = {
                "code": node.code,
                "name": node.name,
                "color": node.color,
                "parent_id": None,
                "is_secondary": False,
                "node_type": "system",
                "assignable": False,
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
        db.flush()
        concept_seed = sync_business_concepts(db)
        db.commit()
    return created, updated, concept_seed


def main() -> None:
    created, updated, concept_seed = seed_taxonomy()
    print(
        "Seeded taxonomy: "
        f"created={created}, updated={updated}, "
        f"business_concepts={concept_seed[0]}, concept_phrases={concept_seed[2]}"
    )


if __name__ == "__main__":
    main()
