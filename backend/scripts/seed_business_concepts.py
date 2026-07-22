from __future__ import annotations

from itertools import combinations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.business_intents import load_business_intents
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.business_concept import (
    BusinessConcept,
    ConceptRelation,
    ConceptSearchPhrase,
    ConceptSystemLink,
)
from app.models.tag import Tag

# 业务已确认由其他稳定卖点承载的旧 source_document 话术。
# 保留原记录用于审计，但每次幂等同步都要维持 rejected，避免旧库或备份
# 恢复后重新覆盖 Skill 已校准的跨体系边界。
REJECTED_SOURCE_PHRASES_BY_CONCEPT = {
    "universal_method": {
        "一道题会一类题",
        "一道题学会一类题",
    },
}


def sync_business_concepts(db) -> tuple[int, int, int, int]:
    """Idempotently materialize concept seeds after taxonomy tags exist."""
    catalog = load_taxonomy_catalog()
    intents = load_business_intents()
    tags_by_code = {
        item.code: item
        for item in db.scalars(select(Tag).where(Tag.code.is_not(None))).all()
        if item.code
    }
    concepts_by_code = {
        item.code: item for item in db.scalars(select(BusinessConcept)).all()
    }
    created = updated = phrase_count = relation_count = 0

    for node in catalog.image_label_nodes:
        concept = concepts_by_code.get(node.code)
        if concept is None:
            concept = BusinessConcept(
                code=node.code,
                name=node.name,
                concept_type="business_term",
                definition=node.definition or None,
                status="active",
            )
            db.add(concept)
            db.flush()
            concepts_by_code[node.code] = concept
            created += 1
        elif not (concept.definition or "").strip() and node.definition:
            # D027：数据库是概念名称/定义的运行事实来源。种子只负责初始化，
            # 已存在的概念不再被静态文件覆盖，仅补齐仍为空的定义。
            concept.definition = node.definition
            concept.version += 1
            updated += 1

        system_tag = tags_by_code.get(node.parent_code or "")
        if system_tag and not any(
            link.system_tag is system_tag or link.system_tag_id == system_tag.id
            for link in concept.system_links
        ):
            concept.system_links.append(
                ConceptSystemLink(
                    system_tag=system_tag,
                    role="core",
                    weight=1.0,
                    reason="由六大体系与业务概念源文件初始化",
                )
            )
        phrase_count += _add_phrases(
            concept,
            [(node.name, "official"), *((value, "alias") for value in node.aliases)],
            source_ref=f"taxonomy/catalog.json#{node.code}",
        )

    for intent in intents.intents:
        concept = concepts_by_code.get(intent.target_label_code)
        if not concept:
            continue
        phrase_count += _add_phrases(
            concept,
            [
                *((value, "official") for value in intent.phrases),
                *((value, "pain") for value in intent.pain_points),
                *((value, "alias") for value in intent.must_have_concepts),
                *((value, "outcome") for value in intent.nice_to_have_concepts),
            ],
            source_ref=f"taxonomy/business_intents.json#{intent.code}",
        )

    for point in catalog.copy_points:
        system_tag = tags_by_code.get(point.system_code)
        targets = [
            concepts_by_code[code]
            for code in point.target_label_codes
            if code in concepts_by_code
        ]
        for concept in targets:
            if system_tag and not any(
                link.system_tag is system_tag or link.system_tag_id == system_tag.id
                for link in concept.system_links
            ):
                concept.system_links.append(
                    ConceptSystemLink(
                        system_tag=system_tag,
                        role="support",
                        weight=0.7,
                        reason=f"跨体系卖点映射：{point.name}",
                    )
                )
            phrase_count += _add_phrases(
                concept,
                [(point.name, "alias")],
                source_ref=f"taxonomy/catalog.json#copy-point:{point.code}",
            )
        for left, right in combinations(targets, 2):
            relation_count += _add_relation(
                db,
                left,
                right,
                "similar_to",
                f"共享跨体系卖点：{point.name}",
            )
            relation_count += _add_relation(
                db,
                right,
                left,
                "similar_to",
                f"共享跨体系卖点：{point.name}",
            )

    # 必须放在全部静态话术合并之后执行：即使旧目录、旧备份或后续静态来源
    # 再次带回已校准的错误表达，最终运行态仍以 Skill 边界为准并保留审计记录。
    for concept in concepts_by_code.values():
        updated += _reject_deprecated_source_phrases(concept)

    db.flush()
    return created, updated, phrase_count, relation_count


def _reject_deprecated_source_phrases(concept: BusinessConcept) -> int:
    rejected_phrases = REJECTED_SOURCE_PHRASES_BY_CONCEPT.get(concept.code, set())
    changed = False
    for item in concept.search_phrases:
        if (
            item.origin == "source_document"
            and item.review_status == "accepted"
            and item.phrase in rejected_phrases
        ):
            item.review_status = "rejected"
            changed = True
    if not changed:
        return 0
    concept.version += 1
    return 1


def _add_phrases(
    concept: BusinessConcept,
    values: list[tuple[str, str]],
    *,
    source_ref: str,
) -> int:
    existing = {item.phrase for item in concept.search_phrases}
    count = 0
    for value, phrase_type in values:
        phrase = value.strip()
        if not phrase or phrase in existing:
            continue
        concept.search_phrases.append(
            ConceptSearchPhrase(
                phrase=phrase,
                phrase_type=phrase_type,
                origin="source_document",
                review_status="accepted",
                weight=1.0,
                source_ref=source_ref,
            )
        )
        existing.add(phrase)
        count += 1
    return count


def _add_relation(db, source, target, relation_type: str, reason: str) -> int:
    exists = db.scalar(
        select(ConceptRelation.id).where(
            ConceptRelation.source_concept_id == source.id,
            ConceptRelation.target_concept_id == target.id,
            ConceptRelation.relation_type == relation_type,
        )
    )
    if exists:
        return 0
    db.add(
        ConceptRelation(
            source_concept=source,
            target_concept=target,
            relation_type=relation_type,
            reason=reason,
        )
    )
    return 1


def main() -> None:
    with SessionLocal() as db:
        result = sync_business_concepts(db)
        db.commit()
    print(
        "Seeded business concepts: "
        f"created={result[0]}, updated={result[1]}, phrases={result[2]}, relations={result[3]}"
    )


if __name__ == "__main__":
    main()
