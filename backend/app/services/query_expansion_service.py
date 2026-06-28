from __future__ import annotations

from app.domain.search_query_expansion import ExpandedQuery, expand_search_queries
from app.schemas.ai import SearchUnderstanding


class QueryExpansionService:
    def database_queries(
        self,
        keyword: str,
        extra_queries: list[ExpandedQuery],
    ) -> list[ExpandedQuery]:
        unique: list[ExpandedQuery] = []
        seen: set[str] = set()
        for query in [*expand_search_queries(keyword), *extra_queries]:
            term = query.term.strip()
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(ExpandedQuery(term, query.score, query.reasons))
        return unique

    def queries_from_understanding(
        self,
        understanding: SearchUnderstanding | None,
    ) -> list[ExpandedQuery]:
        if not understanding:
            return []
        queries: list[ExpandedQuery] = []
        if understanding.normalized_query.strip():
            queries.append(
                ExpandedQuery(
                    understanding.normalized_query,
                    0.86,
                    ("AI 意图理解：标准化查询",),
                )
            )
        for item in understanding.expanded_level1_tags:
            if not item.tag.strip():
                continue
            queries.append(
                ExpandedQuery(
                    item.tag,
                    max(0.65, min(item.weight, 0.95)),
                    (f"AI 意图扩展：{item.tag}",),
                )
            )
        for item in understanding.matched_level2_categories:
            if not item.category.strip():
                continue
            queries.append(
                ExpandedQuery(
                    item.category,
                    max(0.62, min(item.weight, 0.92)),
                    (f"AI 二级标签理解：{item.category}",),
                )
            )
        return queries

    def smart_keyword(
        self,
        keyword: str,
        expanded_queries: list[ExpandedQuery],
    ) -> str:
        terms = [
            keyword,
            *(query.term for query in expand_search_queries(keyword)),
            *(query.term for query in expanded_queries),
        ]
        return " ".join(unique([term.strip() for term in terms if term.strip()]))


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
