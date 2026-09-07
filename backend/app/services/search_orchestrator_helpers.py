from __future__ import annotations

import time

from app.core.errors import AppError
from app.domain.search_query_expansion import ExpandedQuery
from app.schemas.image import SearchResponse
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_context import merge_concept_matches
from app.services.search_diagnostics_service import SearchDiagnosticsService
from app.services.search_models import (
    SearchBranchDiagnostic,
    SearchDeadline,
    SearchHit,
)
from app.services.search_ranking_service import SearchRankingService
from app.services.search_result_recommendation_service import (
    SearchResultRecommendationService,
)


def explicit_or_local_understanding(
    query_understanding: QueryUnderstandingService,
    keyword: str,
    concept_code: str | None,
    proof_point_code: str | None,
    evidence_point_code: str | None,
):
    if not concept_code:
        return query_understanding.understand_locally(keyword), False
    understanding = query_understanding.explicit_understanding(
        keyword,
        concept_code=concept_code,
        proof_point_code=proof_point_code,
        evidence_point_code=evidence_point_code,
    )
    if understanding is None:
        raise AppError("invalid_business_filter", "所选卖点、证明点或证据表达点已失效")
    return understanding, True


def start_external_branches(
    external_branches,
    external_query,
    keyword,
    limit,
    understanding,
    *,
    deadline: SearchDeadline,
):
    return (
        external_branches.start_meilisearch(
            external_query,
            limit,
            understanding,
            deadline=deadline,
        ),
        external_branches.start_embedding(
            keyword,
            understanding,
            deadline=deadline,
        ),
        external_branches.start_understanding(
            keyword,
            understanding,
            deadline=deadline,
        ),
    )


def database_hits(
    database_recall: DatabaseSearchRecallService,
    expansion: QueryExpansionService,
    keyword: str,
    limit: int,
    candidate_limit: int,
    extra_queries: list[ExpandedQuery],
) -> list[SearchHit]:
    return database_recall.search_queries(
        expansion.database_queries(keyword, extra_queries),
        limit=max(limit * 3, candidate_limit),
    )


def concept_queries(matches) -> list[ExpandedQuery]:
    return [
        ExpandedQuery(term=item.name, score=item.score, reasons=item.reasons)
        for item in matches
    ]


def concept_hits(
    concept_recall: ConceptSearchRecallService,
    matches,
    limit: int,
    candidate_limit: int,
) -> list[SearchHit]:
    return concept_recall.recall(matches, limit=max(limit * 3, candidate_limit))


def merge_added_concept_hits(
    *,
    concept_matches,
    concept_hits_value: list[SearchHit],
    added_matches,
    concept_recall: ConceptSearchRecallService,
    ranking: SearchRankingService,
    limit: int,
    candidate_limit: int,
):
    if not added_matches:
        return concept_matches, concept_hits_value
    return (
        merge_concept_matches(concept_matches, added_matches),
        ranking.merge_hits(
            concept_hits_value,
            concept_hits(concept_recall, added_matches, limit, candidate_limit),
        ),
    )


def confirmed_route(ranking: SearchRankingService, hits, concept_matches, keyword, understanding):
    route = ranking.route_confirmed_concepts(
        hits,
        concept_matches,
        keyword=keyword,
        understanding=understanding,
    )
    return route.hits, list(route.active_matches)


def diagnostics_for_sources(
    concept: SearchBranchDiagnostic,
    database: SearchBranchDiagnostic,
    meili,
    embedding,
    understanding,
) -> list[SearchBranchDiagnostic]:
    return [
        concept,
        database,
        meili.diagnostic,
        embedding.diagnostic,
        understanding.diagnostic,
    ]


def elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))


async def finalize_search_response(
    *,
    keyword: str,
    limit: int,
    hits: list[SearchHit],
    meili_hits: list[SearchHit],
    active_concept_matches,
    understanding,
    ranking: SearchRankingService,
    result_recommendation: SearchResultRecommendationService,
    diagnostics: SearchDiagnosticsService,
    branch_diagnostics: list[SearchBranchDiagnostic],
    reranker_used: bool,
    total_timed_out: bool,
    started: float,
    deadline: SearchDeadline,
) -> SearchResponse:
    if deadline.expired:
        branch_diagnostics.append(
            SearchBranchDiagnostic(
                source="search_deadline",
                status="timed_out",
                duration_ms=0,
                detail="搜索总时间预算已用尽，保留当前已完成结果",
            )
        )
    response = ranking.build_response(
        keyword=keyword,
        hits=hits[:limit],
        search_mode="meilisearch" if meili_hits else "fuzzy",
        fallback=False,
        search_understanding=understanding,
        query_concept_matches=active_concept_matches,
    )
    route_explanation = await result_recommendation.explain_route(
        keyword=keyword,
        understanding=understanding,
        result_count=len(response.results),
        deadline=deadline,
    )
    branch_diagnostics.append(route_explanation.diagnostic)
    if route_explanation.value:
        response.route_explanation = route_explanation.value

    search_diagnostics = diagnostics.build(
        total_duration_ms=elapsed_ms(started),
        branches=branch_diagnostics,
        reranker_used=reranker_used,
        total_timed_out=total_timed_out,
    )
    fallback_reason = diagnostics.user_fallback_reason(
        branch_diagnostics,
        trusted_business_route=bool(active_concept_matches),
    )
    response.fallback = fallback_reason is not None
    response.fallback_reason = fallback_reason
    response.search_diagnostics = search_diagnostics
    return response
