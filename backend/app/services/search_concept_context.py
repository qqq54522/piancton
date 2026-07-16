from __future__ import annotations

from app.schemas.ai import SearchUnderstanding
from app.services.concept_search_recall import ConceptSearchRecallService
from app.services.search_models import ConceptMatch


def matches_from_understanding(
    understanding: SearchUnderstanding | None,
    concept_recall: ConceptSearchRecallService,
) -> list[ConceptMatch]:
    if understanding is None:
        return []
    weighted: list[ConceptMatch] = []
    for item in understanding.matched_business_concepts:
        display_name = item.concept.rsplit(">", 1)[-1].strip()
        candidates = concept_recall.match(display_name)
        exact = [
            match
            for match in candidates
            if _normalize(match.name) == _normalize(display_name)
            or _normalize(match.code) == _normalize(display_name)
        ]
        for match in exact or candidates[:1]:
            weighted.append(
                ConceptMatch(
                    concept_id=match.concept_id,
                    code=match.code,
                    name=match.name,
                    score=min(match.score, item.weight),
                    system_codes=match.system_codes,
                    reasons=tuple(
                        dict.fromkeys(
                            [*match.reasons, f"查询意图识别：{item.concept}"]
                        )
                    ),
                )
            )
    return merge_concept_matches(weighted)


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


def new_concept_matches(
    existing: list[ConceptMatch],
    candidates: list[ConceptMatch],
) -> list[ConceptMatch]:
    existing_ids = {item.concept_id for item in existing}
    return [item for item in candidates if item.concept_id not in existing_ids]


def merge_concept_matches(*groups: list[ConceptMatch]) -> list[ConceptMatch]:
    merged: dict[str, ConceptMatch] = {}
    for match in (item for group in groups for item in group):
        existing = merged.get(match.concept_id)
        if existing is None:
            merged[match.concept_id] = match
            continue
        preferred = match if match.score > existing.score else existing
        merged[match.concept_id] = ConceptMatch(
            concept_id=preferred.concept_id,
            code=preferred.code,
            name=preferred.name,
            score=max(existing.score, match.score),
            system_codes=tuple(
                dict.fromkeys([*existing.system_codes, *match.system_codes])
            ),
            reasons=tuple(dict.fromkeys([*existing.reasons, *match.reasons])),
        )
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)
