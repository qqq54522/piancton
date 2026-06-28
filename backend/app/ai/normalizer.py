from __future__ import annotations

from typing import Any

from app.ai.contracts import ModelRequest
from app.domain.taxonomy_catalog import load_taxonomy_catalog

DEFAULT_SECONDARY_LABEL_REASON = (
    "模型返回稳定 code，系统已转换为标准二级标签结构；"
    "模型未提供具体适配证据和相邻概念边界。"
)
STRING_SECONDARY_LABEL_REASON = (
    "模型以简写形式返回，系统已转换为标准二级标签结构；"
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
    normalized["image_type"] = _normalize_image_type(normalized.get("image_type"))

    content_tags = normalized.get("content_tags")
    if isinstance(content_tags, list):
        normalized["content_tags"] = [
            _normalize_content_tag(item)
            for item in content_tags
            if item
        ]

    secondary_labels = normalized.get("secondary_labels")
    if isinstance(secondary_labels, list):
        normalized_secondary_labels = [
            _normalize_secondary_label(item)
            for item in secondary_labels
            if item
        ]
        normalized["secondary_labels"] = [
            item for item in normalized_secondary_labels if item
        ]

    return normalized


def _normalize_search_understanding_payload(payload: dict[str, Any]) -> dict[str, Any]:
    catalog = load_taxonomy_catalog()
    normalized = dict(payload)

    expanded_tags = normalized.get("expanded_level1_tags")
    if isinstance(expanded_tags, list):
        normalized["expanded_level1_tags"] = [
            _normalize_search_tag(item, catalog.node_by_code)
            for item in expanded_tags
            if item
        ]

    categories = normalized.get("matched_level2_categories")
    if isinstance(categories, list):
        normalized["matched_level2_categories"] = [
            _normalize_search_category(item, catalog.node_by_code)
            for item in categories
            if item
        ]

    exclude_tags = normalized.get("exclude_tags")
    if isinstance(exclude_tags, list):
        normalized["exclude_tags"] = [
            _display_name_from_code(str(item), catalog.node_by_code) or str(item)
            for item in exclude_tags
        ]
    return normalized


def _normalize_search_tag(
    value: Any,
    node_by_code: dict[str, Any],
) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    tag = str(normalized.get("tag") or "").strip()
    normalized["tag"] = _display_name_from_code(tag, node_by_code) or tag
    return normalized


def _normalize_search_category(
    value: Any,
    node_by_code: dict[str, Any],
) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    category = str(normalized.get("category") or "").strip()
    normalized["category"] = _display_name_from_code(category, node_by_code) or category
    return normalized


def _display_name_from_code(code: str, node_by_code: dict[str, Any]) -> str | None:
    node = node_by_code.get(code.strip())
    if not node:
        return None
    if node.parent_code and node.parent_code in node_by_code:
        parent = node_by_code[node.parent_code]
        return f"{parent.name} > {node.name}"
    return node.name


def _normalize_content_tag(value: Any) -> Any:
    if isinstance(value, str):
        return {"tag": value.strip(), "confidence": 0.75, "dimension": "其他"}
    if isinstance(value, dict):
        normalized = dict(value)
        if "tag" not in normalized:
            candidate = (
                normalized.get("tag_name")
                or normalized.get("name")
                or normalized.get("label")
            )
            if candidate:
                normalized["tag"] = str(candidate).strip()
        normalized["confidence"] = normalized.get("confidence", 0.75)
        normalized["dimension"] = _normalize_content_dimension(
            normalized.get("dimension")
        )
        return normalized
    return value


def _normalize_image_type(value: Any) -> str:
    if value in {"function", "scene_emotion", "scene_functional"}:
        return str(value)
    text = str(value or "")
    if "情绪" in text:
        return "scene_emotion"
    if "场景" in text:
        return "scene_functional"
    return "function"


def _normalize_secondary_label(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_secondary_label_dict(value)
    if not isinstance(value, str):
        return value
    system, separator, label = value.partition(">")
    label = label.strip() if separator else system.strip()
    system = system.strip() if separator else ""
    code_label = _secondary_label_from_code(label)
    if code_label:
        return code_label
    return {
        "system": system,
        "label": label,
        "confidence": 0.75,
        "evidence_level": "C",
        "role": "secondary",
        "reason": STRING_SECONDARY_LABEL_REASON,
    }


def _normalize_secondary_label_dict(value: dict[str, Any]) -> dict[str, Any] | None:
    normalized = dict(value)
    candidate_code = str(
        normalized.get("label_code")
        or normalized.get("code")
        or ""
    ).strip()
    if not candidate_code:
        for key in ("label", "name"):
            candidate = str(normalized.get(key) or "").strip()
            if _secondary_label_from_code(candidate):
                candidate_code = candidate
                break
    code_label = _secondary_label_from_code(
        candidate_code,
        confidence=normalized.get("confidence", 0.75),
        evidence_level=normalized.get("evidence_level", "C"),
        role=normalized.get("role", "secondary"),
        reason=normalized.get(
            "reason",
            DEFAULT_SECONDARY_LABEL_REASON,
        ),
    )
    if code_label:
        return code_label
    return normalized


def _secondary_label_from_code(
    code: str,
    *,
    confidence: Any = 0.75,
    evidence_level: Any = "C",
    role: Any = "secondary",
    reason: Any = DEFAULT_SECONDARY_LABEL_REASON,
) -> dict[str, Any] | None:
    catalog = load_taxonomy_catalog()
    node_by_code = catalog.node_by_code
    node = node_by_code.get(str(code or "").strip())
    if not node or node.node_type != "image_label" or not node.assignable:
        return None
    system = node_by_code.get(node.parent_code or "")
    return {
        "label_code": node.code,
        "system": system.name if system else "",
        "label": node.name,
        "confidence": confidence,
        "evidence_level": evidence_level if evidence_level in {"A", "B", "C"} else "C",
        "role": role if role in {"primary", "secondary"} else "secondary",
        "reason": str(reason or DEFAULT_SECONDARY_LABEL_REASON),
    }


def _normalize_content_dimension(value: Any) -> str:
    aliases = {
        "person": "人物",
        "people": "人物",
        "人物": "人物",
        "relationship": "人物",
        "relation": "人物",
        "关系": "人物",
        "scene": "场景",
        "场景": "场景",
        "object": "物体",
        "物体": "物体",
        "action": "动作",
        "动作": "动作",
        "emotion": "情绪",
        "情绪": "情绪",
        "text": "文字",
        "文字": "文字",
        "style": "视觉风格",
        "visual_style": "视觉风格",
        "视觉风格": "视觉风格",
        "color": "颜色",
        "颜色": "颜色",
        "product_function": "产品功能",
        "function": "产品功能",
        "产品功能": "产品功能",
        "selling_point": "业务卖点",
        "business_selling_point": "业务卖点",
        "业务卖点": "业务卖点",
        "other": "其他",
        "其他": "其他",
    }
    return aliases.get(str(value or "").strip().lower(), "其他")
