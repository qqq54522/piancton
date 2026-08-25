from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.api.dependencies import get_search_service
from app.db.session import SessionLocal
from app.domain.taxonomy_catalog import load_taxonomy_catalog
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept
from app.services.search_service import SearchService

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = PROJECT_DIR / "taxonomy" / "business_side_search_eval_2026-07-30.json"
DEFAULT_OUTPUT_JSON = PROJECT_DIR / "docs" / "BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_LOCAL.json"
DEFAULT_OUTPUT_MD = PROJECT_DIR / "docs" / "BUSINESS_SIDE_SEARCH_EVAL_50_2026-07-30_LOCAL.md"


@dataclass(frozen=True)
class GoldAssets:
    names: dict[str, str]
    expresses: dict[str, frozenset[str]]
    supports: dict[str, frozenset[str]]
    excludes: dict[str, frozenset[str]]


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_ ")
    return "".join(char.lower() for char in value if char not in ignored)


def _load_gold_assets(db) -> GoldAssets:
    names = {
        code: name
        for code, name in db.execute(
            select(BusinessConcept.code, BusinessConcept.name).where(
                BusinessConcept.status == "active"
            )
        )
    }
    grouped: dict[str, dict[str, set[str]]] = {
        "expresses": defaultdict(set),
        "supports": defaultdict(set),
        "excludes": defaultdict(set),
    }
    rows = db.execute(
        select(
            BusinessConcept.code,
            AssetConceptLink.relation_role,
            AssetGroup.id,
        )
        .join(AssetConceptLink, AssetConceptLink.concept_id == BusinessConcept.id)
        .join(AssetGroup, AssetGroup.id == AssetConceptLink.asset_group_id)
        .where(
            BusinessConcept.status == "active",
            AssetGroup.approval_status == "approved",
            AssetGroup.publish_status == "published",
            AssetConceptLink.origin == "manual",
            AssetConceptLink.review_status == "accepted",
            AssetConceptLink.relation_role.in_(("expresses", "supports", "excludes")),
        )
    )
    for concept_code, role, asset_group_id in rows:
        grouped[role][concept_code].add(asset_group_id)
    return GoldAssets(
        names=names,
        expresses={code: frozenset(ids) for code, ids in grouped["expresses"].items()},
        supports={code: frozenset(ids) for code, ids in grouped["supports"].items()},
        excludes={code: frozenset(ids) for code, ids in grouped["excludes"].items()},
    )


def _name_to_code() -> dict[str, str]:
    mapping: dict[str, str] = {}
    taxonomy = load_taxonomy_catalog()
    for node in taxonomy.image_label_nodes:
        system = taxonomy.node_by_code.get(node.parent_code or "")
        display = f"{system.name} > {node.name}" if system else node.name
        for value in (node.code, node.name, display):
            mapping[_normalize(value)] = node.code
    return mapping


def _concept_codes_from_understanding(understanding, mapping: dict[str, str]) -> list[str]:
    if understanding is None:
        return []
    codes: list[str] = []
    for match in understanding.matched_business_concepts:
        code = mapping.get(_normalize(match.concept))
        if code and code not in codes:
            codes.append(code)
    return codes


def _concept_codes_from_results(results, mapping: dict[str, str]) -> list[str]:
    codes: list[str] = []
    for result in results:
        for match in result.matched_query_concepts:
            for value in (match.concept_code, match.concept_name):
                code = mapping.get(_normalize(value))
                if code and code not in codes:
                    codes.append(code)
        for value in (*result.expressed_concepts, *result.supported_concepts):
            code = mapping.get(_normalize(value))
            if code and code not in codes:
                codes.append(code)
    return codes


def _diagnostics(response) -> dict[str, Any] | None:
    if response.search_diagnostics is None:
        return None
    return response.search_diagnostics.model_dump(mode="json", by_alias=True)


def _load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    seen: set[str] = set()
    taxonomy_codes = {node.code for node in load_taxonomy_catalog().image_label_nodes}
    for suite in payload.get("suites", []):
        for case in suite.get("cases", []):
            case_id = str(case.get("id") or "")
            expected_code = str(case.get("expectedCode") or "")
            if case_id in seen:
                raise SystemExit(f"重复用例 id：{case_id}")
            if expected_code not in taxonomy_codes:
                raise SystemExit(f"无效预期卖点 code：{case_id} -> {expected_code}")
            seen.add(case_id)
    return payload


def _build_service(db, *, production_deps: bool) -> SearchService:
    if production_deps:
        return get_search_service(db)
    return SearchService(db)


def _evaluate_case(
    service: SearchService,
    case: dict[str, Any],
    *,
    limit: int,
    mapping: dict[str, str],
    gold: GoldAssets,
) -> dict[str, Any]:
    expected_code = str(case["expectedCode"])
    started = time.perf_counter()
    error = ""
    try:
        response = service.search(str(case["query"]), limit)
    except Exception as exc:  # noqa: BLE001 - preserve failure in report
        return {
            **case,
            "latencyMs": round((time.perf_counter() - started) * 1000, 2),
            "error": f"{type(exc).__name__}: {exc}",
            "actualQueryType": None,
            "actualIntentCodes": [],
            "actualResultCodes": [],
            "intentHit": False,
            "queryTypeHit": False,
            "top5ExpectedAssetHit": False,
            "top5OutOfScopeAssetIds": [],
            "topTitles": [],
            "resultCount": 0,
            "diagnostics": None,
        }
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    understanding = response.search_understanding
    top_asset_ids = [
        result.image.asset_group_id or result.image.id for result in response.results[:5]
    ]
    allowed_assets = set(gold.expresses.get(expected_code, ())) | set(
        gold.supports.get(expected_code, ())
    )
    forbidden_assets = set(gold.excludes.get(expected_code, ()))
    out_of_scope = [
        asset_id
        for asset_id in top_asset_ids
        if allowed_assets and asset_id not in allowed_assets
    ]
    out_of_scope.extend(
        asset_id
        for asset_id in top_asset_ids
        if asset_id in forbidden_assets and asset_id not in out_of_scope
    )
    actual_intent_codes = _concept_codes_from_understanding(understanding, mapping)
    actual_result_codes = _concept_codes_from_results(response.results[:5], mapping)
    expected_query_type = str(case.get("expectedQueryType") or "")
    actual_query_type = understanding.query_type if understanding else None
    return {
        **case,
        "latencyMs": latency_ms,
        "error": error,
        "actualQueryType": actual_query_type,
        "actualIntentCodes": actual_intent_codes,
        "actualResultCodes": actual_result_codes,
        "intentHit": expected_code in actual_intent_codes,
        "queryTypeHit": (
            actual_query_type == expected_query_type if expected_query_type else None
        ),
        "top5ExpectedAssetHit": bool(allowed_assets & set(top_asset_ids)),
        "top5OutOfScopeAssetIds": out_of_scope,
        "topTitles": [result.image.title for result in response.results[:5]],
        "resultCount": len(response.results),
        "fallback": response.fallback,
        "fallbackReason": response.fallback_reason,
        "diagnostics": _diagnostics(response),
    }


def _rate(items: list[dict[str, Any]], key: str) -> str:
    return f"{sum(1 for item in items if item.get(key) is True)}/{len(items)}"


def run(dataset_path: Path, *, limit: int, production_deps: bool) -> dict[str, Any]:
    dataset = _load_dataset(dataset_path)
    mapping = _name_to_code()
    suites = []
    with SessionLocal() as db:
        service = _build_service(db, production_deps=production_deps)
        gold = _load_gold_assets(db)
        for suite in dataset.get("suites", []):
            results = [
                _evaluate_case(
                    service,
                    case,
                    limit=limit,
                    mapping=mapping,
                    gold=gold,
                )
                for case in suite.get("cases", [])
            ]
            latencies = sorted(result["latencyMs"] for result in results)
            p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0
            suites.append(
                {
                    "id": suite["id"],
                    "title": suite["title"],
                    "sourceDoc": suite.get("sourceDoc"),
                    "summary": {
                        "caseCount": len(results),
                        "intentHit": _rate(results, "intentHit"),
                        "queryTypeHit": _rate(results, "queryTypeHit"),
                        "top5ExpectedAssetHit": _rate(results, "top5ExpectedAssetHit"),
                        "zeroResultIds": [
                            result["id"] for result in results if not result["resultCount"]
                        ],
                        "outOfScopeIds": [
                            result["id"]
                            for result in results
                            if result["top5OutOfScopeAssetIds"]
                        ],
                        "errorIds": [result["id"] for result in results if result["error"]],
                        "p95LatencyMs": p95,
                    },
                    "results": results,
                }
            )
    return {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "dataset": str(dataset_path.relative_to(PROJECT_DIR)),
        "mode": "production_deps" if production_deps else "local_no_external",
        "note": (
            "production_deps may call configured external model providers. "
            "local_no_external uses deterministic local search service only."
        ),
        "suites": suites,
    }


def _join(values: list[str]) -> str:
    return "、".join(values) if values else "—"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 业务端搜索话术专项评测结果",
        "",
        f"运行时间：{report['generatedAt']}",
        f"数据集：`{report['dataset']}`",
        f"模式：`{report['mode']}`",
        "",
        "## 口径",
        "",
        "- 本报告只评核心卖点识别和当前素材关系覆盖，不评证明点、证据表达点或图片美术质量。",
        "- `intentHit` 表示搜索理解中包含预设卖点。",
        (
            "- `top5ExpectedAssetHit` 表示 Top 5 里至少有一张人工 accepted "
            "expresses/supports 关系属于预设卖点的素材。"
        ),
        (
            "- `outOfScopeIds` 表示已有预设卖点素材关系时，Top 5 出现了不属于"
            "该卖点人工关系集合的素材，需要重点人工看。"
        ),
        "",
        "## 汇总",
        "",
        (
            "| 测试集 | 条数 | 意图命中 | 查询状态命中 | Top5素材命中 | 空结果 | "
            "越界 | 错误 | P95耗时 |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for suite in report["suites"]:
        summary = suite["summary"]
        lines.append(
            f"| {suite['title']} | {summary['caseCount']} | {summary['intentHit']} | "
            f"{summary['queryTypeHit']} | {summary['top5ExpectedAssetHit']} | "
            f"{len(summary['zeroResultIds'])} | {len(summary['outOfScopeIds'])} | "
            f"{len(summary['errorIds'])} | {summary['p95LatencyMs']:.0f}ms |"
        )
    for suite in report["suites"]:
        lines.extend(
            [
                "",
                f"## {suite['title']}",
                "",
                (
                    "| ID | 测试话术 | 预期卖点 | 实际意图 code | 实际结果 code | "
                    "意图 | Top5素材 | 越界 | 耗时 | Top 结果 |"
                ),
                "|---|---|---|---|---|---|---|---|---:|---|",
            ]
        )
        for result in suite["results"]:
            query = str(result["query"]).replace("|", "\\|")
            top_titles = _join([str(title).replace("|", "\\|") for title in result["topTitles"]])
            intent = "是" if result["intentHit"] else "否"
            top5 = "是" if result["top5ExpectedAssetHit"] else "否"
            out = "是" if result["top5OutOfScopeAssetIds"] else "否"
            lines.append(
                f"| {result['id']} | {query} | {result['expectedName']} | "
                f"{_join(result['actualIntentCodes'])} | {_join(result['actualResultCodes'])} | "
                f"{intent} | {top5} | {out} | {result['latencyMs']:.0f}ms | {top_titles} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run business-side search eval suites.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument(
        "--production-deps",
        action="store_true",
        help="使用线上同款依赖，可能调用已配置的外部模型 Provider。",
    )
    args = parser.parse_args()
    report = run(
        args.dataset,
        limit=max(1, args.limit),
        production_deps=args.production_deps,
    )
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "suites"},
            ensure_ascii=False,
            indent=2,
        )
    )
    for suite in report["suites"]:
        print(json.dumps({"suite": suite["id"], **suite["summary"]}, ensure_ascii=False))
    print(f"wrote {args.output_json}")
    print(f"wrote {args.output_md}")


if __name__ == "__main__":
    main()
