from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from app.models.image import Image
from app.services.image_semantic_profile_service import ImageSemanticProfileService


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def image_to_search_document(image: Image) -> dict[str, Any]:
    """Build the fully derived Phase 6 search document for one image."""

    semantic = ImageSemanticProfileService()
    profile = semantic.profile_from_image(image)
    group = image.asset_group
    links = list(group.concept_links) if group else []
    active_links = [
        link
        for link in links
        if link.review_status != "rejected" and link.relation_role != "excludes"
    ]
    manual_links = [
        link
        for link in active_links
        if link.review_status == "accepted" and link.origin in {"manual", "migrated"}
    ]
    accepted_ai_links = [
        link
        for link in active_links
        if link.review_status == "accepted" and link.origin == "ai"
    ]
    pending_ai_links = [
        link
        for link in active_links
        if link.review_status == "pending" and link.origin == "ai"
    ]
    accepted_links = [*manual_links, *accepted_ai_links]
    accepted_concept_codes = _unique(link.concept.code for link in accepted_links)
    accepted_concept_names = _unique(link.concept.name for link in accepted_links)
    accepted_concept_phrases = _unique(
        phrase.phrase
        for link in accepted_links
        for phrase in link.concept.search_phrases
        if phrase.review_status == "accepted"
    )
    accepted_concept_systems = _unique(
        system.system_tag.code
        for link in accepted_links
        for system in link.concept.system_links
        if system.status == "active"
    )
    asset_phrases = _unique(
        phrase.phrase
        for phrase in (group.search_phrases if group else [])
        if phrase.review_status == "accepted"
    )
    profile_visual_facts = profile.visual_facts if profile else []
    profile_scenes = profile.scenes if profile else []
    profile_search_phrases = semantic.semantic_search_phrases(image, profile=profile)
    business_intent = semantic.business_intent_from_image(image)
    searchable_text = " \n".join(
        _unique(
            [
                image.title,
                Path(image.file_name).stem,
                image.image_summary,
                image.channel,
                *profile_visual_facts,
                *profile_scenes,
                *profile_search_phrases,
                *accepted_concept_names,
                *accepted_concept_codes,
                *accepted_concept_phrases,
                *accepted_concept_systems,
                *asset_phrases,
            ]
        )
    )

    return {
        "id": image.id,
        "assetGroupId": image.asset_group_id or image.id,
        "assetRole": image.asset_role,
        "title": image.title,
        "fileName": image.file_name,
        "fileStem": Path(image.file_name).stem,
        "caption": image.image_summary or "",
        "channel": image.channel,
        "width": image.width,
        "height": image.height,
        "aspectRatio": image.aspect_ratio,
        "semanticProfileVisualFacts": profile_visual_facts,
        "semanticProfileScenes": profile_scenes,
        "semanticProfileBusinessIntent": business_intent,
        "semanticProfileSearchPhrases": profile_search_phrases,
        "manualConceptCodes": _unique(link.concept.code for link in manual_links),
        "acceptedAiConceptCodes": _unique(
            link.concept.code for link in accepted_ai_links
        ),
        "pendingAiConceptCodes": _unique(link.concept.code for link in pending_ai_links),
        "pendingConceptNames": _unique(link.concept.name for link in pending_ai_links),
        "acceptedConceptCodes": accepted_concept_codes,
        "acceptedConceptNames": accepted_concept_names,
        "acceptedConceptPhrases": accepted_concept_phrases,
        "acceptedConceptSystems": accepted_concept_systems,
        "excludedConceptCodes": _unique(
            link.concept.code
            for link in links
            if link.relation_role == "excludes" and link.review_status == "accepted"
        ),
        "assetSearchPhrases": asset_phrases,
        "searchableText": searchable_text,
        "downloadCount": image.download_count,
        "status": (
            "deleted"
            if image.deleted_at
            else "active"
            if not group or (group.publish_status == "published" and image.is_current)
            else "inactive"
        ),
        "createdAt": _iso(image.created_at),
        "deletedAt": _iso(image.deleted_at),
    }
