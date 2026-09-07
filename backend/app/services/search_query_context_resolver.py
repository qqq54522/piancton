from __future__ import annotations

from dataclasses import dataclass

from app.schemas.ai import SearchUnderstanding
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.database_search_recall import DatabaseSearchRecallService
from app.services.query_expansion_service import QueryExpansionService
from app.services.query_profile_service import QueryProfileService
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.search_concept_context import matches_from_understanding, new_concept_matches
from app.services.search_external_branches import SearchExternalBranches
from app.services.search_models import SearchBranchResult, SearchHit
from app.services.search_orchestrator_helpers import concept_hits, merge_added_concept_hits
from app.services.search_ranking_service import SearchRankingService


@dataclass(frozen=True)
class SearchQueryContext:
    """The validated query state used by recall and ranking."""

    understanding: SearchUnderstanding | None
    concept_matches: list
    concept_hits: list[SearchHit]
    database_hits: list[SearchHit]
    model_understanding_succeeded: bool
    precision_lock: bool


class SearchQueryContextResolver:
    """Merges local and staged model understanding before candidate fusion."""

    def __init__(
        self,
        *,
        expansion: QueryExpansionService,
        query_understanding: QueryUnderstandingService,
        query_profile: QueryProfileService,
        concept_recall: ConceptSearchRecallService,
        database_recall: DatabaseSearchRecallService,
        external_branches: SearchExternalBranches,
        ranking: SearchRankingService,
        candidate_limit: int,
    ):
        self.expansion = expansion
        self.query_understanding = query_understanding
        self.query_profile = query_profile
        self.concept_recall = concept_recall
        self.database_recall = database_recall
        self.external_branches = external_branches
        self.ranking = ranking
        self.candidate_limit = max(1, candidate_limit)

    def resolve(
        self,
        *,
        keyword: str,
        local_understanding: SearchUnderstanding | None,
        understanding_result: SearchBranchResult,
        explicit_filter: bool,
        concept_matches: list,
        concept_hits_value: list[SearchHit],
        database_hits_value: list[SearchHit],
        limit: int,
        pure_vikingdb_required: bool = False,
    ) -> SearchQueryContext:
        understanding = self.external_branches.final_understanding(
            keyword,
            local_understanding,
            understanding_result,
            pure_vikingdb_required=pure_vikingdb_required,
        )
        model_understanding_succeeded = (
            self.external_branches.understanding_succeeded(understanding_result)
        )
        precision_lock = self.external_branches.requires_precision_lock(
            understanding_result
        )
        if (
            pure_vikingdb_required
            and not model_understanding_succeeded
        ):
            return SearchQueryContext(
                understanding=None,
                concept_matches=[],
                concept_hits=[],
                database_hits=[],
                model_understanding_succeeded=False,
                precision_lock=True,
            )
        if (
            understanding
            and understanding is not local_understanding
            and not pure_vikingdb_required
        ):
            model_expansions = self.expansion.queries_from_understanding(understanding)
            database_hits_value = self.ranking.merge_hits(
                database_hits_value,
                self._database_hits(keyword, limit, model_expansions),
            )

        understood_matches = matches_from_understanding(
            understanding,
            self.concept_recall,
        )
        if model_understanding_succeeded:
            concept_matches = understood_matches
            concept_hits_value = concept_hits(
                self.concept_recall,
                concept_matches,
                limit,
                self.candidate_limit,
            )
        else:
            added_matches = new_concept_matches(concept_matches, understood_matches)
            concept_matches, concept_hits_value = merge_added_concept_hits(
                concept_matches=concept_matches,
                concept_hits_value=concept_hits_value,
                added_matches=added_matches,
                concept_recall=self.concept_recall,
                ranking=self.ranking,
                limit=limit,
                candidate_limit=self.candidate_limit,
            )

        normalized_query = self.query_profile.build(
            keyword,
            concept_matches=concept_matches,
            understanding=understanding,
        ).normalized_query
        if (
            not explicit_filter
            and not model_understanding_succeeded
            and normalized_query != keyword.strip()
        ):
            normalized_matches = self.concept_recall.match(normalized_query)
            added_matches = new_concept_matches(concept_matches, normalized_matches)
            concept_matches, concept_hits_value = merge_added_concept_hits(
                concept_matches=concept_matches,
                concept_hits_value=concept_hits_value,
                added_matches=added_matches,
                concept_recall=self.concept_recall,
                ranking=self.ranking,
                limit=limit,
                candidate_limit=self.candidate_limit,
            )

        understanding = self.query_understanding.present_recognized_concepts(
            keyword,
            understanding,
            concept_matches,
        )
        if pure_vikingdb_required and model_understanding_succeeded and understanding:
            understanding.search_strategy = (
                "VikingDB 卖点库存路由："
                + (understanding.search_strategy or "按命中卖点返回本地图库")
            )
        return SearchQueryContext(
            understanding=understanding,
            concept_matches=concept_matches,
            concept_hits=concept_hits_value,
            database_hits=database_hits_value,
            model_understanding_succeeded=model_understanding_succeeded,
            precision_lock=precision_lock,
        )

    def _database_hits(
        self,
        keyword: str,
        limit: int,
        extra_queries: list,
    ) -> list[SearchHit]:
        return self.database_recall.search_queries(
            self.expansion.database_queries(keyword, extra_queries),
            limit=max(limit * 3, self.candidate_limit),
        )
