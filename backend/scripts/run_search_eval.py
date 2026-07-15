from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.domain.search_eval import SearchEvalCase, expected_display_name, load_search_eval_cases
from app.schemas.image import ScoredImage
from app.services.search_service import SearchService


def _result_text(result: ScoredImage) -> str:
    image = result.image
    parts = [
        image.title,
        *result.matched_content_terms,
        *result.matched_business_concepts,
        *result.expressed_concepts,
        *result.supported_concepts,
        *result.match_reasons,
    ]
    return " ".join(part for part in parts if part)


def _matches_expected_result(
    result: ScoredImage,
    *,
    expected_category: str,
) -> bool:
    if expected_category in result.matched_business_concepts:
        return True
    return any(expected_category in reason for reason in result.match_reasons)


def _evaluate_case(
    service: SearchService,
    case: SearchEvalCase,
    *,
    limit: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    response = service.search(case.query, limit)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    expected_category = expected_display_name(case)
    top_ids = [result.image.id for result in response.results]
    top_titles = [result.image.title for result in response.results]
    top_asset_ids = [result.image.asset_group_id or result.image.id for result in response.results]
    top_label_match_rank: int | None = None
    top_category_match_rank: int | None = None

    for index, result in enumerate(response.results, start=1):
        if top_label_match_rank is None and _matches_expected_result(
            result,
            expected_category=expected_category,
        ):
            top_label_match_rank = index
        if (
            top_category_match_rank is None
            and (
                expected_category in result.matched_business_concepts
                or any(expected_category in reason for reason in result.match_reasons)
            )
        ):
            top_category_match_rank = index

    disallowed_terms: list[str] = []
    for result in response.results[:5]:
        image_text = _result_text(result)
        for term in case.disallowed_images:
            if term and term in image_text and term not in disallowed_terms:
                disallowed_terms.append(term)

    return {
        "id": case.id,
        "query": case.query,
        "expected": {
            "systemCode": case.expected_system_code,
            "labelCode": case.expected_label_code,
            "displayName": expected_category,
        },
        "topIds": top_ids,
        "topAssetIds": top_asset_ids,
        "topTitles": top_titles,
        "topLabelMatchRank": top_label_match_rank,
        "topCategoryMatchRank": top_category_match_rank,
        "top3Hit": (
            any(asset_id in set(case.strong_relevant_asset_ids) for asset_id in top_asset_ids[:3])
            if case.strong_relevant_asset_ids
            else bool(
                top_label_match_rank and top_label_match_rank <= 3
                or top_category_match_rank and top_category_match_rank <= 3
            )
        ),
        "top5ForbiddenAssetIds": [
            asset_id for asset_id in top_asset_ids[:5] if asset_id in set(case.forbidden_asset_ids)
        ],
        "latencyMs": latency_ms,
        "top5DisallowedTerms": disallowed_terms,
        "fallback": response.fallback,
        "fallbackReason": response.fallback_reason,
        "searchDiagnostics": (
            response.search_diagnostics.model_dump(mode="json", by_alias=True)
            if response.search_diagnostics
            else None
        ),
    }


def run_eval(batch: int, limit: int) -> dict[str, Any]:
    catalog = load_search_eval_cases()
    cases = catalog.cumulative_cases(batch)
    with SessionLocal() as db:
        service = SearchService(db)
        results = [
            _evaluate_case(service, case, limit=limit)
            for case in cases
        ]

    top3_hits = sum(1 for result in results if result["top3Hit"])
    disallowed_cases = [
        result["id"]
        for result in results
        if result["top5DisallowedTerms"] or result["top5ForbiddenAssetIds"]
    ]
    latencies = sorted(result["latencyMs"] for result in results)
    bound_cases = [case for case in cases if case.strong_relevant_asset_ids]
    timed_out_case_ids = [
        result["id"]
        for result in results
        if result["searchDiagnostics"]
        and result["searchDiagnostics"]["timedOut"]
    ]
    fallback_case_ids = [result["id"] for result in results if result["fallback"]]
    return {
        "version": catalog.version,
        "batch": batch,
        "caseCount": len(cases),
        "datasetStatus": catalog.dataset_status,
        "realBoundCaseCount": len(bound_cases),
        "missingBindingCaseIds": [case.id for case in cases if not case.strong_relevant_asset_ids],
        "top3HitRate": top3_hits / len(cases) if cases else 0,
        "p95LatencyMs": latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0,
        "disallowedCaseIds": disallowed_cases,
        "fallbackCaseIds": fallback_case_ids,
        "timedOutCaseIds": timed_out_case_ids,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run search evaluation cases.")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], default=3)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.validate_only:
        catalog = load_search_eval_cases()
        report = {
            "version": catalog.version,
            "batch": args.batch,
            "caseCount": len(catalog.cumulative_cases(args.batch)),
            "status": "validated",
        }
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return

    try:
        report = run_eval(args.batch, max(args.limit, 1))
    except OperationalError as exc:
        raise SystemExit(
            "搜索评测需要已迁移到当前 schema 的数据库；"
            "请先运行 Alembic migration 或切换到服务器/测试库后重试。"
        ) from exc
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
