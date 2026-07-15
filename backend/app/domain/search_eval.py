from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import PROJECT_DIR
from app.domain.taxonomy_catalog import load_taxonomy_catalog

SEARCH_EVAL_CASES_PATH = PROJECT_DIR / "taxonomy" / "search_eval_cases.json"
EXPECTED_CUMULATIVE_BATCH_COUNTS = {1: 15, 2: 30, 3: 50}


@dataclass(frozen=True)
class SearchEvalScoring:
    must: tuple[str, ...]
    should: tuple[str, ...]
    pass_condition: str


@dataclass(frozen=True)
class SearchEvalResultRecord:
    status: str
    screenshot: str
    notes: str
    top_asset_ids: tuple[str, ...] = ()
    latency_ms: float | None = None
    error: str = ""
    recorded_at: str = ""


@dataclass(frozen=True)
class SearchEvalCase:
    id: str
    batch: int
    query: str
    true_intent: str
    expected_system_code: str
    expected_label_code: str
    strong_relevant_images: tuple[str, ...]
    disallowed_images: tuple[str, ...]
    strong_relevant_asset_ids: tuple[str, ...]
    acceptable_asset_ids: tuple[str, ...]
    forbidden_asset_ids: tuple[str, ...]
    expected_concept_codes: tuple[str, ...]
    ambiguity: tuple[str, ...]
    allow_few_results: bool
    scoring: SearchEvalScoring
    result_record: SearchEvalResultRecord


@dataclass(frozen=True)
class SearchEvalCatalog:
    version: str
    dataset_status: str
    cases: tuple[SearchEvalCase, ...]

    def cases_for_batch(self, batch: int) -> tuple[SearchEvalCase, ...]:
        return tuple(case for case in self.cases if case.batch == batch)

    def cumulative_cases(self, batch: int) -> tuple[SearchEvalCase, ...]:
        return tuple(case for case in self.cases if case.batch <= batch)


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


def _scoring(payload: dict[str, Any]) -> SearchEvalScoring:
    return SearchEvalScoring(
        must=_strings(payload.get("must")),
        should=_strings(payload.get("should")),
        pass_condition=str(payload.get("pass_condition") or "").strip(),
    )


def _result_record(payload: dict[str, Any]) -> SearchEvalResultRecord:
    return SearchEvalResultRecord(
        status=str(payload.get("status") or "").strip(),
        screenshot=str(payload.get("screenshot") or "").strip(),
        notes=str(payload.get("notes") or "").strip(),
        top_asset_ids=_strings(payload.get("top_asset_ids")),
        latency_ms=(
            float(payload["latency_ms"])
            if payload.get("latency_ms") is not None
            else None
        ),
        error=str(payload.get("error") or "").strip(),
        recorded_at=str(payload.get("recorded_at") or "").strip(),
    )


def _case(payload: dict[str, Any]) -> SearchEvalCase:
    return SearchEvalCase(
        id=str(payload["id"]).strip(),
        batch=int(payload["batch"]),
        query=str(payload["query"]).strip(),
        true_intent=str(payload["true_intent"]).strip(),
        expected_system_code=str(payload["expected_system_code"]).strip(),
        expected_label_code=str(payload["expected_label_code"]).strip(),
        strong_relevant_images=_strings(payload.get("strong_relevant_images")),
        disallowed_images=_strings(payload.get("disallowed_images")),
        strong_relevant_asset_ids=_strings(payload.get("strong_relevant_asset_ids")),
        acceptable_asset_ids=_strings(payload.get("acceptable_asset_ids")),
        forbidden_asset_ids=_strings(payload.get("forbidden_asset_ids")),
        expected_concept_codes=_strings(payload.get("expected_concept_codes")),
        ambiguity=_strings(payload.get("ambiguity")),
        allow_few_results=bool(payload.get("allow_few_results", False)),
        scoring=_scoring(payload.get("scoring") or {}),
        result_record=_result_record(payload.get("result_record") or {}),
    )


def _validate(catalog: SearchEvalCatalog) -> None:
    if not catalog.version:
        raise ValueError("搜索评测集缺少版本")
    if catalog.dataset_status not in {"template", "partial", "ready"}:
        raise ValueError("搜索评测集 dataset_status 无效")
    if len(catalog.cases) != EXPECTED_CUMULATIVE_BATCH_COUNTS[3]:
        raise ValueError("搜索评测集必须包含 50 条评测 query")

    ids = [case.id for case in catalog.cases]
    if len(ids) != len(set(ids)):
        raise ValueError("搜索评测集存在重复 id")

    taxonomy = load_taxonomy_catalog()
    node_by_code = taxonomy.node_by_code
    for batch, expected_count in EXPECTED_CUMULATIVE_BATCH_COUNTS.items():
        actual_count = len(catalog.cumulative_cases(batch))
        if actual_count != expected_count:
            raise ValueError(
                f"搜索评测集第 {batch} 批累计数量应为 {expected_count}，实际为 {actual_count}"
            )

    for case in catalog.cases:
        if not case.query or not case.true_intent:
            raise ValueError(f"搜索评测案例缺少 query 或真实意图：{case.id}")
        system = node_by_code.get(case.expected_system_code)
        if not system or system.node_type != "system":
            raise ValueError(f"搜索评测案例目标体系无效：{case.id}")
        label = node_by_code.get(case.expected_label_code)
        if not label or label.node_type != "image_label":
            raise ValueError(f"搜索评测案例目标标签无效：{case.id}")
        if label.parent_code != system.code:
            raise ValueError(f"搜索评测案例目标体系与标签不匹配：{case.id}")
        if not case.strong_relevant_images:
            raise ValueError(f"搜索评测案例缺少强相关图片描述：{case.id}")
        if not case.disallowed_images:
            raise ValueError(f"搜索评测案例缺少不应出现图片描述：{case.id}")
        if not case.scoring.must or not case.scoring.pass_condition:
            raise ValueError(f"搜索评测案例缺少评分标准：{case.id}")
        if case.result_record.status not in {"not_run", "recorded"}:
            raise ValueError(f"搜索评测案例结果记录状态无效：{case.id}")
        if catalog.dataset_status == "ready" and not case.strong_relevant_asset_ids:
            raise ValueError(f"ready 评测案例必须绑定真实素材组 ID：{case.id}")


@lru_cache
def load_search_eval_cases(path: Path = SEARCH_EVAL_CASES_PATH) -> SearchEvalCatalog:
    raw = json.loads(path.read_text(encoding="utf-8"))
    catalog = SearchEvalCatalog(
        version=str(raw.get("version") or "").strip(),
        dataset_status=str(raw.get("dataset_status") or "template").strip(),
        cases=tuple(_case(item) for item in raw.get("cases", [])),
    )
    _validate(catalog)
    return catalog


def expected_display_name(case: SearchEvalCase) -> str:
    taxonomy = load_taxonomy_catalog()
    system = taxonomy.node_by_code[case.expected_system_code]
    label = taxonomy.node_by_code[case.expected_label_code]
    return f"{system.name} > {label.name}"
