from __future__ import annotations

from dataclasses import dataclass

from app.domain.taxonomy_catalog import TaxonomyNode, load_taxonomy_catalog


@dataclass(frozen=True)
class ExpandedQuery:
    term: str
    score: float | None = None
    reasons: tuple[str, ...] = ()


def expand_search_queries(keyword: str) -> list[ExpandedQuery]:
    cleaned = keyword.strip()
    if not cleaned:
        return []

    expanded: list[ExpandedQuery] = [ExpandedQuery(cleaned)]
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code

    for node in catalog.nodes:
        if not _query_matches_taxonomy_node(cleaned, node):
            continue
        expanded.extend(_expanded_queries_for_node(node, node_by_code))

    for point in catalog.copy_points:
        if not _query_matches_terms(cleaned, [point.name, point.code]):
            continue
        system = node_by_code.get(point.system_code)
        if system:
            expanded.extend(_expanded_queries_for_node(system, node_by_code))
        for target_code in point.target_label_codes:
            target = node_by_code.get(target_code)
            if target:
                expanded.extend(_expanded_queries_for_node(target, node_by_code))

    unique: list[ExpandedQuery] = []
    seen: set[str] = set()
    for query in expanded:
        term = query.term.strip()
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(ExpandedQuery(term=term, score=query.score, reasons=query.reasons))
    return unique


def expand_search_terms(keyword: str) -> list[str]:
    return [query.term for query in expand_search_queries(keyword)]


def _expanded_queries_for_node(
    node: TaxonomyNode,
    node_by_code: dict[str, TaxonomyNode],
) -> list[ExpandedQuery]:
    terms = [node.name, node.code, *node.aliases]
    if node.parent_code and node.parent_code in node_by_code:
        parent = node_by_code[node.parent_code]
        terms.extend([parent.name, f"{parent.name} > {node.name}"])
    reason = f"语义扩展匹配：{node.name}"
    score = 0.82 if node.node_type == "image_label" else 0.74
    return [ExpandedQuery(term=term, score=score, reasons=(reason,)) for term in terms]


def _query_matches_taxonomy_node(keyword: str, node: TaxonomyNode) -> bool:
    terms = [
        node.name,
        node.code,
        *node.aliases,
        *node.positive_evidence,
    ]
    return _query_matches_terms(keyword, terms)


def _query_matches_terms(keyword: str, terms: list[str]) -> bool:
    needle = _normalize_query_text(keyword)
    if not needle:
        return False
    for term in terms:
        normalized = _normalize_query_text(term)
        if len(normalized) < 2:
            continue
        if normalized in needle:
            return True
        if len(needle) >= 4 and needle in normalized:
            return True
    return False


def _normalize_query_text(value: str) -> str:
    return "".join(value.lower().split())
