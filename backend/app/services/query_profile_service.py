from __future__ import annotations

from app.schemas.ai import SearchUnderstanding
from app.services.query_expansion_service import unique
from app.services.search_models import ConceptMatch, SearchQueryProfile


class QueryProfileService:
    """Builds the Phase 4 internal query profile from validated local/model signals."""

    def build(
        self,
        keyword: str,
        *,
        concept_matches: list[ConceptMatch],
        understanding: SearchUnderstanding | None,
    ) -> SearchQueryProfile:
        normalized_query = keyword.strip()
        negative_constraints: list[str] = []
        confidence = 0.0
        if understanding:
            normalized_query = understanding.normalized_query.strip() or normalized_query
            negative_constraints.extend(understanding.excluded_concepts)
            confidence = max(
                (
                    item.weight
                    for item in understanding.matched_business_concepts
                ),
                default=0.0,
            )
        if concept_matches:
            confidence = max(confidence, concept_matches[0].score)
            if not understanding:
                normalized_query = concept_matches[0].name

        ambiguity: list[str] = []
        if len(concept_matches) > 1:
            top_score = concept_matches[0].score
            ambiguity.extend(
                item.name
                for item in concept_matches[1:]
                if top_score - item.score <= 0.05
            )

        return SearchQueryProfile(
            original_query=keyword,
            normalized_query=normalized_query,
            explicit_system_codes=tuple(
                unique(
                    [
                        code
                        for match in concept_matches
                        for code in match.system_codes
                    ]
                )
            ),
            candidate_concept_codes=tuple(
                unique([item.code for item in concept_matches])
            ),
            negative_constraints=tuple(unique(negative_constraints)),
            ambiguity=tuple(unique(ambiguity)),
            confidence=confidence,
        )
