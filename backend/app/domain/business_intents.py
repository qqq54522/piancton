from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR
from app.domain.taxonomy_catalog import TaxonomyNode, load_taxonomy_catalog

BUSINESS_INTENTS_PATH = PROJECT_DIR / "taxonomy" / "business_intents.json"


@dataclass(frozen=True)
class BusinessIntent:
    code: str
    name: str
    target_system_code: str
    target_label_code: str
    phrases: tuple[str, ...]
    pain_points: tuple[str, ...]
    must_have_concepts: tuple[str, ...]
    nice_to_have_concepts: tuple[str, ...]
    exclude_concepts: tuple[str, ...]
    result_policy: str


@dataclass(frozen=True)
class BusinessIntentCatalog:
    version: str
    intents: tuple[BusinessIntent, ...]

    @property
    def intent_by_code(self) -> dict[str, BusinessIntent]:
        return {intent.code: intent for intent in self.intents}


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _intent(payload: dict[str, Any]) -> BusinessIntent:
    return BusinessIntent(
        code=str(payload["code"]).strip(),
        name=str(payload["name"]).strip(),
        target_system_code=str(payload["target_system_code"]).strip(),
        target_label_code=str(payload["target_label_code"]).strip(),
        phrases=_strings(payload.get("phrases")),
        pain_points=_strings(payload.get("pain_points")),
        must_have_concepts=_strings(payload.get("must_have_concepts")),
        nice_to_have_concepts=_strings(payload.get("nice_to_have_concepts")),
        exclude_concepts=_strings(payload.get("exclude_concepts")),
        result_policy=str(payload.get("result_policy") or "").strip(),
    )


def _validate(catalog: BusinessIntentCatalog) -> None:
    if not catalog.version:
        raise ValueError("业务意图目录缺少版本")
    codes = [intent.code for intent in catalog.intents]
    if len(codes) != len(set(codes)):
        raise ValueError("业务意图目录存在重复 code")

    taxonomy = load_taxonomy_catalog()
    node_by_code = taxonomy.node_by_code
    for intent in catalog.intents:
        if not intent.name:
            raise ValueError(f"业务意图缺少名称：{intent.code}")
        system = node_by_code.get(intent.target_system_code)
        if not system or system.node_type != "system":
            raise ValueError(f"业务意图目标体系无效：{intent.code}")
        label = node_by_code.get(intent.target_label_code)
        if not label or label.node_type != "image_label":
            raise ValueError(f"业务意图目标标签无效：{intent.code}")
        if label.parent_code != system.code:
            raise ValueError(f"业务意图目标体系与标签不匹配：{intent.code}")
        if not any([intent.phrases, intent.pain_points, intent.must_have_concepts]):
            raise ValueError(f"业务意图缺少匹配材料：{intent.code}")


@lru_cache
def load_business_intents(path: Path = BUSINESS_INTENTS_PATH) -> BusinessIntentCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    catalog = BusinessIntentCatalog(
        version=str(raw.get("version") or "").strip(),
        intents=tuple(_intent(item) for item in raw.get("intents", [])),
    )
    _validate(catalog)
    return catalog


def render_business_intents_for_prompt(
    catalog: BusinessIntentCatalog | None = None,
) -> str:
    selected = catalog or load_business_intents()
    taxonomy = load_taxonomy_catalog()
    node_by_code = taxonomy.node_by_code
    lines = [f"# 业务意图目录（版本 {selected.version}）"]
    for intent in selected.intents:
        system = node_by_code[intent.target_system_code]
        label = node_by_code[intent.target_label_code]
        lines.append(f"\n## {intent.code} / {intent.name}")
        lines.append(f"目标标签：{_display_name(system, label)}")
        if intent.phrases:
            lines.append(f"- 功能表达：{'、'.join(intent.phrases)}")
        if intent.pain_points:
            lines.append(f"- 家长痛点：{'、'.join(intent.pain_points)}")
        if intent.must_have_concepts:
            lines.append(f"- 必须概念：{'、'.join(intent.must_have_concepts)}")
        if intent.exclude_concepts:
            lines.append(f"- 排除概念：{'、'.join(intent.exclude_concepts)}")
    return "\n".join(lines)


def target_display_name(intent: BusinessIntent) -> str:
    taxonomy = load_taxonomy_catalog()
    node_by_code = taxonomy.node_by_code
    return _display_name(
        node_by_code[intent.target_system_code],
        node_by_code[intent.target_label_code],
    )


def target_label(intent: BusinessIntent) -> TaxonomyNode:
    return load_taxonomy_catalog().node_by_code[intent.target_label_code]


def _display_name(system: TaxonomyNode, label: TaxonomyNode) -> str:
    return f"{system.name} > {label.name}"
