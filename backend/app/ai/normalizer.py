from __future__ import annotations

from typing import Any

from app.ai.contracts import ModelRequest
from app.domain.evidence_points import load_evidence_point_catalog
from app.domain.proof_points import load_proof_point_catalog, semantic_text
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.schemas.ai import SEARCH_QUERY_TYPES

# 模型历史上会自造 query_type；这里把旧写法映射进封闭枚举，未知值按候选数量兜底。
QUERY_TYPE_ALIASES = {
    "single_intent_search": "business_intent_search",
    "pain_point_search": "business_intent_search",
    "feature_search": "business_intent_search",
    "keyword_search": "business_intent_search",
    "multi_intent_search": "multi_business_intent_search",
    "exploratory_search": "exploratory_business_intent_search",
    "browse_search": "exploratory_business_intent_search",
    "ambiguous_search": "ambiguous_business_intent_search",
    "visual_search": "visual_scene_search",
    "scene_search": "visual_scene_search",
    "unknown": "no_reliable_intent_search",
}

SYSTEM_CODE_ALIASES = {
    "sync_school": "sync_school",
    "同步校内": "sync_school",
    "校内同步": "sync_school",
    "校内": "sync_school",
    "sync_exam": "sync_exam",
    "同步考点": "sync_exam",
    "考点同步": "sync_exam",
    "考点": "sync_exam",
    "sync_cultivation": "sync_cultivation",
    "同步培养": "sync_cultivation",
    "长期培养": "sync_cultivation",
    "培养": "sync_cultivation",
    "sync_planning": "sync_planning",
    "同步规划": "sync_planning",
    "学习规划": "sync_planning",
    "规划": "sync_planning",
    "sync_self_study": "sync_self_study",
    "同步自学": "sync_self_study",
    "自学": "sync_self_study",
    "sync_companion": "sync_companion",
    "同步伴学": "sync_companion",
    "伴学": "sync_companion",
}

ROUTE_TYPE_ALIASES = {
    "single": "single_system",
    "single_intent": "single_system",
    "single_business": "single_system",
    "multi": "multi_system",
    "multi_intent": "multi_system",
    "ambiguous": "ambiguous_system",
    "visual": "visual_scene",
    "visual_search": "visual_scene",
    "unknown": "no_reliable_system",
    "no_reliable": "no_reliable_system",
}

DEFAULT_CONCEPT_SUGGESTION_REASON = (
    "模型返回稳定 code，系统已转换为业务概念建议；模型未提供具体适配证据和相邻概念边界。"
)
STRING_CONCEPT_SUGGESTION_REASON = (
    "模型以简写形式返回，系统已转换为业务概念建议；模型未提供具体适配证据和相邻概念边界。"
)


def normalize_model_payload(
    request: ModelRequest,
    payload: dict[str, Any],
    *,
    concept_display_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Normalize tolerated vendor/model deviations before schema validation.

    This is still a strict boundary: services validate the normalized payload
    against Pydantic schemas, and invalid model output becomes a domain error.
    """

    if request.task == "search_system_routing":
        return _normalize_system_routing_payload(payload, request.input_text or "")
    if request.task == "search_candidate_review":
        return _normalize_candidate_review_payload(payload)
    if request.task == "search_result_recommendation_reason":
        return _normalize_result_recommendation_reason_payload(payload)
    if request.task in {
        "search_intent_understanding",
        "search_proof_point_understanding",
    }:
        return _normalize_search_understanding_payload(
            payload,
            original_query=_query_from_input_text(request.input_text or ""),
            concept_display_names=concept_display_names,
        )
    if request.task == "asset_search_phrase_generation":
        return _normalize_asset_search_phrase_payload(payload)
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
            _normalize_concept_suggestion(
                item,
                concept_display_names=concept_display_names,
            )
            for item in concept_suggestions
            if item
        ]
        normalized["concept_suggestions"] = [
            item for item in normalized_concept_suggestions if item
        ]

    return normalized


def _normalize_result_recommendation_reason_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    raw_reasons = (
        payload.get("reasons")
        or payload.get("recommendations")
        or payload.get("results")
        or []
    )
    reasons: list[dict[str, str]] = []
    if isinstance(raw_reasons, list):
        for item in raw_reasons:
            if not isinstance(item, dict):
                continue
            image_id = str(
                item.get("image_id")
                or item.get("imageId")
                or item.get("id")
                or ""
            ).strip()
            reason = str(
                item.get("reason")
                or item.get("recommendation_reason")
                or item.get("rationale")
                or ""
            ).strip()
            if image_id and reason:
                reasons.append({"image_id": image_id, "reason": reason})
    return {
        "reasons": reasons,
        "generation_strategy": str(
            payload.get("generation_strategy")
            or payload.get("strategy")
            or payload.get("search_strategy")
            or ""
        ),
    }


def _normalize_candidate_review_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_decisions = (
        payload.get("decisions")
        or payload.get("reviews")
        or payload.get("candidates")
        or []
    )
    decisions = []
    if isinstance(raw_decisions, list):
        for item in raw_decisions:
            decision = _normalize_candidate_review_decision(item)
            if decision is not None:
                decisions.append(decision)
    return {
        "decisions": decisions,
        "review_strategy": str(
            payload.get("review_strategy")
            or payload.get("strategy")
            or payload.get("search_strategy")
            or ""
        ),
    }


def _normalize_candidate_review_decision(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    image_id = str(
        value.get("image_id")
        or value.get("imageId")
        or value.get("id")
        or ""
    ).strip()
    if not image_id:
        return None
    raw_decision = str(
        value.get("decision")
        or value.get("action")
        or value.get("verdict")
        or ""
    ).strip().lower()
    decision_aliases = {
        "pass": "keep",
        "accept": "keep",
        "matched": "keep",
        "relevant": "keep",
        "lower": "demote",
        "weak": "demote",
        "maybe": "demote",
        "reject": "exclude",
        "remove": "exclude",
        "irrelevant": "exclude",
    }
    decision = decision_aliases.get(raw_decision, raw_decision)
    if decision not in {"keep", "demote", "exclude"}:
        decision = "demote"
    return {
        "image_id": image_id,
        "decision": decision,
        "confidence": _normalize_weight(
            value.get("confidence") or value.get("score"),
            0.75,
        ),
        "reason": str(
            value.get("reason")
            or value.get("rationale")
            or value.get("evidence")
            or "模型返回候选复核简写，系统已补齐结构字段。"
        ),
    }


def _normalize_system_routing_payload(
    payload: dict[str, Any],
    original_query: str,
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["original_query"] = (
        str(normalized.get("original_query") or original_query).strip()
    )
    route_type = str(normalized.get("route_type") or "").strip()
    normalized["route_type"] = ROUTE_TYPE_ALIASES.get(route_type, route_type)

    candidates = normalized.get("candidate_systems")
    if not isinstance(candidates, list):
        candidates = (
            normalized.get("systems")
            or normalized.get("candidateSystems")
            or normalized.get("candidates")
        )
    normalized_candidates = []
    if isinstance(candidates, list):
        for index, item in enumerate(candidates):
            candidate = _normalize_system_candidate(item, index)
            if candidate is not None:
                normalized_candidates.append(candidate)
    normalized["candidate_systems"] = normalized_candidates

    if not normalized.get("route_type"):
        if len(normalized_candidates) == 1:
            normalized["route_type"] = "single_system"
        elif len(normalized_candidates) > 1:
            normalized["route_type"] = "ambiguous_system"
        else:
            normalized["route_type"] = "no_reliable_system"

    excluded = normalized.get("excluded_systems")
    normalized["excluded_systems"] = excluded if isinstance(excluded, list) else []
    return normalized


def _normalize_system_candidate(value: Any, index: int) -> dict[str, Any] | None:
    if isinstance(value, str):
        code = _normalize_system_code(value)
        if not code:
            return None
        return {
            "code": code,
            "relation": "primary" if index == 0 else "related",
            "reason": "模型返回体系简写，系统已按封闭体系 code 归一化。",
            "weight": 0.9 if index == 0 else 0.75,
        }
    if not isinstance(value, dict):
        return None
    normalized = dict(value)
    raw_code = (
        normalized.get("code")
        or normalized.get("system_code")
        or normalized.get("systemCode")
        or normalized.get("name")
        or normalized.get("system")
    )
    code = _normalize_system_code(str(raw_code or ""))
    if not code:
        return None
    relation = str(normalized.get("relation") or "").strip()
    normalized.update(
        code=code,
        relation=relation if relation in {"primary", "related"} else (
            "primary" if index == 0 else "related"
        ),
        reason=str(normalized.get("reason") or "模型返回体系候选，系统已归一化。"),
        weight=_normalize_weight(normalized.get("weight"), 0.9 if index == 0 else 0.75),
    )
    return normalized


def _normalize_system_code(value: str) -> str | None:
    key = value.strip()
    if not key:
        return None
    return SYSTEM_CODE_ALIASES.get(key)


def _normalize_weight(value: Any, default: float) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, weight))


def _normalize_asset_search_phrase_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    phrases = normalized.get("phrases")
    if not isinstance(phrases, list):
        phrases = normalized.get("asset_search_phrases")
    if not isinstance(phrases, list):
        profile = normalized.get("semantic_profile")
        phrases = profile.get("asset_search_phrases") if isinstance(profile, dict) else []
    return {"phrases": phrases if isinstance(phrases, list) else []}


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


def _normalize_search_understanding_payload(
    payload: dict[str, Any],
    *,
    original_query: str,
    concept_display_names: dict[str, str] | None,
) -> dict[str, Any]:
    catalog = load_taxonomy_catalog()
    normalized = dict(payload)
    normalized["original_query"] = str(
        normalized.get("original_query")
        or normalized.get("originalQuery")
        or original_query
    ).strip()
    normalized["normalized_query"] = str(
        normalized.get("normalized_query")
        or normalized.get("normalizedQuery")
        or normalized.get("normalized")
        or normalized.get("query")
        or normalized["original_query"]
    ).strip()
    normalized["search_intent"] = str(
        normalized.get("search_intent")
        or normalized.get("searchIntent")
        or normalized.get("intent")
        or normalized.get("search_strategy")
        or normalized["normalized_query"]
    ).strip()

    expanded_terms = normalized.get("expanded_terms")
    if isinstance(expanded_terms, list):
        normalized["expanded_terms"] = [
            _normalize_search_term(
                item,
                catalog.node_by_code,
                concept_display_names,
            )
            for item in expanded_terms
            if item
        ]

    concepts = normalized.get("matched_business_concepts")
    if isinstance(concepts, list):
        normalized["matched_business_concepts"] = [
            _normalize_search_concept(
                item,
                catalog.node_by_code,
                concept_display_names,
            )
            for item in concepts
            if item
        ]

    proof_points = normalized.get("matched_proof_points")
    if isinstance(proof_points, list):
        proof_catalog = load_proof_point_catalog().by_code
        normalized["matched_proof_points"] = [
            item
            for value in proof_points
            if (item := _normalize_proof_point(value, proof_catalog)) is not None
        ]

    evidence_points = normalized.get("matched_evidence_points")
    if isinstance(evidence_points, list):
        evidence_catalog = load_evidence_point_catalog().by_code
        normalized["matched_evidence_points"] = [
            item
            for value in evidence_points
            if (item := _normalize_evidence_point(value, evidence_catalog)) is not None
        ]

    excluded_concepts = normalized.get("excluded_concepts")
    if isinstance(excluded_concepts, list):
        normalized["excluded_concepts"] = [
            _display_name_from_code(
                str(item),
                catalog.node_by_code,
                concept_display_names,
            )
            or str(item)
            for item in excluded_concepts
        ]
    normalized["query_type"] = _normalize_query_type(
        str(
            normalized.get("query_type")
            or normalized.get("query_status")
            or normalized.get("query_state")
            or ""
        ).strip(),
        normalized.get("matched_business_concepts"),
    )
    return normalized


def _query_from_input_text(value: str) -> str:
    marker = "原始查询："
    if marker in value:
        return value.rsplit(marker, 1)[-1].strip()
    return value.strip()


def _normalize_query_type(value: str, matched_concepts: Any) -> str:
    if value in SEARCH_QUERY_TYPES:
        return value
    alias = QUERY_TYPE_ALIASES.get(value)
    if alias:
        return alias
    count = len(matched_concepts) if isinstance(matched_concepts, list) else 0
    if count > 1:
        # 未确认的多候选不允许触发多卖点硬路由，按待消歧处理。
        return "ambiguous_business_intent_search"
    if count == 1:
        return "business_intent_search"
    return "no_reliable_intent_search"


def _normalize_search_term(
    value: Any,
    node_by_code: dict[str, Any],
    concept_display_names: dict[str, str] | None,
) -> Any:
    if isinstance(value, str):
        term = _display_name_from_code(value, node_by_code, concept_display_names) or value.strip()
        return {
            "term": term,
            "relation": "strong",
            "reason": "模型返回字符串扩展词，系统已补齐结构字段。",
            "weight": 0.85,
        }
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    term = str(
        normalized.get("term")
        or normalized.get("normalized")
        or normalized.get("source")
        or normalized.get("text")
        or ""
    ).strip()
    normalized["term"] = (
        _display_name_from_code(term, node_by_code, concept_display_names) or term
    )
    relation = str(normalized.get("relation") or "").strip()
    normalized["relation"] = (
        relation if relation in {"exact", "strong", "medium", "weak"} else "strong"
    )
    normalized["reason"] = str(
        normalized.get("reason")
        or normalized.get("source")
        or "模型返回简写扩展词，系统已补齐结构字段。"
    )
    normalized["weight"] = _normalize_weight(
        normalized.get("weight") or normalized.get("score"),
        0.85,
    )
    return normalized


def _normalize_search_concept(
    value: Any,
    node_by_code: dict[str, Any],
    concept_display_names: dict[str, str] | None,
) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    concept = str(
        normalized.get("concept")
        or normalized.get("code")
        or normalized.get("concept_code")
        or normalized.get("conceptCode")
        or normalized.get("name")
        or ""
    ).strip()
    normalized["concept"] = (
        _display_name_from_code(concept, node_by_code, concept_display_names) or concept
    )
    relation = str(normalized.get("relation") or "").strip()
    normalized["relation"] = relation if relation in {"direct", "related", "fallback"} else "direct"
    evidence = normalized.get("evidence")
    evidence_text = "、".join(str(item) for item in evidence) if isinstance(evidence, list) else ""
    normalized["reason"] = str(
        normalized.get("reason")
        or evidence_text
        or "模型返回卖点简写，系统已补齐结构字段。"
    )
    normalized["weight"] = _normalize_weight(
        normalized.get("weight") or normalized.get("confidence") or normalized.get("score"),
        0.9,
    )
    return normalized


def _normalize_proof_point(value: Any, by_code: dict[str, Any]) -> Any:
    if not isinstance(value, dict):
        return None
    point = by_code.get(str(value.get("code") or "").strip())
    if point is None:
        return None
    normalized = dict(value)
    allowed_evidence = {
        semantic_text(item): item
        for item in (*point.search_terms, *point.asset_terms)
        if semantic_text(item)
    }
    raw_evidence = normalized.get("evidence_terms")
    evidence_terms = []
    if isinstance(raw_evidence, list):
        for item in raw_evidence:
            canonical = allowed_evidence.get(semantic_text(str(item)))
            if canonical and canonical not in evidence_terms:
                evidence_terms.append(canonical)
    normalized.update(
        code=point.code,
        concept_code=point.concept_code,
        name=point.name,
        evidence_terms=evidence_terms[:3],
    )
    return normalized


def _normalize_evidence_point(value: Any, by_code: dict[str, Any]) -> Any:
    if not isinstance(value, dict):
        return None
    point = by_code.get(str(value.get("code") or "").strip())
    if point is None:
        return None
    normalized = dict(value)
    normalized.update(
        code=point.code,
        proof_point_code=point.proof_point_code,
        concept_code=point.concept_code,
        name=point.name,
    )
    return normalized


def _display_name_from_code(
    code: str,
    node_by_code: dict[str, Any],
    concept_display_names: dict[str, str] | None = None,
) -> str | None:
    runtime_name = (concept_display_names or {}).get(code.strip())
    if runtime_name:
        return runtime_name
    node = node_by_code.get(code.strip())
    if not node:
        return None
    if node.parent_code and node.parent_code in node_by_code:
        parent = node_by_code[node.parent_code]
        return f"{parent.name} > {node.name}"
    return node.name


def _normalize_concept_suggestion(
    value: Any,
    *,
    concept_display_names: dict[str, str] | None,
) -> Any:
    if isinstance(value, dict):
        return _normalize_concept_suggestion_dict(
            value,
            concept_display_names=concept_display_names,
        )
    if not isinstance(value, str):
        return value
    system, separator, label = value.partition(">")
    label = label.strip() if separator else system.strip()
    system = system.strip() if separator else ""
    code_concept = _concept_suggestion_from_code(
        label,
        concept_display_names=concept_display_names,
    )
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


def _normalize_concept_suggestion_dict(
    value: dict[str, Any],
    *,
    concept_display_names: dict[str, str] | None,
) -> dict[str, Any] | None:
    normalized = dict(value)
    candidate_code = str(normalized.get("concept_code") or normalized.get("code") or "").strip()
    if not candidate_code:
        for key in ("concept_name", "name"):
            candidate = str(normalized.get(key) or "").strip()
            if _concept_suggestion_from_code(
                candidate,
                concept_display_names=concept_display_names,
            ):
                candidate_code = candidate
                break
    code_concept = _concept_suggestion_from_code(
        candidate_code,
        concept_display_names=concept_display_names,
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
    concept_display_names: dict[str, str] | None = None,
    confidence: Any = 0.75,
    evidence_level: Any = "C",
    relation_role: Any = "supports",
    reason: Any = DEFAULT_CONCEPT_SUGGESTION_REASON,
) -> dict[str, Any] | None:
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code
    cleaned_code = str(code or "").strip()
    node = node_by_code.get(cleaned_code)
    if not node:
        display_name = (concept_display_names or {}).get(cleaned_code)
        if not display_name:
            return None
        system_name, separator, concept_name = display_name.partition(">")
        return {
            "concept_code": cleaned_code,
            "system_name": system_name.strip() if separator else "",
            "concept_name": concept_name.strip() if separator else system_name.strip(),
            "confidence": confidence,
            "evidence_level": evidence_level if evidence_level in {"A", "B", "C"} else "C",
            "relation_role": (
                relation_role if relation_role in {"expresses", "supports"} else "supports"
            ),
            "reason": str(reason or DEFAULT_CONCEPT_SUGGESTION_REASON),
        }
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
            relation_role if relation_role in {"expresses", "supports"} else "supports"
        ),
        "reason": str(reason or DEFAULT_CONCEPT_SUGGESTION_REASON),
    }
