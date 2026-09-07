from __future__ import annotations

import time

from app.schemas.image import SearchResponse
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_profile_service import QueryProfileService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_context import (
    matches_from_understanding,
    merge_concept_matches,
)
from app.services.search_diagnostics_service import SearchDiagnosticsService
from app.services.search_external_branches import SearchExternalBranches
from app.services.search_models import (
    SearchBranchDiagnostic,
    SearchBranchResult,
    SearchDeadline,
)
from app.services.search_orchestrator_helpers import (
    concept_hits as recall_concept_hits,
)
from app.services.search_orchestrator_helpers import (
    concept_queries,
    confirmed_route,
    diagnostics_for_sources,
    elapsed_ms,
    explicit_or_local_understanding,
    finalize_search_response,
    start_external_branches,
)
from app.services.search_orchestrator_helpers import (
    database_hits as recall_database_hits,
)
from app.services.search_query_context_resolver import SearchQueryContextResolver
from app.services.search_ranking_service import SearchRankingService
from app.services.search_rerank_coordinator import SearchRerankCoordinator
from app.services.search_result_recommendation_service import (
    SearchResultRecommendationService,
)
from app.services.search_system_filter import SearchSystemFilter


class AsyncSearchOrchestrator:
    """Phase 4 deadline-aware coordinator; recall services keep source ownership."""

    def __init__(
        self,
        *,
        expansion: QueryExpansionService,
        query_understanding: QueryUnderstandingService,
        query_profile: QueryProfileService,
        concept_recall: ConceptSearchRecallService,
        database_recall: DatabaseSearchRecallService,
        ranking: SearchRankingService,
        external_branches: SearchExternalBranches,
        rerank_coordinator: SearchRerankCoordinator,
        result_recommendation: SearchResultRecommendationService,
        system_filter: SearchSystemFilter,
        candidate_limit: int,
        total_timeout_seconds: float,
    ):
        self.expansion = expansion
        self.query_understanding = query_understanding
        self.query_profile = query_profile
        self.concept_recall = concept_recall
        self.database_recall = database_recall
        self.ranking = ranking
        self.external_branches = external_branches
        self.rerank_coordinator = rerank_coordinator
        self.result_recommendation = result_recommendation
        self.system_filter = system_filter
        self.candidate_limit = max(1, candidate_limit)
        self.total_timeout_seconds = max(0.1, total_timeout_seconds)
        self.diagnostics = SearchDiagnosticsService()
        self.query_context = SearchQueryContextResolver(
            expansion=expansion,
            query_understanding=query_understanding,
            query_profile=query_profile,
            concept_recall=concept_recall,
            database_recall=database_recall,
            external_branches=external_branches,
            ranking=ranking,
            candidate_limit=self.candidate_limit,
        )

    async def search(
        self,
        keyword: str,
        limit: int,
        system_code: str | None = None,
        concept_code: str | None = None,
        proof_point_code: str | None = None,
        evidence_point_code: str | None = None,
    ) -> SearchResponse:
        started = time.monotonic()
        deadline = SearchDeadline.from_timeout(self.total_timeout_seconds)
        local_understanding, explicit_filter = explicit_or_local_understanding(
            self.query_understanding,
            keyword,
            concept_code,
            proof_point_code,
            evidence_point_code,
        )
        local_expansions = self.expansion.queries_from_understanding(local_understanding)
        external_query = self.expansion.external_keyword(keyword, local_expansions)
        pure_vikingdb_route = (
            self.external_branches.pure_vikingdb_knowledge_mode
            and not explicit_filter
            and not system_code
        )

        meili_task, embedding_branch, understanding_branch = start_external_branches(
            self.external_branches,
            external_query,
            keyword,
            limit,
            local_understanding,
            deadline=deadline,
        )
        embedding_result, embedding_task = embedding_branch
        understanding_result, understanding_task = understanding_branch

        concept_started = time.monotonic()
        understanding_matches = matches_from_understanding(
            local_understanding,
            self.concept_recall,
        )
        if pure_vikingdb_route:
            concept_matches = []
            concept_hits = []
        else:
            concept_matches = (
                understanding_matches
                if explicit_filter
                else merge_concept_matches(
                    self.concept_recall.match(keyword),
                    understanding_matches,
                )
            )
            concept_hits = recall_concept_hits(
                self.concept_recall, concept_matches, limit, self.candidate_limit
            )
        concept_diagnostic = SearchBranchDiagnostic(
            source="local_concepts",
            status="skipped" if pure_vikingdb_route else "ok",
            duration_ms=elapsed_ms(concept_started),
            result_count=len(concept_hits),
            detail=(
                "火山知识路由测试模式下关闭本地公共话术召回"
                if pure_vikingdb_route
                else None
            ),
        )

        database_started = time.monotonic()
        database_hits = (
            []
            if pure_vikingdb_route
            else recall_database_hits(
                self.database_recall,
                self.expansion,
                keyword,
                limit,
                self.candidate_limit,
                [*local_expansions, *concept_queries(concept_matches)],
            )
        )

        meili_result = await meili_task
        if embedding_task is not None:
            embedding_result = await embedding_task
        if understanding_task is not None:
            understanding_result = await understanding_task
        assert embedding_result is not None
        assert understanding_result is not None

        context = self.query_context.resolve(
            keyword=keyword,
            local_understanding=local_understanding,
            understanding_result=understanding_result,
            explicit_filter=explicit_filter,
            concept_matches=concept_matches,
            concept_hits_value=concept_hits,
            database_hits_value=database_hits,
            limit=limit,
            pure_vikingdb_required=pure_vikingdb_route,
        )
        understanding = context.understanding
        concept_matches = context.concept_matches
        concept_hits = context.concept_hits
        database_hits = context.database_hits
        precision_lock = context.precision_lock

        database_diagnostic = SearchBranchDiagnostic(
            source="database",
            status="skipped" if pure_vikingdb_route else "ok",
            duration_ms=elapsed_ms(database_started),
            result_count=len(database_hits),
            detail=(
                "火山知识路由测试模式下等待卖点命中后再取图库"
                if pure_vikingdb_route
                else None
            ),
        )
        meili_hits = self.external_branches.hydrate_meilisearch(meili_result)
        meili_result = self.external_branches.with_result_count(
            meili_result,
            len(meili_hits),
        )
        embedding_hits = self.external_branches.hydrate_embedding(
            embedding_result,
            limit=limit,
            keyword=keyword,
        )
        embedding_result = self.external_branches.with_result_count(
            embedding_result,
            len(embedding_hits),
        )

        hits = self.ranking.fuse_sources(
            [concept_hits, database_hits, meili_hits, embedding_hits]
        )
        hits, active_concept_matches = confirmed_route(
            self.ranking, hits, concept_matches, keyword, understanding
        )
        if precision_lock and not active_concept_matches:
            # 第一层已经确认这是业务查询，但第二层没有在预算内完成。
            # 此时绝不能把全库 Meili/Embedding 候选冒充成卖点结果。
            hits = []
        hits = self.system_filter.apply(hits, system_code)
        hits = self.ranking.collapse_asset_groups(hits)
        hits = hits[: max(limit, self.candidate_limit)]

        branch_diagnostics = diagnostics_for_sources(
            concept_diagnostic,
            database_diagnostic,
            meili_result,
            embedding_result,
            understanding_result,
        )
        optional_rerank_started = time.monotonic()
        (
            hits,
            reranker_diagnostic,
            reranker_used,
            total_timed_out,
        ) = await self.rerank_coordinator.rerank(
            keyword,
            hits,
            search_started=optional_rerank_started,
            deadline=deadline,
            trusted_business_route=bool(active_concept_matches),
        )
        hits, active_concept_matches = confirmed_route(
            self.ranking, hits, concept_matches, keyword, understanding
        )
        branch_diagnostics.append(reranker_diagnostic)

        vikingdb_route = _is_vikingdb_knowledge_result(
            understanding_result
        ) or _is_vikingdb_knowledge_route(understanding)
        if vikingdb_route:
            candidate_review_result = SearchBranchResult(
                value=hits,
                diagnostic=SearchBranchDiagnostic(
                    source="candidate_review",
                    status="skipped",
                    duration_ms=0,
                    result_count=len(hits),
                    detail="VikingDB 已完成卖点路由，直接返回本地 accepted 素材",
                ),
            )
        else:
            candidate_review_result = await self.external_branches.review_candidates(
                keyword=keyword,
                understanding=understanding,
                hits=hits[: max(limit, self.candidate_limit)],
                limit=limit,
                deadline=deadline,
            )
        if candidate_review_result.value is not None:
            hits = candidate_review_result.value
            hits, active_concept_matches = confirmed_route(
                self.ranking, hits, concept_matches, keyword, understanding
            )
        branch_diagnostics.append(candidate_review_result.diagnostic)

        return await finalize_search_response(keyword=keyword,
            limit=limit,
            hits=hits,
            meili_hits=meili_hits,
            active_concept_matches=active_concept_matches,
            understanding=understanding,
            ranking=self.ranking,
            result_recommendation=self.result_recommendation,
            diagnostics=self.diagnostics,
            branch_diagnostics=branch_diagnostics,
            reranker_used=reranker_used,
            total_timed_out=total_timed_out,
            started=started,
            deadline=deadline,
        )


def _is_vikingdb_knowledge_route(understanding) -> bool:
    return bool(
        understanding
        and "VikingDB" in (understanding.search_strategy or "")
    )


def _is_vikingdb_knowledge_result(result: SearchBranchResult) -> bool:
    return (
        result.diagnostic.source == "vikingdb_knowledge_router"
        and result.diagnostic.status == "ok"
    )
