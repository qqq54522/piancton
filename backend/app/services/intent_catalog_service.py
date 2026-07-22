from __future__ import annotations

from app.domain.runtime_intents import (
    NICE_TIER,
    PHRASE_TYPE_TIERS,
    ConceptVocabulary,
    RuntimeIntentCatalog,
    merge_runtime_catalog,
    runtime_catalog_from_static,
)
from app.models.business_concept import BusinessConcept, ConceptSearchPhrase
from app.repositories.business_concept_repository import BusinessConceptRepository

# Designer-added short generic words (e.g. “课程”) grab too many unrelated
# sentences via substring matching; seeds stay curated so they keep old rules.
MANUAL_SUBSTRING_MIN_LENGTH = 4
SEED_ORIGINS = {"source_document", "migrated"}


class IntentCatalogService:
    """Builds the D027 runtime intent catalog: database first, static seed as fallback."""

    def __init__(self, concepts: BusinessConceptRepository):
        self.concepts = concepts

    def runtime_catalog(self) -> RuntimeIntentCatalog:
        static_catalog = runtime_catalog_from_static()
        try:
            rows = self.concepts.list(include_inactive=True)
        except Exception:  # noqa: BLE001 - 数据库不可用时保持静态兜底，不阻断搜索
            return static_catalog
        vocabularies = [_vocabulary(row) for row in rows]
        if not vocabularies:
            return static_catalog
        return merge_runtime_catalog(static_catalog, vocabularies)


def _vocabulary(concept: BusinessConcept) -> ConceptVocabulary:
    tiered: list[tuple[str, str]] = []
    exact_only: list[str] = []
    rejected: list[str] = []
    for phrase in concept.search_phrases:
        text = phrase.phrase.strip()
        if not text:
            continue
        if phrase.review_status == "rejected":
            rejected.append(text)
            continue
        if phrase.review_status != "accepted":
            continue
        if not _substring_safe(phrase):
            # D053：短人工词保留为完整查询入口，只禁止在长句里做子串强匹配。
            exact_only.append(text)
            continue
        tiered.append((text, PHRASE_TYPE_TIERS.get(phrase.phrase_type, NICE_TIER)))
    return ConceptVocabulary(
        code=concept.code,
        name=concept.name.strip() or concept.code,
        system_name=_system_name(concept),
        status=concept.status,
        tiered_phrases=tuple(tiered),
        exact_only_phrases=tuple(exact_only),
        rejected_phrases=tuple(rejected),
    )


def _substring_safe(phrase: ConceptSearchPhrase) -> bool:
    if phrase.origin in SEED_ORIGINS:
        return True
    normalized = "".join(phrase.phrase.split())
    return len(normalized) >= MANUAL_SUBSTRING_MIN_LENGTH


def _system_name(concept: BusinessConcept) -> str:
    active_links = [
        link
        for link in concept.system_links
        if link.status == "active" and link.system_tag is not None
    ]
    # D064：跨体系 support 关系可以保留，但展示名称必须优先主归属 core。
    for role in ("core", "support"):
        for link in active_links:
            if link.role == role:
                return link.system_tag.name
    if active_links:
        return active_links[0].system_tag.name
    return ""
