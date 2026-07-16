from __future__ import annotations

from typing import Any

from app.ai.contracts import ModelRequest
from app.domain.taxonomy_catalog import load_taxonomy_catalog

DEFAULT_CONCEPT_SUGGESTION_REASON = (
    "模型返回稳定 code，系统已转换为业务概念建议；"
    "模型未提供具体适配证据和相邻概念边界。"
)
STRING_CONCEPT_SUGGESTION_REASON = (
    "模型以简写形式返回，系统已转换为业务概念建议；"
    "模型未提供具体适配证据和相邻概念边界。"
)


def normalize_model_payload(
    request: ModelRequest,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Normalize tolerated vendor/model deviations before schema validation.

    This is still a strict boundary: services validate the normalized payload
    against Pydantic schemas, and invalid model output becomes a domain error.
    """

    if request.task == "search_intent_understanding":
        return _normalize_search_understanding_payload(payload)
    if request.task != "image_content_analysis":
        return payload

    normalized = dict(payload)
    normalized["semantic_profile"] = _normalize_semantic_profile(
        normalized.get("semantic_profile"),
        normalized.get("image_summary"),
    )
    normalized.pop("content_tags", None)
    normalized.pop("recommended_search_words", None)

    concept_suggestions = normalized.get("concept_suggestions")
    if isinstance(concept_suggestions, list):
        normalized_concept_suggestions = [
            _normalize_concept_suggestion(item)
            for item in concept_suggestions
            if item
        ]
        normalized["concept_suggestions"] = [
            item for item in normalized_concept_suggestions if item
        ]

    return normalized


def _normalize_semantic_profile(
    value: Any,
    image_summary: Any,
) -> dict[str, Any]:
    old = dict(value) if isinstance(value, dict) else {}
    visual_facts = old.get("visual_facts")
    if not isinstance(visual_facts, list) or not visual_facts:
        visual_facts = [str(image_summary).strip()] if str(image_summary or "").strip() else []
    asset_phrases = old.get("asset_search_phrases")
    if not isinstance(asset_phrases, list):
        asset_phrases = []
    return {
        "schema_version": 3,
        "visual_facts": visual_facts,
        "scenes": old.get("scenes") if isinstance(old.get("scenes"), list) else [],
        "asset_search_phrases": asset_phrases,
    }


def _normalize_search_understanding_payload(payload: dict[str, Any]) -> dict[str, Any]:
    catalog = load_taxonomy_catalog()
    normalized = dict(payload)

    expanded_terms = normalized.get("expanded_terms")
    if isinstance(expanded_terms, list):
        normalized["expanded_terms"] = [
            _normalize_search_term(item, catalog.node_by_code)
            for item in expanded_terms
            if item
        ]

    concepts = normalized.get("matched_business_concepts")
    if isinstance(concepts, list):
        normalized["matched_business_concepts"] = [
            _normalize_search_concept(item, catalog.node_by_code)
            for item in concepts
            if item
        ]

    excluded_concepts = normalized.get("excluded_concepts")
    if isinstance(excluded_concepts, list):
        normalized["excluded_concepts"] = [
            _display_name_from_code(str(item), catalog.node_by_code) or str(item)
            for item in excluded_concepts
        ]
    return normalized


def _normalize_search_term(
    value: Any,
    node_by_code: dict[str, Any],
) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    term = str(normalized.get("term") or "").strip()
    normalized["term"] = _display_name_from_code(term, node_by_code) or term
    return normalized


def _normalize_search_concept(
    value: Any,
    node_by_code: dict[str, Any],
) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    concept = str(normalized.get("concept") or "").strip()
    normalized["concept"] = _display_name_from_code(concept, node_by_code) or concept
    return normalized


def _display_name_from_code(code: str, node_by_code: dict[str, Any]) -> str | None:
    node = node_by_code.get(code.strip())
    if not node:
        return None
    if node.parent_code and node.parent_code in node_by_code:
        parent = node_by_code[node.parent_code]
        return f"{parent.name} > {node.name}"
    return node.name


def _normalize_concept_suggestion(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_concept_suggestion_dict(value)
    if not isinstance(value, str):
        return value
    system, separator, label = value.partition(">")
    label = label.strip() if separator else system.strip()
    system = system.strip() if separator else ""
    code_concept = _concept_suggestion_from_code(label)
    if code_concept:
        return code_concept
    return {
        "system_name": system,
        "concept_name": label,
        "confidence": 0.75,
        "evidence_level": "C",
        "relation_role": "supports",
        "reason": STRING_CONCEPT_SUGGESTION_REASON,
    }


def _normalize_concept_suggestion_dict(value: dict[str, Any]) -> dict[str, Any] | None:
    normalized = dict(value)
    candidate_code = str(
        normalized.get("concept_code")
        or normalized.get("code")
        or ""
    ).strip()
    if not candidate_code:
        for key in ("concept_name", "name"):
            candidate = str(normalized.get(key) or "").strip()
            if _concept_suggestion_from_code(candidate):
                candidate_code = candidate
                break
    code_concept = _concept_suggestion_from_code(
        candidate_code,
        confidence=normalized.get("confidence", 0.75),
        evidence_level=normalized.get("evidence_level", "C"),
        relation_role=normalized.get("relation_role", "supports"),
        reason=normalized.get(
            "reason",
            DEFAULT_CONCEPT_SUGGESTION_REASON,
        ),
    )
    if code_concept:
        return code_concept
    return normalized


def _concept_suggestion_from_code(
    code: str,
    *,
    confidence: Any = 0.75,
    evidence_level: Any = "C",
    relation_role: Any = "supports",
    reason: Any = DEFAULT_CONCEPT_SUGGESTION_REASON,
) -> dict[str, Any] | None:
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code
    node = node_by_code.get(str(code or "").strip())
    if not node or node.node_type != "image_label" or not node.assignable:
        return None
    system = node_by_code.get(node.parent_code or "")
    return {
        "concept_code": node.code,
        "system_name": system.name if system else "",
        "concept_name": node.name,
        "confidence": confidence,
        "evidence_level": evidence_level if evidence_level in {"A", "B", "C"} else "C",
        "relation_role": (
            relation_role
            if relation_role in {"expresses", "supports"}
            else "supports"
        ),
        "reason": str(reason or DEFAULT_CONCEPT_SUGGESTION_REASON),
    }
