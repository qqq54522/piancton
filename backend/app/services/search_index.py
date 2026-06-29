from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.domain.taxonomy_catalog import TaxonomyCatalog, load_taxonomy_catalog
from app.models.image import Image, ImageBusinessLabel
from app.models.tag import Tag
from app.services.image_semantic_profile_service import ImageSemanticProfileService


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _tag_label(tag: Tag) -> str:
    if tag.parent:
        return f"{tag.parent.name} > {tag.name}"
    return tag.name


def _system_code_for_tag(tag: Tag) -> str | None:
    if tag.parent and tag.parent.code:
        return tag.parent.code
    if tag.node_type == "system" and tag.code:
        return tag.code
    return None


def _system_name_for_tag(tag: Tag) -> str | None:
    if tag.parent:
        return tag.parent.name
    if tag.node_type == "system":
        return tag.name
    return None


def _catalog_terms(catalog: TaxonomyCatalog, codes: Iterable[str]) -> tuple[list[str], list[str]]:
    aliases: list[str] = []
    definitions: list[str] = []
    node_by_code = catalog.node_by_code
    for code in codes:
        node = node_by_code.get(code)
        if not node:
            continue
        aliases.extend(node.aliases)
        if node.definition:
            definitions.append(node.definition)
    return _unique(aliases), _unique(definitions)


def _business_label_names(labels: Iterable[ImageBusinessLabel]) -> list[str]:
    names: list[str] = []
    for label in labels:
        names.append(label.tag.name)
        names.append(_tag_label(label.tag))
    return _unique(names)


def image_to_search_document(
    image: Image,
    *,
    catalog: TaxonomyCatalog | None = None,
) -> dict[str, Any]:
    """Build the derived Meilisearch document for one image.

    The relational database remains authoritative. This document intentionally
    duplicates only search-oriented text, codes and filter fields so the index
    can be rebuilt from scratch at any time.
    """

    catalog = catalog or load_taxonomy_catalog()
    semantic_profile = ImageSemanticProfileService()
    profile = semantic_profile.profile_from_image(image)
    manual_tags = [link.tag for link in image.tag_links]
    searchable_business_labels = [
        label for label in image.business_labels if label.review_status != "rejected"
    ]
    manual_business_labels = [
        label for label in searchable_business_labels if label.origin == "manual"
    ]
    manual_primary_label = next(
        (label for label in manual_business_labels if label.role == "primary"),
        None,
    )
    manual_assignable_tags = [
        tag for tag in manual_tags if tag.assignable and tag.status == "active"
    ]
    fallback_manual_primary = sorted(
        manual_assignable_tags,
        key=lambda tag: (tag.sort_order, tag.name, tag.id),
    )[0] if manual_assignable_tags else None
    manual_primary = manual_primary_label.tag if manual_primary_label else fallback_manual_primary

    manual_label_codes = _unique(tag.code for tag in manual_tags)
    manual_label_names = _unique(_tag_label(tag) for tag in manual_tags)
    manual_system_codes = _unique(_system_code_for_tag(tag) for tag in manual_tags)
    manual_system_names = _unique(_system_name_for_tag(tag) for tag in manual_tags)

    accepted_ai_labels = [
        label
        for label in searchable_business_labels
        if label.origin == "ai" and label.review_status == "accepted"
    ]
    pending_ai_labels = [
        label
        for label in searchable_business_labels
        if label.origin == "ai" and label.review_status == "pending"
    ]
    accepted_ai_codes = _unique(label.label_code for label in accepted_ai_labels)
    pending_ai_codes = _unique(label.label_code for label in pending_ai_labels)
    manual_business_codes = _unique(label.label_code for label in manual_business_labels)
    business_label_codes = _unique(
        [*manual_business_codes, *accepted_ai_codes, *pending_ai_codes]
    )
    business_label_names = _business_label_names(searchable_business_labels)
    business_system_codes = _unique(
        _system_code_for_tag(label.tag) for label in searchable_business_labels
    )
    business_system_names = _unique(
        _system_name_for_tag(label.tag) for label in searchable_business_labels
    )

    all_label_codes = _unique([*manual_label_codes, *business_label_codes])
    ancestor_codes: list[str] = []
    for code in all_label_codes:
        ancestor_codes.extend(catalog.ancestor_codes(code) if code in catalog.node_by_code else [])
    systems = _unique([*manual_system_codes, *business_system_codes, *ancestor_codes])
    system_names = _unique([*manual_system_names, *business_system_names])
    aliases, definitions = _catalog_terms(catalog, [*systems, *all_label_codes])

    content_tags = _unique(item.tag_name for item in image.content_tags)
    content_dimensions = _unique(item.dimension for item in image.content_tags)
    level2_categories = _unique(item.category_name for item in image.level2_categories)
    ai_reasons = _unique(label.reason for label in searchable_business_labels)
    category_names = _unique(item.name for item in image.categories)
    file_stem = Path(image.file_name).stem
    profile_visual_facts = profile.visual_facts if profile else []
    profile_search_phrases = profile.search_phrases if profile else []
    profile_exclusion_boundaries = profile.exclusion_boundaries if profile else []
    profile_business_intent = profile.business_intent if profile else ""

    searchable_text_parts = _unique(
        [
            image.title,
            file_stem,
            image.image_summary,
            *profile_visual_facts,
            profile_business_intent,
            *profile_search_phrases,
            *profile_exclusion_boundaries,
            *manual_label_names,
            *manual_label_codes,
            *business_label_names,
            *business_label_codes,
            *system_names,
            *systems,
            *content_tags,
            *content_dimensions,
            *level2_categories,
            *category_names,
            *aliases,
            *definitions,
            *ai_reasons,
        ]
    )

    return {
        "id": image.id,
        "title": image.title,
        "fileName": image.file_name,
        "fileStem": file_stem,
        "caption": image.image_summary or "",
        "semanticProfileVisualFacts": profile_visual_facts,
        "semanticProfileBusinessIntent": profile_business_intent,
        "semanticProfileSearchPhrases": profile_search_phrases,
        "semanticProfileExclusionBoundaries": profile_exclusion_boundaries,
        "manualPrimaryLabelCode": manual_primary.code if manual_primary else None,
        "manualPrimaryLabelName": _tag_label(manual_primary) if manual_primary else None,
        "manualLabelCodes": manual_label_codes,
        "manualLabelNames": manual_label_names,
        "manualBusinessLabelCodes": manual_business_codes,
        "acceptedAiLabelCodes": accepted_ai_codes,
        "pendingAiLabelCodes": pending_ai_codes,
        "businessLabelCodes": business_label_codes,
        "businessLabelNames": business_label_names,
        "systems": systems,
        "systemNames": system_names,
        "ancestorCodes": _unique(ancestor_codes),
        "contentTags": content_tags,
        "contentDimensions": content_dimensions,
        "level2Categories": level2_categories,
        "categories": category_names,
        "aliases": aliases,
        "searchableText": " \n".join(searchable_text_parts),
        "downloadCount": image.download_count,
        "status": "deleted" if image.deleted_at else "active",
        "createdAt": _iso(image.created_at),
        "deletedAt": _iso(image.deleted_at),
    }
