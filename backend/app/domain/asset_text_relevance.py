from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog
from app.schemas.ai import SearchUnderstanding


@dataclass(frozen=True)
class AssetSelectionEvidence:
    query_text_score: float = 0.0
    phrase_score: float = 0.0
    phrase: str | None = None
    phrase_matched: bool = False
    auxiliary_score: float = 0.0
    auxiliary: str | None = None
    auxiliary_matched: bool = False
    proof_point_code: str | None = None
    proof_point_name: str | None = None
    proof_point_confidence: float = 0.0
    proof_asset_score: float = 0.0
    proof_asset_matched: bool = False
    business_facet_matched: bool = False
    business_facet_mismatch: bool = False


def best_text_match(
    contexts: list[str], values: list[tuple[str, float]]
) -> tuple[float, str | None]:
    best_score, best_value = 0.0, None
    for context in contexts:
        query = normalize_text(context)
        for value, weight in values:
            candidate = normalize_text(value)
            if not query or not candidate:
                continue
            if query == candidate:
                score = 1.0
            elif candidate in query:
                score = 0.96
            elif query in candidate:
                score = 0.92
            else:
                score = SequenceMatcher(None, query, candidate).ratio()
            score = min(score, max(0.0, min(1.0, weight)))
            if score > best_score:
                best_score, best_value = score, value
    return best_score, best_value


def contains_any(value: str, terms: tuple[str, ...]) -> bool:
    normalized = normalize_text(value)
    return bool(normalized) and any(
        term and term in normalized for item in terms if (term := normalize_text(item))
    )


def policy_evidence_terms(
    keyword: str,
    concept_codes: set[str],
    requirements,
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            term
            for demand in requirements
            if concept_codes.intersection(demand.concept_codes)
            and contains_any(keyword, demand.query_trigger_terms)
            for term in demand.asset_terms
        )
    )


def asset_selection_text(hit) -> str:
    group = hit.image.asset_group
    values = [hit.image.title, group.title if group else ""]
    values.extend(
        item.phrase
        for item in (group.search_phrases if group else [])
        if item.review_status == "accepted"
    )
    return " ".join(value for value in values if value)


def normalize_text(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”‘’\"'（）()《》<>[]【】-_")
    normalized = "".join(char.lower() for char in value if char not in ignored)
    return normalized.replace("5到8", "58").replace("五到八", "58")


def query_contexts(keyword: str, understanding: SearchUnderstanding | None) -> list[str]:
    values = [keyword]
    if understanding:
        values.extend([understanding.normalized_query, understanding.search_intent])
        values.extend(item.term for item in understanding.expanded_terms if item.weight >= 0.65)
        values.extend(
            item.concept.rsplit(">", 1)[-1] for item in understanding.matched_business_concepts
        )
        values.extend(item.name for item in understanding.matched_proof_points)
        values.extend(item.name for item in understanding.matched_evidence_points)
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def best_proof_asset_match(
    understanding: SearchUnderstanding | None,
    concept_codes: set[str],
    phrase_values: list[tuple[str, float]],
    auxiliary_values: list[tuple[str, float]],
    *,
    query_phrase_score: float,
    phrase_threshold: float,
    auxiliary_threshold: float,
    policy_evidence_terms: tuple[str, ...] = (),
) -> tuple[str | None, str | None, float, float, bool]:
    if understanding is None or not understanding.matched_proof_points:
        return None, None, 0.0, 0.0, False
    definitions = load_proof_point_catalog().by_code
    evidence_definitions = load_evidence_point_catalog().by_code
    best: tuple[str | None, str | None, float, float, bool] = (
        None,
        None,
        0.0,
        0.0,
        False,
    )
    for match in understanding.matched_proof_points:
        point = definitions.get(match.code)
        if point is None or point.concept_code not in concept_codes:
            continue
        evidence_contexts = [
            value
            for evidence_match in understanding.matched_evidence_points
            if evidence_match.proof_point_code == point.code
            if (evidence := evidence_definitions.get(evidence_match.code)) is not None
            for value in (evidence.name, *evidence.search_terms)
        ]
        contexts = [
            *evidence_contexts,
            *match.evidence_terms,
            *policy_evidence_terms,
        ]
        phrase_score, _ = best_text_match(contexts, phrase_values)
        auxiliary_score, _ = best_text_match(contexts, auxiliary_values)
        proof_score = max(phrase_score, auxiliary_score, query_phrase_score)
        matched = (
            max(phrase_score, query_phrase_score) >= phrase_threshold
            or auxiliary_score >= auxiliary_threshold
        )
        candidate = (point.code, point.name, match.weight, proof_score, matched)
        if best[0] is None or (int(candidate[4]), candidate[3]) > (
            int(best[4]),
            best[3],
        ):
            best = candidate
    return best


def image_rank_key(
    evidence: AssetSelectionEvidence | None, fallback_score: float
) -> tuple[int, float, int, float, int, float, int, float]:
    """Make accepted asset-specific wording the final intra-concept tiebreaker."""
    if evidence is None:
        return (0, 0.0, 0, 0.0, 0, 0.0, 0, fallback_score)
    return (
        int(evidence.business_facet_matched),
        evidence.query_text_score,
        int(evidence.phrase_matched),
        evidence.phrase_score if evidence.phrase_matched else 0.0,
        int(evidence.proof_asset_matched),
        evidence.proof_asset_score,
        int(evidence.auxiliary_matched),
        fallback_score,
    )
