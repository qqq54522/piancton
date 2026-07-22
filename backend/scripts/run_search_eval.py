from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.domain.search_eval import (
    SearchEvalCase,
    display_name_for_label,
    expected_display_name,
    load_search_eval_cases,
)
from app.models.asset import AssetConceptLink, AssetGroup
from app.models.business_concept import BusinessConcept
from app.schemas.image import ScoredImage
from app.services.search_service import SearchService

SCOPED_QUERY_TYPES = {
    "business_intent_search",
    "multi_business_intent_search",
    "exploratory_business_intent_search",
}


@dataclass(frozen=True)
class ReviewedGoldAssets:
    concept_names: dict[str, tuple[str, ...]]
    expresses: dict[str, frozenset[str]]
    supports: dict[str, frozenset[str]]
    excludes: dict[str, frozenset[str]]


def _load_reviewed_gold_assets(db) -> ReviewedGoldAssets:
    concept_names = {
        code: (name,)
        for code, name in db.execute(
            select(BusinessConcept.code, BusinessConcept.name).where(
                BusinessConcept.status == "active"
            )
        )
    }
    assets_by_role: dict[str, dict[str, set[str]]] = {
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
    for concept_code, relation_role, asset_group_id in rows:
        assets_by_role[relation_role][concept_code].add(asset_group_id)

    return ReviewedGoldAssets(
        concept_names=concept_names,
        expresses={
            code: frozenset(asset_ids) for code, asset_ids in assets_by_role["expresses"].items()
        },
        supports={
            code: frozenset(asset_ids) for code, asset_ids in assets_by_role["supports"].items()
        },
        excludes={
            code: frozenset(asset_ids) for code, asset_ids in assets_by_role["excludes"].items()
        },
    )


def _case_expected_concept_codes(case: SearchEvalCase) -> tuple[str, ...]:
    if case.expected_concept_codes:
        return case.expected_concept_codes
    if case.expected_label_code:
        return (case.expected_label_code,)
    return ()


def _understanding_has_concept(
    understanding,
    *,
    concept_code: str,
    gold_assets: ReviewedGoldAssets,
) -> bool:
    if understanding is None:
        return False
    expected_names = {
        concept_code,
        display_name_for_label(concept_code),
        display_name_for_label(concept_code).rsplit(">", 1)[-1].strip(),
        *gold_assets.concept_names.get(concept_code, ()),
    }
    return any(
        match.concept.strip() in expected_names for match in understanding.matched_business_concepts
    )


def _rate(values: list[bool | None]) -> float | None:
    measured = [value for value in values if value is not None]
    if not measured:
        return None
    return sum(value is True for value in measured) / len(measured)


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


def _expected_match_terms(case: SearchEvalCase) -> tuple[str, ...]:
    """期望卖点的所有等价写法：全名（体系 > 卖点）、卖点短名、卖点/概念 code。

    本地词表通道与模型通道写入结果字段的概念命名格式不同，
    判分需要同时兼容，否则模型通道的正确结果会被误判为未命中。
    """
    terms: list[str] = []
    if case.expected_label_code:
        display = expected_display_name(case)
        terms.append(display)
        terms.append(display.rsplit(">", 1)[-1].strip())
        terms.append(case.expected_label_code)
    terms.extend(case.expected_concept_codes)
    return tuple(term for term in terms if term)


def _matches_expected_result(
    result: ScoredImage,
    *,
    expected_terms: tuple[str, ...],
) -> bool:
    if not expected_terms:
        return False
    haystack = [
        *result.matched_business_concepts,
        *result.expressed_concepts,
        *result.supported_concepts,
        *(match.concept_name for match in result.matched_query_concepts),
        *(match.concept_code for match in result.matched_query_concepts),
        *result.match_reasons,
    ]
    return any(term in text for term in expected_terms for text in haystack if text)


def _evaluate_case(
    service: SearchService,
    case: SearchEvalCase,
    *,
    limit: int,
    gold_assets: ReviewedGoldAssets,
) -> dict[str, Any]:
    started = time.perf_counter()
    response = service.search(case.query, limit)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    expected_category = expected_display_name(case) if case.expected_label_code else ""
    expected_terms = _expected_match_terms(case)
    top_ids = [result.image.id for result in response.results]
    top_titles = [result.image.title for result in response.results]
    top_asset_ids = [result.image.asset_group_id or result.image.id for result in response.results]
    expected_concept_codes = _case_expected_concept_codes(case)
    strong_gold_asset_ids = set(case.strong_relevant_asset_ids)
    acceptable_gold_asset_ids = set(case.acceptable_asset_ids)
    forbidden_gold_asset_ids = set(case.forbidden_asset_ids)
    for concept_code in expected_concept_codes:
        strong_gold_asset_ids.update(gold_assets.expresses.get(concept_code, ()))
        acceptable_gold_asset_ids.update(gold_assets.supports.get(concept_code, ()))
        forbidden_gold_asset_ids.update(gold_assets.excludes.get(concept_code, ()))
    allowed_gold_asset_ids = strong_gold_asset_ids | acceptable_gold_asset_ids
    top_label_match_rank: int | None = None
    top_category_match_rank: int | None = None

    for index, result in enumerate(response.results, start=1):
        if not expected_terms:
            break
        if top_label_match_rank is None and _matches_expected_result(
            result,
            expected_terms=expected_terms,
        ):
            top_label_match_rank = index
        if (
            top_category_match_rank is None
            and expected_category
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

    understanding = response.search_understanding
    intent_concept_hits = {
        concept_code: _understanding_has_concept(
            understanding,
            concept_code=concept_code,
            gold_assets=gold_assets,
        )
        for concept_code in expected_concept_codes
    }
    top5_concept_coverage = {
        concept_code: bool(
            set(top_asset_ids[:5])
            & (
                set(gold_assets.expresses.get(concept_code, ()))
                | set(gold_assets.supports.get(concept_code, ()))
            )
        )
        for concept_code in expected_concept_codes
    }
    top3_strong_concept_coverage = {
        concept_code: bool(
            set(top_asset_ids[:3]) & set(gold_assets.expresses.get(concept_code, ()))
        )
        for concept_code in expected_concept_codes
    }
    expected_query_type = case.expected_query_type or (
        "business_intent_search" if expected_concept_codes else ""
    )
    enforce_closed_scope = expected_query_type in SCOPED_QUERY_TYPES
    top5_out_of_scope_asset_ids = (
        [
            asset_id
            for asset_id in top_asset_ids[:5]
            if allowed_gold_asset_ids and asset_id not in allowed_gold_asset_ids
        ]
        if enforce_closed_scope
        else []
    )
    top3_strong_hit = (
        bool(set(top_asset_ids[:3]) & strong_gold_asset_ids) if strong_gold_asset_ids else None
    )
    all_expected_concepts_understood = (
        all(intent_concept_hits.values()) if intent_concept_hits else None
    )
    all_expected_concepts_covered = (
        all(top5_concept_coverage.values()) if top5_concept_coverage else None
    )
    if not case.expected_query_type:
        query_type_hit = None
    elif case.expected_query_type == "visual_scene_search" and understanding is None:
        # 纯画面查询本地不伪造业务理解，交给画面召回即为正确路由。
        query_type_hit = True
    else:
        query_type_hit = (
            understanding is not None and understanding.query_type == case.expected_query_type
        )
    return {
        "id": case.id,
        "query": case.query,
        "expected": {
            "systemCode": case.expected_system_code,
            "labelCode": case.expected_label_code,
            "displayName": expected_category,
            "queryType": case.expected_query_type,
            "conceptCodes": list(expected_concept_codes),
            "excludedConceptCodes": list(case.expected_excluded_concept_codes),
        },
        "queryType": understanding.query_type if understanding else None,
        "queryTypeHit": query_type_hit,
        "intentConceptHits": intent_concept_hits,
        "allExpectedConceptsUnderstood": all_expected_concepts_understood,
        "excludedConcepts": (list(understanding.excluded_concepts) if understanding else []),
        "topIds": top_ids,
        "topAssetIds": top_asset_ids,
        "topTitles": top_titles,
        "strongGoldAssetIds": sorted(strong_gold_asset_ids),
        "acceptableGoldAssetIds": sorted(acceptable_gold_asset_ids),
        "forbiddenGoldAssetIds": sorted(forbidden_gold_asset_ids),
        "top3StrongConceptCoverage": top3_strong_concept_coverage,
        "top5ConceptCoverage": top5_concept_coverage,
        "allExpectedConceptsCoveredTop5": all_expected_concepts_covered,
        "topLabelMatchRank": top_label_match_rank,
        "topCategoryMatchRank": top_category_match_rank,
        "top3Hit": top3_strong_hit,
        "top3StrongHit": top3_strong_hit,
        "top5ForbiddenAssetIds": [
            asset_id for asset_id in top_asset_ids[:5] if asset_id in forbidden_gold_asset_ids
        ],
        "top5OutOfScopeAssetIds": top5_out_of_scope_asset_ids,
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


def _build_service(db, *, with_ai: bool) -> SearchService:
    if not with_ai:
        return SearchService(db)
    # 复用线上依赖装配，保证评测链路与生产一致（模型路由 + 向量召回 + 重排）。
    from app.api.dependencies import get_search_service

    return get_search_service(db)


def run_eval(batch: int, limit: int, *, with_ai: bool = False) -> dict[str, Any]:
    catalog = load_search_eval_cases()
    cases = catalog.cumulative_cases(batch)
    with SessionLocal() as db:
        service = _build_service(db, with_ai=with_ai)
        gold_assets = _load_reviewed_gold_assets(db)
        results = [
            _evaluate_case(service, case, limit=limit, gold_assets=gold_assets) for case in cases
        ]

    business_results = [result for result in results if result["expected"]["conceptCodes"]]
    bound_results = [result for result in business_results if result["strongGoldAssetIds"]]
    disallowed_cases = [
        result["id"]
        for result in results
        if result["top5DisallowedTerms"] or result["top5ForbiddenAssetIds"]
    ]
    latencies = sorted(result["latencyMs"] for result in results)
    timed_out_case_ids = [
        result["id"]
        for result in results
        if result["searchDiagnostics"] and result["searchDiagnostics"]["timedOut"]
    ]
    fallback_case_ids = [result["id"] for result in results if result["fallback"]]
    out_of_scope_case_ids = [result["id"] for result in results if result["top5OutOfScopeAssetIds"]]
    zero_result_case_ids = [result["id"] for result in results if not result["topAssetIds"]]
    forbidden_relation_case_ids = [
        result["id"] for result in results if result["top5ForbiddenAssetIds"]
    ]
    concept_codes = sorted(
        {
            concept_code
            for result in business_results
            for concept_code in result["expected"]["conceptCodes"]
        }
    )
    concept_metrics = {}
    for concept_code in concept_codes:
        concept_results = [
            result
            for result in business_results
            if concept_code in result["expected"]["conceptCodes"]
        ]
        concept_metrics[concept_code] = {
            "name": gold_assets.concept_names.get(concept_code, (concept_code,))[0],
            "caseCount": len(concept_results),
            "intentHitRate": _rate(
                [result["intentConceptHits"][concept_code] for result in concept_results]
            ),
            "top3StrongHitRate": _rate(
                [result["top3StrongConceptCoverage"][concept_code] for result in concept_results]
            ),
            "top5AcceptedHitRate": _rate(
                [result["top5ConceptCoverage"][concept_code] for result in concept_results]
            ),
        }
    return {
        "version": catalog.version,
        "batch": batch,
        "withAi": with_ai,
        "caseCount": len(cases),
        "datasetStatus": catalog.dataset_status,
        "goldSource": "published manual accepted expresses/supports relations",
        "businessCaseCount": len(business_results),
        "realBoundCaseCount": len(bound_results),
        "businessDatasetReady": len(bound_results) == len(business_results),
        "missingBindingCaseIds": [
            result["id"] for result in business_results if not result["strongGoldAssetIds"]
        ],
        "top3HitRate": _rate([result["top3StrongHit"] for result in business_results]),
        "allExpectedConceptsUnderstoodRate": _rate(
            [result["allExpectedConceptsUnderstood"] for result in business_results]
        ),
        "allExpectedConceptsCoveredTop5Rate": _rate(
            [result["allExpectedConceptsCoveredTop5"] for result in bound_results]
        ),
        "queryTypeHitRate": _rate([result["queryTypeHit"] for result in results]),
        "conceptMetrics": concept_metrics,
        "p95LatencyMs": latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0,
        "disallowedCaseIds": disallowed_cases,
        "forbiddenRelationCaseIds": forbidden_relation_case_ids,
        "outOfScopeCaseIds": out_of_scope_case_ids,
        "zeroResultCaseIds": zero_result_case_ids,
        "fallbackCaseIds": fallback_case_ids,
        "timedOutCaseIds": timed_out_case_ids,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run search evaluation cases.")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3, 4, 5], default=5)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="接入线上同款 AI 依赖（模型路由/向量召回/重排）跑评测",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="标准输出只打印聚合指标，完整明细仍写入 --output",
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
        rendered = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return

    try:
        report = run_eval(args.batch, max(args.limit, 1), with_ai=args.with_ai)
    except OperationalError as exc:
        raise SystemExit(
            "搜索评测需要已迁移到当前 schema 的数据库；"
            "请先运行 Alembic migration 或切换到服务器/测试库后重试。"
        ) from exc
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    if args.summary_only:
        summary = {key: value for key, value in report.items() if key != "results"}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(rendered)


if __name__ == "__main__":
    main()
