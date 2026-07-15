from __future__ import annotations

import time

from app.domain.search_query_expansion import ExpandedQuery
from app.schemas.image import SearchResponse
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_profile_service import QueryProfileService
from app.services.query_understanding_service import QueryUnderstandingService
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
    ) -> SearchResponse:
        started = time.monotonic()
        local_understanding = self.query_understanding.understand_locally(keyword)
        local_expansions = self.expansion.queries_from_understanding(local_understanding)
        external_query = self.expansion.external_keyword(keyword, local_expansions)

        meili_task = self.external_branches.start_meilisearch(
            external_query,
            limit,
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
        concept_matches = self.concept_recall.match(keyword)
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
        if understanding and understanding is not local_understanding:
            model_expansions = self.expansion.queries_from_understanding(understanding)
            database_hits = self.ranking.merge_hits(
                database_hits,
                self._database_hits(keyword, limit, model_expansions),
            )

        profile = self.query_profile.build(
            keyword,
            concept_matches=concept_matches,
            understanding=understanding,
        )
        if profile.normalized_query != keyword.strip():
            normalized_matches = self.concept_recall.match(profile.normalized_query)
            added_matches = _new_concept_matches(concept_matches, normalized_matches)
            if added_matches:
                concept_matches.extend(added_matches)
                concept_hits = self.ranking.merge_hits(
                    concept_hits,
                    self.concept_recall.recall(
                        added_matches,
                        limit=max(limit * 3, self.candidate_limit),
                    ),
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
        (
            hits,
            reranker_diagnostic,
            reranker_used,
            total_timed_out,
        ) = await self.rerank_coordinator.rerank(
            keyword,
            hits,
            search_started=started,
        )
        branch_diagnostics.append(reranker_diagnostic)

        total_duration_ms = _elapsed_ms(started)
        search_diagnostics = self.diagnostics.build(
            total_duration_ms=total_duration_ms,
            branches=branch_diagnostics,
            reranker_used=reranker_used,
            total_timed_out=total_timed_out,
        )
        fallback_reason = self.diagnostics.fallback_reason(branch_diagnostics)
        return self.ranking.build_response(
            keyword=keyword,
            hits=hits[:limit],
            search_mode="meilisearch" if meili_hits else "fuzzy",
            fallback=fallback_reason is not None,
            fallback_reason=fallback_reason,
            search_understanding=understanding,
            search_diagnostics=search_diagnostics,
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

def _new_concept_matches(
    existing: list[ConceptMatch],
    candidates: list[ConceptMatch],
) -> list[ConceptMatch]:
    existing_ids = {item.concept_id for item in existing}
    return [item for item in candidates if item.concept_id not in existing_ids]


def _elapsed_ms(started: float) -> int:
    return max(0, round((time.monotonic() - started) * 1000))
