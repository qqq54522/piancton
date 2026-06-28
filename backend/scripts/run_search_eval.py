from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.domain.search_eval import SearchEvalCase, expected_display_name, load_search_eval_cases
from app.schemas.image import ImageRead, ScoredImage
from app.services.search_service import SearchService


def _image_label_codes(image: ImageRead) -> set[str]:
    return {tag.code for tag in image.tags if tag.code}


def _result_text(result: ScoredImage) -> str:
    image = result.image
    parts = [
        image.title,
        *(tag.name for tag in image.tags),
        *result.matched_level1_tags,
        *result.matched_level2_categories,
        *result.match_reasons,
    ]
    return " ".join(part for part in parts if part)


def _matches_expected_result(
    result: ScoredImage,
    *,
    expected_label_code: str,
    expected_category: str,
) -> bool:
    if expected_label_code in _image_label_codes(result.image):
        return True
    if expected_category in result.matched_level2_categories:
        return True
    return any(expected_category in reason for reason in result.match_reasons)


def _evaluate_case(
    service: SearchService,
    case: SearchEvalCase,
    *,
    limit: int,
    search_mode: str,
) -> dict[str, Any]:
    response = service.search(case.query, limit, search_mode)  # type: ignore[arg-type]
    expected_category = expected_display_name(case)
    top_ids = [result.image.id for result in response.results]
    top_titles = [result.image.title for result in response.results]
    top_label_match_rank: int | None = None
    top_category_match_rank: int | None = None

    for index, result in enumerate(response.results, start=1):
        if top_label_match_rank is None and _matches_expected_result(
            result,
            expected_label_code=case.expected_label_code,
            expected_category=expected_category,
        ):
            top_label_match_rank = index
        if (
            top_category_match_rank is None
            and (
                expected_category in result.matched_level2_categories
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
        "topTitles": top_titles,
        "topLabelMatchRank": top_label_match_rank,
        "topCategoryMatchRank": top_category_match_rank,
        "top3Hit": bool(
            top_label_match_rank and top_label_match_rank <= 3
            or top_category_match_rank and top_category_match_rank <= 3
        ),
        "top5DisallowedTerms": disallowed_terms,
        "fallback": response.fallback,
        "fallbackReason": response.fallback_reason,
    }


def run_eval(batch: int, limit: int, search_mode: str) -> dict[str, Any]:
    catalog = load_search_eval_cases()
    cases = catalog.cumulative_cases(batch)
    with SessionLocal() as db:
        service = SearchService(db)
        results = [
            _evaluate_case(service, case, limit=limit, search_mode=search_mode)
            for case in cases
        ]

    top3_hits = sum(1 for result in results if result["top3Hit"])
    disallowed_cases = [
        result["id"] for result in results if result["top5DisallowedTerms"]
    ]
    return {
        "version": catalog.version,
        "batch": batch,
        "caseCount": len(cases),
        "top3HitRate": top3_hits / len(cases) if cases else 0,
        "disallowedCaseIds": disallowed_cases,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run search evaluation cases.")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], default=3)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--search-mode",
        choices=["configured", "precise", "smart"],
        default="smart",
    )
    args = parser.parse_args()
    if args.validate_only:
        catalog = load_search_eval_cases()
        report = {
            "version": catalog.version,
            "batch": args.batch,
            "caseCount": len(catalog.cumulative_cases(args.batch)),
            "status": "validated",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    try:
        report = run_eval(args.batch, max(args.limit, 1), args.search_mode)
    except OperationalError as exc:
        raise SystemExit(
            "搜索评测需要已迁移到当前 schema 的数据库；"
            "请先运行 Alembic migration 或切换到服务器/测试库后重试。"
        ) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
