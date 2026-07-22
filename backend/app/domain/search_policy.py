from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR

SEARCH_POLICY_PATH = PROJECT_DIR / "taxonomy" / "search_policy.json"


@dataclass(frozen=True)
class AssetSpecificityGate:
    """Require explicit query evidence before a specialist proof asset can rank."""

    code: str
    concept_codes: tuple[str, ...]
    asset_terms: tuple[str, ...]
    query_trigger_terms: tuple[str, ...]


@dataclass(frozen=True)
class AssetEvidenceRequirement:
    """Demand matching asset evidence when the query names a proof-point topic.

    Keeps proof-point queries empty (exposing the material gap) instead of
    flooding them with sibling assets of the same selling point.
    """

    code: str
    concept_codes: tuple[str, ...]
    query_trigger_terms: tuple[str, ...]
    asset_terms: tuple[str, ...]


@dataclass(frozen=True)
class AssetSelectionRules:
    """Tune third-layer image filtering without changing business routing."""

    accepted_phrase_match_threshold: float = 0.58
    auxiliary_match_threshold: float = 0.72
    filter_supports_when_expresses_exist: bool = True


@dataclass(frozen=True)
class SearchPolicyCatalog:
    version: str
    ambiguous_terms: tuple[str, ...]
    asset_specificity_gates: tuple[AssetSpecificityGate, ...] = ()
    asset_evidence_requirements: tuple[AssetEvidenceRequirement, ...] = ()
    asset_selection: AssetSelectionRules = AssetSelectionRules()


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _term_rules(value: Any, factory):
    if not isinstance(value, list):
        return ()
    rules = []
    for item in value:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        concept_codes = _strings(item.get("concept_codes"))
        asset_terms = _strings(item.get("asset_terms"))
        query_trigger_terms = _strings(item.get("query_trigger_terms"))
        if not all((code, concept_codes, asset_terms, query_trigger_terms)):
            continue
        rules.append(
            factory(
                code=code,
                concept_codes=concept_codes,
                asset_terms=asset_terms,
                query_trigger_terms=query_trigger_terms,
            )
        )
    return tuple(rules)


def _asset_selection_rules(value: Any) -> AssetSelectionRules:
    if not isinstance(value, dict):
        return AssetSelectionRules()
    defaults = AssetSelectionRules()
    return AssetSelectionRules(
        accepted_phrase_match_threshold=_bounded_float(
            value.get("accepted_phrase_match_threshold"),
            defaults.accepted_phrase_match_threshold,
        ),
        auxiliary_match_threshold=_bounded_float(
            value.get("auxiliary_match_threshold"),
            defaults.auxiliary_match_threshold,
        ),
        filter_supports_when_expresses_exist=bool(
            value.get(
                "filter_supports_when_expresses_exist",
                defaults.filter_supports_when_expresses_exist,
            )
        ),
    )


def _bounded_float(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


@lru_cache
def load_search_policy(path: Path = SEARCH_POLICY_PATH) -> SearchPolicyCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SearchPolicyCatalog(
        version=str(raw.get("version") or "").strip(),
        ambiguous_terms=_strings(raw.get("ambiguous_terms")),
        asset_specificity_gates=_term_rules(
            raw.get("asset_specificity_gates"), AssetSpecificityGate
        ),
        asset_evidence_requirements=_term_rules(
            raw.get("asset_evidence_requirements"), AssetEvidenceRequirement
        ),
        asset_selection=_asset_selection_rules(raw.get("asset_selection")),
    )
