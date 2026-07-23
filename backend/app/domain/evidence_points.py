from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.core.config import PROJECT_DIR
from app.domain.proof_points import load_proof_point_catalog, proof_text_score

EVIDENCE_POINTS_PATH = (
    PROJECT_DIR
    / "skills"
    / "understand-image-search-intent"
    / "references"
    / "evidence-points.json"
)


@dataclass(frozen=True)
class EvidencePointSourcePathNode:
    level: str
    label: str


@dataclass(frozen=True)
class EvidencePointDefinition:
    code: str
    name: str
    proof_point_code: str
    system_code: str
    concept_code: str
    source_ref: str
    search_terms: tuple[str, ...] = ()
    source_paths: tuple[tuple[EvidencePointSourcePathNode, ...], ...] = ()
    review_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePointCatalog:
    version: str
    points: tuple[EvidencePointDefinition, ...]

    @property
    def by_code(self) -> dict[str, EvidencePointDefinition]:
        return {item.code: item for item in self.points}


def render_evidence_points_for_prompt(system_codes: tuple[str, ...]) -> str:
    selected = [
        item
        for item in load_evidence_point_catalog().points
        if item.system_code in system_codes
    ]
    lines = [
        "# 候选体系证据表达点目录",
        "仅在父卖点已命中时选择；不得自造 code，也不得把它升级成卖点。",
    ]
    for item in selected:
        aliases = "、".join(item.search_terms)
        suffix = f"；近义入口：{aliases}" if aliases else ""
        lines.append(
            f"- `{item.code}`｜父证明点 `{item.proof_point_code}`｜"
            f"父卖点 `{item.concept_code}`｜{item.name}{suffix}"
        )
    return "\n".join(lines)


@lru_cache
def load_evidence_point_catalog(
    path: Path = EVIDENCE_POINTS_PATH,
) -> EvidencePointCatalog:
    raw_text = path.read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    proof_points = load_proof_point_catalog().by_code
    points: list[EvidencePointDefinition] = []
    for payload in raw.get("points", []):
        proof_code = str(payload.get("proofPointCode") or "").strip()
        proof = proof_points.get(proof_code)
        if proof is None:
            raise ValueError(f"证据表达点父证明点无效：{proof_code}")
        points.append(
            EvidencePointDefinition(
                code=str(payload.get("code") or "").strip(),
                name=str(payload.get("name") or "").strip(),
                proof_point_code=proof_code,
                system_code=proof.system_code,
                concept_code=proof.concept_code,
                source_ref=str(payload.get("sourceRef") or "").strip(),
                search_terms=tuple(
                    str(value).strip()
                    for value in payload.get("searchTerms", [])
                    if str(value).strip()
                ),
                source_paths=tuple(
                    tuple(
                        EvidencePointSourcePathNode(
                            level=str(node.get("level") or "").strip(),
                            label=str(node.get("label") or "").strip(),
                        )
                        for node in path_nodes
                        if isinstance(node, dict)
                    )
                    for path_nodes in payload.get("sourcePaths", [])
                    if isinstance(path_nodes, list)
                ),
                review_notes=tuple(
                    str(value).strip()
                    for value in payload.get("reviewNotes", [])
                    if str(value).strip()
                ),
            )
        )
    codes = [item.code for item in points]
    if not points or any(not item.code or not item.name for item in points):
        raise ValueError("证据表达点目录存在空 code 或名称")
    if len(codes) != len(set(codes)):
        raise ValueError("证据表达点 code 必须全局唯一")
    allowed_path_levels = {
        "system",
        "selling_point",
        "proof_group",
        "evidence_expression",
    }
    for point in points:
        if any(not note for note in point.review_notes):
            raise ValueError(f"证据表达点人工校准说明不能为空：{point.code}")
        for source_path in point.source_paths:
            if not source_path:
                raise ValueError(f"证据表达点来源路径不能为空：{point.code}")
            if any(
                not node.label or node.level not in allowed_path_levels
                for node in source_path
            ):
                raise ValueError(f"证据表达点来源路径节点无效：{point.code}")
    digest = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:12]
    return EvidencePointCatalog(
        version=f"{raw.get('version', '')}+evidence-{digest}",
        points=tuple(points),
    )


def best_query_evidence_point_match(
    query: str,
    point: EvidencePointDefinition,
) -> tuple[float, str | None]:
    best_score, best_value = 0.0, None
    for value in (point.name, *point.search_terms):
        score = proof_text_score(query, value)
        if score > best_score:
            best_score, best_value = score, value
    return best_score, best_value
