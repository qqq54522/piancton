from __future__ import annotations

from app.domain.proof_points import (
    ProofPointCatalog,
    best_query_proof_point_match,
    load_proof_point_catalog,
    semantic_text,
)
from app.schemas.ai import SearchProofPointMatch

PROOF_POINT_TRUST_THRESHOLD = 0.86


class ProofPointUnderstandingService:
    """Recognize optional proof detail inside already-confirmed selling points."""

    def __init__(self, catalog: ProofPointCatalog | None = None):
        self.catalog = catalog or load_proof_point_catalog()

    def recognize(
        self,
        query: str,
        concept_codes: set[str],
        model_matches: list[SearchProofPointMatch] | None = None,
    ) -> list[SearchProofPointMatch]:
        if not query.strip() or not concept_codes:
            return []
        by_code = self.catalog.by_code
        accepted: dict[str, SearchProofPointMatch] = {}
        for match in model_matches or []:
            point = by_code.get(match.code)
            if (
                point is None
                or point.concept_code not in concept_codes
                or match.weight < PROOF_POINT_TRUST_THRESHOLD
            ):
                continue
            accepted[point.concept_code] = SearchProofPointMatch(
                code=point.code,
                concept_code=point.concept_code,
                name=point.name,
                reason=match.reason,
                weight=match.weight,
                evidence_terms=_canonical_evidence_terms(
                    point.search_terms,
                    point.asset_terms,
                    match.evidence_terms,
                ),
            )
        for concept_code in concept_codes:
            candidates = []
            for point in self.catalog.points:
                if point.concept_code != concept_code:
                    continue
                score, evidence = best_query_proof_point_match(query, point)
                candidates.append(
                    (score, len(semantic_text(evidence or "")), point, evidence)
                )
            if not candidates:
                continue
            score, _, point, evidence = max(
                candidates, key=lambda item: (item[0], item[1])
            )
            if score < PROOF_POINT_TRUST_THRESHOLD:
                continue
            current = accepted.get(concept_code)
            if current is not None and current.reason.startswith("组合语义命中"):
                continue
            if current is not None and current.weight >= score:
                continue
            accepted[concept_code] = SearchProofPointMatch(
                code=point.code,
                concept_code=point.concept_code,
                name=point.name,
                reason=f"证明点搜索语言命中：{evidence or point.name}",
                weight=score,
                evidence_terms=[
                    str(item)
                    for item in dict.fromkeys(
                        [*([evidence] if evidence else []), *point.asset_terms]
                    )
                ][:3],
            )
        return sorted(accepted.values(), key=lambda item: item.weight, reverse=True)[:4]


def _canonical_evidence_terms(
    search_terms: tuple[str, ...],
    asset_terms: tuple[str, ...],
    values: list[str],
) -> list[str]:
    allowed = {
        semantic_text(item): item
        for item in (*search_terms, *asset_terms)
        if semantic_text(item)
    }
    result = []
    for value in values:
        canonical = allowed.get(semantic_text(value))
        if canonical and canonical not in result:
            result.append(canonical)
    return result[:3]
