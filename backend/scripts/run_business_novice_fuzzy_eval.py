from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.api.dependencies import get_search_ai_service
from app.core.errors import AppError
from app.db.session import SessionLocal
from app.domain.taxonomy_catalog import load_taxonomy_catalog

PROJECT_DIR = Path(__file__).resolve().parents[2]
SOURCE_DOC = (
    PROJECT_DIR
    / "docs"
    / "SELLING_POINT_FUZZY_SEARCH_EVAL_50_BUSINESS_NOVICE_GPT55_2026-07-23.md"
)
RESULT_JSON = (
    PROJECT_DIR
    / "docs"
    / "SELLING_POINT_FUZZY_SEARCH_EVAL_50_BUSINESS_NOVICE_GPT55_2026-07-23_RUN.json"
)
RESULT_MD = (
    PROJECT_DIR
    / "docs"
    / "SELLING_POINT_FUZZY_SEARCH_EVAL_50_BUSINESS_NOVICE_GPT55_2026-07-23_RUN.md"
)


EXPECTED_NAME_TO_CODE = {
    "同步校内": "school_sync",
    "动画精讲": "animation_explanation",
    "课后小测": "instant_quiz",
    "新课标新考法预测": "new_curriculum_prediction",
    "专项培优": "focused_excellence",
    "举一反三": "transfer_practice",
    "专家规划": "expert_planning",
    "学段衔接": "stage_transition",
    "万能解法": "universal_method",
    "AI定制学习方案": "ai_learning_plan",
    "AI私教答疑": "ai_tutor_qa",
    "AI拍题精学": "photo_guided_learning",
    "极速预习复习": "rapid_preview_review",
    "AI错题本": "ai_error_book",
    "真人老师督学": "human_teacher_supervision",
    "学情报告反馈": "learning_report",
}


@dataclass(frozen=True)
class Case:
    number: int
    query: str
    expected_status: str
    expected_names: tuple[str, ...]
    rationale: str


def _now() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat(timespec="seconds")


def _split_expected(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in re.split(r"\s*/\s*", value) if item.strip())


def _parse_cases(path: Path) -> list[Case]:
    cases: list[Case] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        cases.append(
            Case(
                number=int(cells[0]),
                query=cells[1],
                expected_status=cells[2],
                expected_names=_split_expected(cells[3]),
                rationale=cells[4],
            )
        )
    return cases


def _concept_name_to_code() -> dict[str, str]:
    catalog = load_taxonomy_catalog()
    mapping: dict[str, str] = {}
    for node in catalog.image_label_nodes:
        system = catalog.node_by_code.get(node.parent_code or "")
        display = f"{system.name} > {node.name}" if system else node.name
        mapping[node.code] = node.code
        mapping[node.name] = node.code
        mapping[display] = node.code
    return mapping


def _route_to_json(route) -> dict[str, Any] | None:
    if route is None:
        return None
    return route.model_dump(mode="json", by_alias=True)


def _understanding_to_json(understanding, name_to_code: dict[str, str]) -> dict[str, Any] | None:
    if understanding is None:
        return None
    concepts = [
        {
            "name": item.concept,
            "code": name_to_code.get(item.concept)
            or name_to_code.get(item.concept.split(" > ")[-1]),
            "relation": item.relation,
            "weight": item.weight,
            "reason": item.reason,
        }
        for item in understanding.matched_business_concepts
    ]
    return {
        "queryType": understanding.query_type,
        "searchIntent": understanding.search_intent,
        "strategy": understanding.search_strategy,
        "concepts": concepts,
        "proofPoints": [
            {
                "code": item.code,
                "conceptCode": item.concept_code,
                "name": item.name,
                "weight": item.weight,
                "reason": item.reason,
                "evidenceTerms": item.evidence_terms,
            }
            for item in understanding.matched_proof_points
        ],
        "evidencePoints": [
            {
                "code": item.code,
                "conceptCode": item.concept_code,
                "proofPointCode": item.proof_point_code,
                "name": item.name,
                "weight": item.weight,
                "reason": item.reason,
            }
            for item in understanding.matched_evidence_points
        ],
        "excludedConcepts": understanding.excluded_concepts,
    }


def _status_hit(expected_status: str, actual_query_type: str | None) -> bool:
    expected = expected_status.strip()
    if expected == "明确单卖点":
        return actual_query_type == "business_intent_search"
    if expected == "探索型":
        return actual_query_type in {
            "exploratory_business_intent_search",
            "ambiguous_business_intent_search",
            "multi_business_intent_search",
        }
    if expected == "待消歧":
        return actual_query_type == "ambiguous_business_intent_search"
    return False


def _render_md(report: dict[str, Any]) -> str:
    rows = []
    for item in report["results"]:
        actual = "、".join(concept["name"] for concept in item["actualConcepts"]) or "—"
        actual_codes = "、".join(
            concept["code"] or "" for concept in item["actualConcepts"] if concept["code"]
        ) or "—"
        expected = " / ".join(item["expectedNames"]) or "—"
        check = "含预期" if item["expectedCodePresent"] else "不含预期"
        if item["expectedStatus"] == "探索型":
            check = "探索待人工看"
        rows.append(
            (
                "| {number} | {query} | {expected_status} | {expected} | "
                "{query_type} | {actual} | {actual_codes} | {check} | "
                "{latency}ms | {error} |  |"
            ).format(
                number=item["number"],
                query=item["query"],
                expected_status=item["expectedStatus"],
                expected=expected,
                query_type=item["actualQueryType"] or "—",
                actual=actual,
                actual_codes=actual_codes,
                check=check,
                latency=item["latencyMs"],
                error=item["error"] or "",
            )
        )
    summary = report["summary"]
    lines = [
        "# 50 条业务小白模糊搜索测评结果（GPT-5.5）",
        "",
        f"运行时间：{report['generatedAt']}",
        "",
        "## 汇总",
        "",
        f"- Provider：{report['provider']}",
        f"- 模型：{report['modelName']}",
        f"- 完成：{summary['completed']}/{summary['total']}",
        f"- 模型调用成功：{summary['modelSuccess']}/{summary['total']}",
        f"- 明确单卖点含预期：{summary['singleExpectedPresent']}/{summary['singleCaseCount']}",
        f"- 查询状态匹配：{summary['queryTypeHit']}/{summary['total']}",
        f"- 探索型用例：{summary['exploratoryCaseCount']} 条，需人工看是否合理保留候选",
        "",
        "## 逐条对照表",
        "",
        (
            "| # | 测试话术 | 预期状态 | 预期卖点 | 实际查询状态 | "
            "GPT-5.5 实际识别卖点 | 实际 code | 自动检查 | 耗时 | "
            "错误 | 人工判断 |"
        ),
        "|---:|---|---|---|---|---|---|---|---:|---|---|",
        *rows,
        "",
        "## 使用说明",
        "",
        "- “明确单卖点含预期”只看模型实际识别卖点是否包含预期 code，不替代业务人工审批。",
        "- 探索型话术本来就不应该强行猜唯一卖点；人工重点看候选是否合理、是否过度扩散。",
        "- 本报告只评 GPT-5.5 的卖点理解，不评最终图片排序质量。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    cases = _parse_cases(SOURCE_DOC)
    if len(cases) != 50:
        raise SystemExit(f"expected 50 cases, got {len(cases)}")
    name_to_code = _concept_name_to_code()
    results = []
    with SessionLocal() as db:
        ai_service = get_search_ai_service(db)
        provider = ai_service.provider
        print(f"provider={provider.name} configured={provider.configured}")
        for case in cases:
            expected_codes = tuple(
                EXPECTED_NAME_TO_CODE[name]
                for name in case.expected_names
                if name in EXPECTED_NAME_TO_CODE
            )
            started = time.perf_counter()
            route = None
            understanding = None
            error = ""
            try:
                route = ai_service.route_search_system(case.query).value
                understanding = ai_service.understand_search_from_route(
                    case.query,
                    route,
                ).value
            except AppError as exc:
                error = f"{exc.code}: {exc.message}"
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
            latency_ms = round((time.perf_counter() - started) * 1000)
            understanding_json = _understanding_to_json(understanding, name_to_code)
            actual_concepts = understanding_json["concepts"] if understanding_json else []
            actual_codes = {item["code"] for item in actual_concepts if item.get("code")}
            expected_present = bool(set(expected_codes) & actual_codes)
            actual_query_type = understanding_json["queryType"] if understanding_json else None
            result = {
                "number": case.number,
                "query": case.query,
                "expectedStatus": case.expected_status,
                "expectedNames": case.expected_names,
                "expectedCodes": expected_codes,
                "rationale": case.rationale,
                "route": _route_to_json(route),
                "understanding": understanding_json,
                "actualQueryType": actual_query_type,
                "actualConcepts": actual_concepts,
                "expectedCodePresent": expected_present,
                "queryTypeHit": _status_hit(case.expected_status, actual_query_type),
                "latencyMs": latency_ms,
                "error": error,
            }
            results.append(result)
            actual_display = "、".join(item["name"] for item in actual_concepts) or "—"
            print(
                f"{case.number:02d}/50 {latency_ms}ms "
                f"{actual_query_type or '—'} {actual_display} {error}",
                flush=True,
            )

    single_results = [item for item in results if item["expectedStatus"] == "明确单卖点"]
    report = {
        "generatedAt": _now(),
        "sourceDoc": str(SOURCE_DOC.relative_to(PROJECT_DIR)),
        "provider": "primary",
        "modelName": "gpt-5.5",
        "summary": {
            "total": len(results),
            "completed": len(results),
            "modelSuccess": sum(1 for item in results if not item["error"]),
            "singleCaseCount": len(single_results),
            "singleExpectedPresent": sum(
                1 for item in single_results if item["expectedCodePresent"]
            ),
            "queryTypeHit": sum(1 for item in results if item["queryTypeHit"]),
            "exploratoryCaseCount": sum(
                1 for item in results if item["expectedStatus"] == "探索型"
            ),
        },
        "results": results,
    }
    RESULT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    RESULT_MD.write_text(_render_md(report), encoding="utf-8")
    print(f"wrote {RESULT_JSON}")
    print(f"wrote {RESULT_MD}")


if __name__ == "__main__":
    main()
