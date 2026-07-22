from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.knowledge import AiKnowledge
from app.domain.taxonomy_catalog import TaxonomyNode, load_taxonomy_catalog
from app.models.business_concept import BusinessConcept
from app.repositories.business_concept_repository import BusinessConceptRepository


class AiKnowledgeService:
    """Builds the AI knowledge context from currently enabled selling points (D027).

    The static taxonomy file stays as seed material: it still contributes
    aliases and positive/negative evidence, but names, definitions, enabled
    status and newly created concepts follow the database.
    """

    def __init__(self, db: Session):
        self.concepts = BusinessConceptRepository(db)

    def knowledge(self) -> AiKnowledge | None:
        try:
            rows = self.concepts.list(include_inactive=True)
        except Exception:  # noqa: BLE001 - 数据库不可用时保持静态目录兜底
            return None
        if not rows:
            return None
        return _build_knowledge(rows)


def _build_knowledge(rows: list[BusinessConcept]) -> AiKnowledge:
    catalog = load_taxonomy_catalog()
    by_code = {row.code: row for row in rows}

    codes: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    display_names: dict[str, str] = {}
    prompt_contexts: dict[str, str] = {}
    system_codes_by_concept: dict[str, tuple[str, ...]] = {}
    lines = ["# 当前启用卖点目录（来自数据库，D027 运行事实来源）"]
    handled_codes: set[str] = set()

    for system in catalog.system_nodes:
        section: list[str] = []
        for label in catalog.children_of(system.code):
            concept = by_code.get(label.code)
            if concept is not None:
                handled_codes.add(concept.code)
                # 数据库已停用/合并的卖点不再进入任何识别链路。
                if concept.status != "active":
                    continue
                rendered = _render_concept(concept, static_node=label)
                section.extend(rendered)
                prompt_contexts[concept.code] = "\n".join(rendered)
                linked_system_codes = tuple(
                    dict.fromkeys(
                        link.system_tag.code
                        for link in concept.system_links
                        if link.status == "active" and link.system_tag is not None
                    )
                )
                system_codes_by_concept[concept.code] = (
                    linked_system_codes or (system.code,)
                )
                codes.add(concept.code)
                display_names[concept.code] = _concept_display_name(
                    concept,
                    fallback_system_name=system.name,
                )
                pairs.add((system.name, concept.name.strip()))
                pairs.update(
                    (link.system_tag.name, concept.name.strip())
                    for link in concept.system_links
                    if link.status == "active" and link.system_tag is not None
                )
                continue
            # 数据库尚未收录时保留静态种子定义。
            rendered = _render_static_label(label)
            section.extend(rendered)
            prompt_contexts[label.code] = "\n".join(rendered)
            system_codes_by_concept[label.code] = (system.code,)
            codes.add(label.code)
            display_names[label.code] = f"{system.name} > {label.name}"
            pairs.add((system.name, label.name))
        if section:
            lines.append(f"\n## {system.code} / {system.name}")
            lines.append(system.definition)
            lines.extend(section)

    extra = [
        row
        for row in rows
        if row.code not in handled_codes and row.status == "active"
    ]
    if extra:
        lines.append("\n## 新增卖点（后台维护，静态目录之外）")
        for concept in extra:
            rendered = _render_concept(concept, static_node=None)
            lines.extend(rendered)
            prompt_contexts[concept.code] = "\n".join(rendered)
            system_codes_by_concept[concept.code] = tuple(
                dict.fromkeys(
                    link.system_tag.code
                    for link in concept.system_links
                    if link.status == "active" and link.system_tag is not None
                )
            )
            codes.add(concept.code)
            display_names[concept.code] = _concept_display_name(concept)
            for link in concept.system_links:
                if link.status == "active" and link.system_tag is not None:
                    pairs.add((link.system_tag.name, concept.name.strip()))
            pairs.add(("", concept.name.strip()))

    lines.append("\n模型只能返回以上目录中存在的稳定 code，不得创造新的业务标签。")
    return AiKnowledge(
        catalog_text="\n".join(lines),
        concept_codes=frozenset(codes),
        concept_pairs=frozenset(pairs),
        concept_display_names=tuple(sorted(display_names.items())),
        concept_prompt_contexts=tuple(sorted(prompt_contexts.items())),
        concept_system_codes=tuple(sorted(system_codes_by_concept.items())),
    )


def _render_concept(
    concept: BusinessConcept,
    *,
    static_node: TaxonomyNode | None,
) -> list[str]:
    name = concept.name.strip() or concept.code
    definition = (concept.definition or "").strip() or (
        static_node.definition if static_node else ""
    )
    lines = [f"- `{concept.code}` / {name}: {definition}"]
    rejected = {
        _normalize_phrase(item.phrase)
        for item in concept.search_phrases
        if item.review_status == "rejected" and item.phrase.strip()
    }
    manual_phrases = [
        item.phrase.strip()
        for item in concept.search_phrases
        if item.review_status == "accepted"
        and item.origin not in {"source_document", "migrated"}
        and item.phrase.strip()
        and _normalize_phrase(item.phrase) not in rejected
    ]
    seeded_phrases = [
        item.phrase.strip()
        for item in concept.search_phrases
        if item.review_status == "accepted"
        and item.origin in {"source_document", "migrated"}
        and item.phrase.strip()
        and _normalize_phrase(item.phrase) not in rejected
    ]
    aliases = [
        alias
        for alias in (static_node.aliases if static_node else [])
        if _normalize_phrase(alias) not in rejected
    ]
    expressions = list(
        dict.fromkeys([*manual_phrases, *aliases, *seeded_phrases])
    )[:12]
    if expressions:
        lines.append(f"  - 常见表达：{'、'.join(expressions)}")
    positive_evidence = [
        item
        for item in (static_node.positive_evidence if static_node else [])
        if _normalize_phrase(item) not in rejected
    ]
    negative_evidence = [
        item
        for item in (static_node.negative_evidence if static_node else [])
        if _normalize_phrase(item) not in rejected
    ]
    if positive_evidence:
        lines.append(f"  - 正向证据：{'、'.join(positive_evidence)}")
    if negative_evidence:
        lines.append(f"  - 排除边界：{'、'.join(negative_evidence)}")
    return lines


def _render_static_label(label: TaxonomyNode) -> list[str]:
    lines = [f"- `{label.code}` / {label.name}: {label.definition}"]
    if label.aliases:
        lines.append(f"  - 常见表达：{'、'.join(label.aliases)}")
    if label.positive_evidence:
        lines.append(f"  - 正向证据：{'、'.join(label.positive_evidence)}")
    if label.negative_evidence:
        lines.append(f"  - 排除边界：{'、'.join(label.negative_evidence)}")
    return lines


def _normalize_phrase(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


def _concept_display_name(
    concept: BusinessConcept,
    *,
    fallback_system_name: str = "",
) -> str:
    system_name = next(
        (
            link.system_tag.name.strip()
            for link in concept.system_links
            if link.status == "active" and link.system_tag is not None
        ),
        fallback_system_name,
    )
    name = concept.name.strip() or concept.code
    return f"{system_name} > {name}" if system_name else name
