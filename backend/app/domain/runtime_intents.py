"""Runtime intent catalog used by local query understanding.

D027: the database is the runtime source of truth for selling points.
The static ``business_intents.json`` file stays as seed material and offline
fallback; at runtime the database concepts (names, status, reviewed phrases)
are merged on top of it so admin edits take effect without code changes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from app.core.config import PROJECT_DIR
from app.domain.business_intents import (
    BusinessIntentCatalog,
    load_business_intents,
)
from app.domain.taxonomy_catalog import load_taxonomy_catalog

PHRASE_TIER = "phrase"
PAIN_TIER = "pain"
MUST_TIER = "must"
NICE_TIER = "nice"
PUBLIC_PHRASE_GOVERNANCE_PATH = (
    PROJECT_DIR
    / "skills"
    / "understand-image-search-intent"
    / "references"
    / "public-phrase-governance.json"
)

# How reviewed concept_search_phrases map back to local matching tiers.
PHRASE_TYPE_TIERS = {
    "official": PHRASE_TIER,
    "alias": MUST_TIER,
    "pain": PAIN_TIER,
    "business_language": PAIN_TIER,
    "colloquial": PAIN_TIER,
    "scenario": NICE_TIER,
    "outcome": NICE_TIER,
    "typo": NICE_TIER,
}


@dataclass(frozen=True)
class RuntimeIntent:
    code: str
    name: str
    display_name: str
    phrases: tuple[str, ...]
    exact_only_phrases: tuple[str, ...]
    interpretation_patterns: tuple[str, ...]
    pain_points: tuple[str, ...]
    must_have_concepts: tuple[str, ...]
    nice_to_have_concepts: tuple[str, ...]
    exclude_concepts: tuple[str, ...]


@dataclass(frozen=True)
class ExplorationSignal:
    """A photo-entry + explain-purpose combination that stays exploratory.

    D079: sentences like “拍一下，AI马上给你讲解” name the shared photo entry
    without an object, so they must open a fixed candidate set instead of one
    winner or a global fallback.
    """

    candidate_codes: tuple[str, ...]
    entry_terms: tuple[str, ...]
    purpose_terms: tuple[str, ...]


@dataclass(frozen=True)
class RuntimeIntentCatalog:
    version: str
    intents: tuple[RuntimeIntent, ...]
    exploration_signals: tuple[ExplorationSignal, ...] = ()


@dataclass(frozen=True)
class ConceptVocabulary:
    """Database concept knowledge flattened for the domain merge logic."""

    code: str
    name: str
    system_name: str
    status: str
    tiered_phrases: tuple[tuple[str, str], ...]
    exact_only_phrases: tuple[str, ...]
    rejected_phrases: tuple[str, ...]


def runtime_catalog_from_static(
    catalog: BusinessIntentCatalog | None = None,
) -> RuntimeIntentCatalog:
    selected = catalog or load_business_intents()
    node_by_code = load_taxonomy_catalog().node_by_code
    interpretation_signals = _load_interpretation_signals()
    intents = []
    for intent in selected.intents:
        label = node_by_code[intent.target_label_code]
        system = node_by_code[intent.target_system_code]
        intents.append(
            RuntimeIntent(
                code=intent.target_label_code,
                name=label.name,
                display_name=f"{system.name} > {label.name}",
                phrases=intent.phrases,
                exact_only_phrases=intent.exact_only_phrases,
                interpretation_patterns=interpretation_signals.get(
                    intent.target_label_code, ()
                ),
                pain_points=intent.pain_points,
                must_have_concepts=intent.must_have_concepts,
                nice_to_have_concepts=intent.nice_to_have_concepts,
                exclude_concepts=intent.exclude_concepts,
            )
        )
    return RuntimeIntentCatalog(
        version=f"{selected.version}+skill-{_public_phrase_governance_version()}",
        intents=tuple(intents),
        exploration_signals=_load_exploration_signals(),
    )


def merge_runtime_catalog(
    static_catalog: RuntimeIntentCatalog,
    concepts: Sequence[ConceptVocabulary],
) -> RuntimeIntentCatalog:
    by_code = {concept.code: concept for concept in concepts}
    intents: list[RuntimeIntent] = []
    for intent in static_catalog.intents:
        concept = by_code.pop(intent.code, None)
        if concept is None:
            intents.append(intent)
            continue
        if concept.status != "active":
            continue
        intents.append(_merged_intent(intent, concept))
    for concept in by_code.values():
        if concept.status != "active":
            continue
        merged = _intent_from_concept(concept)
        if merged is not None:
            intents.append(merged)
    return RuntimeIntentCatalog(
        version=_runtime_catalog_version(static_catalog, concepts),
        intents=tuple(intents),
        exploration_signals=static_catalog.exploration_signals,
    )


def _merged_intent(intent: RuntimeIntent, concept: ConceptVocabulary) -> RuntimeIntent:
    tiers = _tier_terms(concept)
    # D064：静态目录当前还承担匹配模式基线。数据库旧 seed 可能把同一
    # 共享入口保存为 official/alias；在数据库尚无 match_mode 字段时，
    # 不能让这些记录重新升级成长句子串强匹配。
    exact_keys = {_normalize(item) for item in intent.exact_only_phrases}
    tiers = {
        tier: [term for term in terms if _normalize(term) not in exact_keys]
        for tier, terms in tiers.items()
    }
    rejected = {_normalize(item) for item in concept.rejected_phrases}
    system_name = concept.system_name or intent.display_name.split(">", 1)[0].strip()
    return RuntimeIntent(
        code=intent.code,
        name=concept.name,
        display_name=f"{system_name} > {concept.name}",
        phrases=_merge_terms([concept.name, *intent.phrases], tiers[PHRASE_TIER], rejected),
        exact_only_phrases=_merge_terms(
            intent.exact_only_phrases,
            concept.exact_only_phrases,
            rejected,
        ),
        interpretation_patterns=intent.interpretation_patterns,
        pain_points=_merge_terms(intent.pain_points, tiers[PAIN_TIER], rejected),
        must_have_concepts=_merge_terms(
            intent.must_have_concepts, tiers[MUST_TIER], rejected
        ),
        nice_to_have_concepts=_merge_terms(
            intent.nice_to_have_concepts, tiers[NICE_TIER], rejected
        ),
        exclude_concepts=intent.exclude_concepts,
    )


def _intent_from_concept(concept: ConceptVocabulary) -> RuntimeIntent | None:
    tiers = _tier_terms(concept)
    rejected = {_normalize(item) for item in concept.rejected_phrases}
    display_name = (
        f"{concept.system_name} > {concept.name}" if concept.system_name else concept.name
    )
    intent = RuntimeIntent(
        code=concept.code,
        name=concept.name,
        display_name=display_name,
        phrases=_merge_terms([concept.name], tiers[PHRASE_TIER], rejected),
        exact_only_phrases=_merge_terms([], concept.exact_only_phrases, rejected),
        interpretation_patterns=(),
        pain_points=_merge_terms([], tiers[PAIN_TIER], rejected),
        must_have_concepts=_merge_terms([], tiers[MUST_TIER], rejected),
        nice_to_have_concepts=_merge_terms([], tiers[NICE_TIER], rejected),
        exclude_concepts=(),
    )
    if not any(
        [
            intent.phrases,
            intent.exact_only_phrases,
            intent.pain_points,
            intent.must_have_concepts,
        ]
    ):
        return None
    return intent


def _tier_terms(concept: ConceptVocabulary) -> dict[str, list[str]]:
    tiers: dict[str, list[str]] = {
        PHRASE_TIER: [],
        PAIN_TIER: [],
        MUST_TIER: [],
        NICE_TIER: [],
    }
    for phrase, tier in concept.tiered_phrases:
        tiers.get(tier, tiers[NICE_TIER]).append(phrase)
    return tiers


def _merge_terms(
    base: Sequence[str],
    additions: Sequence[str],
    rejected: set[str],
) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for term in [*base, *additions]:
        cleaned = term.strip()
        key = _normalize(cleaned)
        if not key or key in seen or key in rejected:
            continue
        seen.add(key)
        merged.append(cleaned)
    return tuple(merged)


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_")
    return "".join(char.lower() for char in value if char not in ignored)


@lru_cache
def _load_interpretation_signals() -> dict[str, tuple[str, ...]]:
    """Load Skill-only language patterns without materializing them as public phrases."""
    payload = json.loads(
        PUBLIC_PHRASE_GOVERNANCE_PATH.read_text(encoding="utf-8")
    )
    signals: dict[str, tuple[str, ...]] = {}
    for item in payload.get("interpretationSignals", []):
        code = str(item.get("code") or "").strip()
        values = tuple(
            value
            for raw in item.get("signals", [])
            if (value := str(raw).strip())
        )
        if code and values:
            signals[code] = values
    return signals


@lru_cache
def _load_exploration_signals() -> tuple[ExplorationSignal, ...]:
    """Load combination signals that keep object-less photo queries exploratory."""
    payload = json.loads(
        PUBLIC_PHRASE_GOVERNANCE_PATH.read_text(encoding="utf-8")
    )
    signals: list[ExplorationSignal] = []
    for item in payload.get("explorationSignals", []):
        codes = tuple(
            code
            for raw in item.get("candidateCodes", [])
            if (code := str(raw).strip())
        )
        entries = tuple(
            term
            for raw in item.get("entryTerms", [])
            if (term := str(raw).strip())
        )
        purposes = tuple(
            term
            for raw in item.get("purposeTerms", [])
            if (term := str(raw).strip())
        )
        if len(codes) >= 2 and entries and purposes:
            signals.append(ExplorationSignal(codes, entries, purposes))
    return tuple(signals)


@lru_cache
def _public_phrase_governance_version() -> str:
    payload = json.loads(
        PUBLIC_PHRASE_GOVERNANCE_PATH.read_text(encoding="utf-8")
    )
    version = str(payload.get("version") or "").strip()
    if not version:
        raise ValueError("公共话术治理文件缺少版本")
    return version


def _runtime_catalog_version(
    static_catalog: RuntimeIntentCatalog,
    concepts: Sequence[ConceptVocabulary],
) -> str:
    """Fingerprint runtime knowledge so cached model understanding cannot outlive edits."""
    payload = [
        {
            "code": concept.code,
            "name": concept.name,
            "system": concept.system_name,
            "status": concept.status,
            "phrases": concept.tiered_phrases,
            "exact": concept.exact_only_phrases,
            "rejected": concept.rejected_phrases,
        }
        for concept in sorted(concepts, key=lambda item: item.code)
    ]
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"{static_catalog.version}+db-{digest}"
