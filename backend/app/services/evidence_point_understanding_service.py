from __future__ import annotations

from app.domain.evidence_points import (
    EvidencePointCatalog,
    best_query_evidence_point_match,
    load_evidence_point_catalog,
)
from app.schemas.ai import SearchEvidencePointMatch

EVIDENCE_POINT_TRUST_THRESHOLD = 0.86


class EvidencePointUnderstandingService:
    def __init__(self, catalog: EvidencePointCatalog | None = None):
        self.catalog = catalog or load_evidence_point_catalog()

    def recognize(
        self,
        query: str,
        proof_point_codes: set[str] | None = None,
        concept_codes: set[str] | None = None,
    ) -> list[SearchEvidencePointMatch]:
        proof_point_codes = proof_point_codes or set()
        concept_codes = concept_codes or set()
        if not query.strip() or not (proof_point_codes or concept_codes):
            return []
        matches: list[SearchEvidencePointMatch] = []
        grouped_candidates: dict[str, list] = {}
        for point in self.catalog.points:
            if point.proof_point_code in proof_point_codes:
                group = f"proof:{point.proof_point_code}"
            elif point.concept_code in concept_codes:
                group = f"concept:{point.concept_code}"
            else:
                continue
            score, evidence = best_query_evidence_point_match(query, point)
            grouped_candidates.setdefault(group, []).append(
                (score, len(evidence or ""), point, evidence)
            )
        for candidates in grouped_candidates.values():
            if not candidates:
                continue
            score, _, point, evidence = max(candidates, key=lambda item: (item[0], item[1]))
            if score < EVIDENCE_POINT_TRUST_THRESHOLD:
                continue
            matches.append(
                SearchEvidencePointMatch(
                    code=point.code,
                    proof_point_code=point.proof_point_code,
                    concept_code=point.concept_code,
                    name=point.name,
                    reason=f"证据表达命中：{evidence or point.name}",
                    weight=score,
                )
            )
        return sorted(matches, key=lambda item: item.weight, reverse=True)
