from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional

from app.core.config import PROJECT_DIR

CATALOG_PATH = PROJECT_DIR / "taxonomy" / "catalog.json"


@dataclass(frozen=True)
class TaxonomyNode:
    code: str
    name: str
    color: str
    node_type: str
    parent_code: Optional[str]
    assignable: bool
    aliases: tuple[str, ...]
    definition: str
    positive_evidence: tuple[str, ...]
    negative_evidence: tuple[str, ...]


@dataclass(frozen=True)
class CopyPoint:
    code: str
    name: str
    system_code: str
    target_label_codes: tuple[str, ...]


@dataclass(frozen=True)
class TaxonomyCatalog:
    version: str
    nodes: tuple[TaxonomyNode, ...]
    copy_points: tuple[CopyPoint, ...]

    @property
    def node_by_code(self) -> dict[str, TaxonomyNode]:
        return {node.code: node for node in self.nodes}

    @property
    def system_nodes(self) -> tuple[TaxonomyNode, ...]:
        return tuple(node for node in self.nodes if node.node_type == "system")

    @property
    def image_label_nodes(self) -> tuple[TaxonomyNode, ...]:
        return tuple(node for node in self.nodes if node.node_type == "image_label")

    def children_of(self, parent_code: str) -> tuple[TaxonomyNode, ...]:
        return tuple(node for node in self.nodes if node.parent_code == parent_code)

    def ancestor_codes(self, code: str) -> tuple[str, ...]:
        node_by_code = self.node_by_code
        current = node_by_code.get(code)
        ancestors: list[str] = []
        seen = {code}
        while current and current.parent_code:
            if current.parent_code in seen:
                raise ValueError(f"标签目录存在循环：{code}")
            seen.add(current.parent_code)
            ancestors.insert(0, current.parent_code)
            current = node_by_code.get(current.parent_code)
        return tuple(ancestors)


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _node(
    payload: dict[str, Any],
    *,
    node_type: str,
    parent_code: Optional[str],
    assignable: bool,
) -> TaxonomyNode:
    return TaxonomyNode(
        code=str(payload["code"]).strip(),
        name=str(payload["name"]).strip(),
        color=str(payload.get("color") or "#6B7280").strip(),
        node_type=node_type,
        parent_code=parent_code,
        assignable=assignable,
        aliases=_strings(payload.get("aliases")),
        definition=str(payload.get("definition") or "").strip(),
        positive_evidence=_strings(payload.get("positive_evidence")),
        negative_evidence=_strings(payload.get("negative_evidence")),
    )


def _validate(catalog: TaxonomyCatalog) -> None:
    if not catalog.version:
        raise ValueError("标签目录缺少版本")
    codes = [node.code for node in catalog.nodes]
    if len(codes) != len(set(codes)):
        raise ValueError("标签目录存在重复 code")
    names_by_parent: set[tuple[Optional[str], str]] = set()
    node_by_code = catalog.node_by_code
    for node in catalog.nodes:
        key = (node.parent_code, node.name)
        if key in names_by_parent:
            raise ValueError(f"标签目录同级名称重复：{node.name}")
        names_by_parent.add(key)
        if node.parent_code and node.parent_code not in node_by_code:
            raise ValueError(f"标签父节点不存在：{node.code} -> {node.parent_code}")
        catalog.ancestor_codes(node.code)

    copy_codes = [point.code for point in catalog.copy_points]
    if len(copy_codes) != len(set(copy_codes)):
        raise ValueError("文案卖点目录存在重复 code")
    for point in catalog.copy_points:
        system = node_by_code.get(point.system_code)
        if not system or system.node_type != "system":
            raise ValueError(f"文案卖点体系无效：{point.code}")
        for target_code in point.target_label_codes:
            target = node_by_code.get(target_code)
            if not target or target.node_type != "image_label":
                raise ValueError(f"文案卖点映射无效：{point.code} -> {target_code}")


@lru_cache
def load_taxonomy_catalog(path: Path = CATALOG_PATH) -> TaxonomyCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    nodes: list[TaxonomyNode] = []
    for system_payload in raw.get("systems", []):
        system = _node(
            system_payload,
            node_type="system",
            parent_code=None,
            assignable=False,
        )
        nodes.append(system)
        for label_payload in system_payload.get("image_labels", []):
            nodes.append(
                _node(
                    label_payload,
                    node_type="image_label",
                    parent_code=system.code,
                    assignable=bool(label_payload.get("assignable", True)),
                )
            )
    copy_points = tuple(
        CopyPoint(
            code=str(item["code"]).strip(),
            name=str(item["name"]).strip(),
            system_code=str(item["system_code"]).strip(),
            target_label_codes=_strings(item.get("target_label_codes")),
        )
        for item in raw.get("copy_points", [])
    )
    catalog = TaxonomyCatalog(
        version=str(raw.get("version") or "").strip(),
        nodes=tuple(nodes),
        copy_points=copy_points,
    )
    _validate(catalog)
    return catalog


def render_catalog_for_prompt(
    *,
    include_copy_points: bool = False,
    nodes: Optional[Iterable[TaxonomyNode]] = None,
) -> str:
    catalog = load_taxonomy_catalog()
    selected_nodes = tuple(nodes) if nodes is not None else catalog.nodes
    lines = [f"# 权威标签目录（版本 {catalog.version}）"]
    for system in catalog.system_nodes:
        if system not in selected_nodes and nodes is not None:
            continue
        lines.append(f"\n## {system.code} / {system.name}")
        lines.append(system.definition)
        for label in catalog.children_of(system.code):
            if label not in selected_nodes and nodes is not None:
                continue
            lines.append(f"- `{label.code}` / {label.name}: {label.definition}")
            if label.aliases:
                lines.append(f"  - 常见表达：{'、'.join(label.aliases)}")
            if label.positive_evidence:
                lines.append(f"  - 正向证据：{'、'.join(label.positive_evidence)}")
            if label.negative_evidence:
                lines.append(f"  - 排除边界：{'、'.join(label.negative_evidence)}")
    if include_copy_points:
        lines.append("\n# 文案卖点映射")
        for point in catalog.copy_points:
            targets = "、".join(point.target_label_codes)
            lines.append(f"- `{point.code}` / {point.name} -> {targets}")
    lines.append("\n模型只能返回以上目录中存在的稳定 code，不得创造新的业务标签。")
    return "\n".join(lines)
