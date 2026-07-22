from __future__ import annotations

import time

from app.core.errors import AppError
from app.domain.search_query_expansion import ExpandedQuery
from app.schemas.image import SearchResponse
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_profile_service import QueryProfileService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_context import (
    matches_from_understanding,
    merge_concept_matches,
    new_concept_matches,
)
from app.services.search_diagnostics_service import SearchDiagnosticsService
from app.services.search_external_branches import SearchExternalBranches
from app.services.search_models import (
    ConceptMatch,
    SearchBranchDiagnostic,
    SearchHit,
)
from app.services.search_ranking_service import SearchRankingService
from app.services.search_rerank_coordinator import SearchRerankCoordinator
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
        system_filter: SearchSystemFilter,
        candidate_limit: int,
    ):
        self.expansion = expansion
        self.query_understanding = query_understanding
        self.query_profile = query_profile
        self.concept_recall = concept_recall
        self.database_recall = database_recall
        self.ranking = ranking
        self.external_branches = external_branches
        self.rerank_coordinator = rerank_coordinator
        self.system_filter = system_filter
        self.candidate_limit = max(1, candidate_limit)
        self.diagnostics = SearchDiagnosticsService()

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
        explicit_understanding = None
        if concept_code:
            explicit_understanding = self.query_understanding.explicit_understanding(
                keyword,
                concept_code=concept_code,
                proof_point_code=proof_point_code,
                evidence_point_code=evidence_point_code,
            )
            if explicit_understanding is None:
                raise AppError(
                    "invalid_business_filter",
                    "所选卖点、证明点或证据表达点已失效",
                )
        local_understanding = (
            explicit_understanding
            or self.query_understanding.understand_locally(keyword)
        )
        local_expansions = self.expansion.queries_from_understanding(local_understanding)
        external_query = self.expansion.external_keyword(keyword, local_expansions)

        meili_task = self.external_branches.start_meilisearch(
            external_query,
            limit,
            local_understanding,
        )
        embedding_result, embedding_task = self.external_branches.start_embedding(
            keyword,
            local_understanding,
        )
        understanding_result, understanding_task = self.external_branches.start_understanding(
            keyword,
            local_understanding,
        )

        concept_started = time.monotonic()
        understanding_matches = matches_from_understanding(
            local_understanding,
            self.concept_recall,
        )
        concept_matches = (
            understanding_matches
            if explicit_understanding is not None
            else merge_concept_matches(
                self.concept_recall.match(keyword),
                understanding_matches,
            )
        )
        concept_hits = self.concept_recall.recall(
            concept_matches,
            limit=max(limit * 3, self.candidate_limit),
        )
        concept_diagnostic = SearchBranchDiagnostic(
            source="local_concepts",
            status="ok",
            duration_ms=_elapsed_ms(concept_started),
            result_count=len(concept_hits),
        )

        database_started = time.monotonic()
        database_hits = self._database_hits(
            keyword,
            limit,
            [*local_expansions, *self._concept_queries(concept_matches)],
        )

        meili_result = await meili_task
        if embedding_task is not None:
            embedding_result = await embedding_task
        if understanding_task is not None:
            understanding_result = await understanding_task
        assert embedding_result is not None
        assert understanding_result is not None

        understanding = self.external_branches.final_understanding(
            keyword,
            local_understanding,
            understanding_result,
        )
        model_understanding_succeeded = (
            self.external_branches.understanding_succeeded(understanding_result)
        )
        precision_lock = self.external_branches.requires_precision_lock(
            understanding_result
        )
        if understanding and understanding is not local_understanding:
            model_expansions = self.expansion.queries_from_understanding(understanding)
            database_hits = self.ranking.merge_hits(
                database_hits,
                self._database_hits(keyword, limit, model_expansions),
            )

        understood_matches = matches_from_understanding(understanding, self.concept_recall)
        if model_understanding_succeeded:
            # 模型成功只表示结构化调用完成。final_understanding 已在查询理解层
            # 完成本地强证据/模型仲裁；这里使用仲裁后的封闭卖点集合，防止相邻
            # 卖点和全局语义候选重新混入可信通道。
            concept_matches = understood_matches
            concept_hits = self.concept_recall.recall(
                concept_matches,
                limit=max(limit * 3, self.candidate_limit),
            )
        else:
            added_matches = new_concept_matches(concept_matches, understood_matches)
            if added_matches:
                concept_matches = merge_concept_matches(concept_matches, added_matches)
                concept_hits = self.ranking.merge_hits(
                    concept_hits,
                    self.concept_recall.recall(
                        added_matches,
                        limit=max(limit * 3, self.candidate_limit),
                    ),
                )

        profile = self.query_profile.build(
            keyword,
            concept_matches=concept_matches,
            understanding=understanding,
        )
        if (
            explicit_understanding is None
            and
            not model_understanding_succeeded
            and profile.normalized_query != keyword.strip()
        ):
            normalized_matches = self.concept_recall.match(profile.normalized_query)
            added_matches = new_concept_matches(concept_matches, normalized_matches)
            if added_matches:
                concept_matches = merge_concept_matches(concept_matches, added_matches)
                concept_hits = self.ranking.merge_hits(
                    concept_hits,
                    self.concept_recall.recall(
                        added_matches,
                        limit=max(limit * 3, self.candidate_limit),
                    ),
                )
        profile = self.query_profile.build(
            keyword,
            concept_matches=concept_matches,
            understanding=understanding,
        )
        understanding = self.query_understanding.present_recognized_concepts(
            keyword,
            understanding,
            concept_matches,
        )

        database_diagnostic = SearchBranchDiagnostic(
            source="database",
            status="ok",
            duration_ms=_elapsed_ms(database_started),
            result_count=len(database_hits),
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

        hits = self.ranking.fuse_sources([concept_hits, database_hits, meili_hits, embedding_hits])
        concept_route = self.ranking.route_confirmed_concepts(
            hits,
            concept_matches,
            keyword=keyword,
            understanding=understanding,
        )
        hits = concept_route.hits
        active_concept_matches = list(concept_route.active_matches)
        if precision_lock and not active_concept_matches:
            # 第一层已经确认这是业务查询，但第二层没有在预算内完成。
            # 此时绝不能把全库 Meili/Embedding 候选冒充成卖点结果。
            hits = []
        hits = self.system_filter.apply(hits, system_code)
        hits = self.ranking.collapse_asset_groups(hits)
        hits = hits[: max(limit, self.candidate_limit)]

        branch_diagnostics = [
            concept_diagnostic,
            database_diagnostic,
            meili_result.diagnostic,
            embedding_result.diagnostic,
            understanding_result.diagnostic,
        ]
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
            trusted_business_route=bool(active_concept_matches),
        )
        concept_route = self.ranking.route_confirmed_concepts(
            hits,
            concept_matches,
            keyword=keyword,
            understanding=understanding,
        )
        hits = concept_route.hits
        active_concept_matches = list(concept_route.active_matches)
        branch_diagnostics.append(reranker_diagnostic)

        total_duration_ms = _elapsed_ms(started)
        search_diagnostics = self.diagnostics.build(
            total_duration_ms=total_duration_ms,
            branches=branch_diagnostics,
            reranker_used=reranker_used,
            total_timed_out=total_timed_out,
        )
        fallback_reason = self.diagnostics.user_fallback_reason(
            branch_diagnostics,
            trusted_business_route=bool(active_concept_matches),
        )
        return self.ranking.build_response(
            keyword=keyword,
            hits=hits[:limit],
            search_mode="meilisearch" if meili_hits else "fuzzy",
            fallback=fallback_reason is not None,
            fallback_reason=fallback_reason,
            search_understanding=understanding,
            search_diagnostics=search_diagnostics,
            query_concept_matches=active_concept_matches,
        )

    def _database_hits(
        self,
        keyword: str,
        limit: int,
        extra_queries: list[ExpandedQuery],
    ) -> list[SearchHit]:
        return self.database_recall.search_queries(
            self.expansion.database_queries(keyword, extra_queries),
            limit=max(limit * 3, self.candidate_limit),
        )

    def _concept_queries(self, matches: list[ConceptMatch]) -> list[ExpandedQuery]:
        return [
            ExpandedQuery(
                term=item.name,
                score=item.score,
                reasons=item.reasons,
            )
            for item in matches
        ]

def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
