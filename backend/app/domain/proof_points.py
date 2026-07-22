from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from app.core.config import PROJECT_DIR

REFERENCE_DIR = PROJECT_DIR / "skills" / "understand-image-search-intent" / "references"
SELLING_POINT_MAP_PATH = REFERENCE_DIR / "selling-point-map.json"

_SELLING_POINT_HEADING = re.compile(r"^##\s+`([^`]+)`[：:]\s*(.+)$")
_PROOF_POINT_HEADING = re.compile(r"^####\s+`(pp_[^`]+)`[：:]\s*(.+)$")
_BACKTICK_VALUE = re.compile(r"`([^`]+)`")


@dataclass(frozen=True)
class ProofPointDefinition:
    code: str
    name: str
    system_code: str
    concept_code: str
    claim: str
    search_terms: tuple[str, ...]
    asset_terms: tuple[str, ...]


@dataclass(frozen=True)
class ProofPointCatalog:
    version: str
    points: tuple[ProofPointDefinition, ...]

    @property
    def by_code(self) -> dict[str, ProofPointDefinition]:
        return {item.code: item for item in self.points}


def _split_terms(value: str) -> tuple[str, ...]:
    return tuple(
        item.strip().strip("。；;")
        for item in re.split(r"[、，,；;]", value)
        if item.strip().strip("。；;")
    )


def _proof_point_from_block(
    *,
    code: str,
    name: str,
    system_code: str,
    concept_code: str,
    lines: list[str],
) -> ProofPointDefinition:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s+([^：:]+)[：:]\s*(.*)$", line)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    asset_value = fields.get("当前素材线索", "")
    asset_terms = tuple(_BACKTICK_VALUE.findall(asset_value))
    return ProofPointDefinition(
        code=code,
        name=name.strip(),
        system_code=system_code,
        concept_code=concept_code,
        claim=fields.get("论断", ""),
        search_terms=_split_terms(fields.get("搜索语言", "")),
        asset_terms=asset_terms,
    )


def _parse_reference(
    path: Path,
    *,
    system_code: str,
    selling_point_codes: set[str],
) -> list[ProofPointDefinition]:
    points: list[ProofPointDefinition] = []
    concept_code = ""
    current: tuple[str, str, str] | None = None
    block: list[str] = []

    def finish() -> None:
        nonlocal current, block
        if current is not None:
            code, name, parent_code = current
            points.append(
                _proof_point_from_block(
                    code=code,
                    name=name,
                    system_code=system_code,
                    concept_code=parent_code,
                    lines=block,
                )
            )
        current, block = None, []

    for line in path.read_text(encoding="utf-8").splitlines():
        selling_point = _SELLING_POINT_HEADING.match(line)
        if selling_point and selling_point.group(1) in selling_point_codes:
            finish()
            concept_code = selling_point.group(1)
            continue
        proof_point = _PROOF_POINT_HEADING.match(line)
        if proof_point:
            finish()
            if not concept_code:
                raise ValueError(f"证明点缺少父卖点：{path.name} {proof_point.group(1)}")
            current = (proof_point.group(1), proof_point.group(2), concept_code)
            continue
        if current is not None:
            block.append(line)
    finish()
    return points


@lru_cache
def load_proof_point_catalog(
    map_path: Path = SELLING_POINT_MAP_PATH,
) -> ProofPointCatalog:
    raw = json.loads(map_path.read_text(encoding="utf-8"))
    points: list[ProofPointDefinition] = []
    source_parts = [map_path.read_text(encoding="utf-8")]
    for system in raw.get("systems", []):
        reference = REFERENCE_DIR / str(system["reference"])
        source_parts.append(reference.read_text(encoding="utf-8"))
        points.extend(
            _parse_reference(
                reference,
                system_code=str(system["code"]),
                selling_point_codes={str(item["code"]) for item in system.get("sellingPoints", [])},
            )
        )
    codes = [item.code for item in points]
    if len(codes) != len(set(codes)):
        raise ValueError("证明点 code 必须全局唯一")
    digest = hashlib.sha256("\n".join(source_parts).encode("utf-8")).hexdigest()[:12]
    return ProofPointCatalog(
        version=f"{raw.get('version', '')}+proof-{digest}",
        points=tuple(points),
    )


def semantic_text(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”‘’\"'（）()《》<>[]【】-_")
    normalized = "".join(char.lower() for char in value if char not in ignored)
    for source, target in (
        ("5到8", "58"),
        ("五到八", "58"),
        ("微信学习周报", "微信周报"),
        ("做错的题", "错题"),
        ("错的题", "错题"),
        ("收集", "整理"),
        ("归纳", "整理"),
        ("归类", "归档"),
        ("录入", "上传"),
        ("查阅", "查看"),
    ):
        normalized = normalized.replace(source, target)
    return normalized


def proof_text_score(query: str, value: str) -> float:
    needle, candidate = semantic_text(query), semantic_text(value)
    if not needle or not candidate:
        return 0.0
    if needle == candidate:
        return 1.0
    if candidate in needle:
        return 0.97 if len(candidate) >= 4 else 0.88
    if len(needle) >= 4 and needle in candidate:
        return 0.93
    return SequenceMatcher(None, needle, candidate).ratio()


def query_proof_point_score(query: str, point: ProofPointDefinition) -> float:
    score, _ = best_query_proof_point_match(query, point)
    return score


def best_query_proof_point_match(
    query: str,
    point: ProofPointDefinition,
) -> tuple[float, str | None]:
    best_score, best_value = 0.0, None
    for value in (point.name, *point.search_terms, *point.asset_terms):
        score = proof_text_score(query, value)
        if score > best_score:
            best_score, best_value = score, value
    return best_score, best_value
