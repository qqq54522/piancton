from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ai.contracts import ModelRequest
from app.ai.factory import get_model_provider
from app.api.dependencies import get_search_service
from app.db.session import SessionLocal

SELLING_POINTS = {
    "school_sync": "孩子校外学习内容要跟学校当前教材、章节和授课进度对应",
    "animation_explanation": "用动画、故事或动态过程把抽象知识讲清楚",
    "instant_quiz": "刚学完当前内容就用练习或检测确认是否掌握",
    "new_curriculum_prediction": "应对课标和考试改革带来的新情境、跨学科和新题型",
    "focused_excellence": "围绕学科重难点、压轴题、薄弱题型或考前重点集中突破",
    "transfer_practice": "在考试题型和变式语境中理解原理并迁移到一类题",
    "expert_planning": "由命题、教材或教研专家设计课程体系和长期路径",
    "stage_transition": "解决小升初、初升高等学段变化造成的知识断层和适应问题",
    "universal_method": "摆脱死记硬背，形成长期学科思维和自主分析能力",
    "ai_learning_plan": "结合个人成绩、目标和时间自动生成接下来任务、顺序和日程",
    "ai_tutor_qa": "孩子学习中遇到问题时可随时与 AI 即时互动并继续追问",
    "photo_guided_learning": "针对当前不会的题，不直接给答案而是分步骤引导推导",
    "rapid_preview_review": "课前或课后拍课本、笔记，在很短时间内梳理内容",
    "ai_error_book": "把个人线下错题长期归档、查询并从错题出发复练",
    "human_teacher_supervision": "由真人老师持续诊断、提醒、打卡、回访并跟进执行",
    "learning_report": "按日或周向家长汇总学习内容、时长、行为、正确率和薄弱点",
}

DISPLAY_NAMES = {
    "school_sync": "同步校内",
    "animation_explanation": "动画精讲",
    "instant_quiz": "课后小测",
    "new_curriculum_prediction": "新课标新考法预测",
    "focused_excellence": "专项培优",
    "transfer_practice": "举一反三",
    "expert_planning": "专家规划",
    "stage_transition": "学段衔接",
    "universal_method": "万能解法",
    "ai_learning_plan": "AI定制学习方案",
    "ai_tutor_qa": "AI私教答疑",
    "photo_guided_learning": "AI拍题精学",
    "rapid_preview_review": "极速预习复习",
    "ai_error_book": "AI错题本",
    "human_teacher_supervision": "真人老师督学",
    "learning_report": "学情报告反馈",
}

TARGET_COUNTS = {
    code: 7 if index < 4 else 6
    for index, code in enumerate(SELLING_POINTS)
}


def _normalize(value: str) -> str:
    ignored = set(" ，。；;：:、,.!?！？“”\"'（）()《》<>[]【】-_ ")
    return "".join(char.lower() for char in value if char not in ignored)


def _generate_candidates(service) -> list[dict[str, str]]:
    provider = get_model_provider(timeout_seconds=180)
    if not provider.configured:
        raise SystemExit("外部模型未配置，无法准备外部语义评测话术")

    generated: list[dict[str, str]] = []
    seen: set[str] = set()
    codes = list(SELLING_POINTS)
    for group_index in range(0, len(codes), 4):
        group = codes[group_index : group_index + 4]
        catalog_lines = []
        for code in group:
            intent = next(
                item
                for item in service.query_understanding.catalog.intents
                if item.code == code
            )
            forbidden = list(
                dict.fromkeys(
                    [
                        intent.display_name,
                        intent.name,
                        *intent.phrases,
                        *intent.pain_points,
                        *intent.interpretation_patterns,
                        *intent.must_have_concepts,
                    ]
                )
            )
            catalog_lines.append(
                json.dumps(
                    {
                        "code": code,
                        "meaning": SELLING_POINTS[code],
                        "avoid_verbatim": forbidden[:45],
                    },
                    ensure_ascii=False,
                )
            )
        prompt = """
生成自然、真实、可供业务负责人审批的中文图片搜索话术。
每个 code 生成 18 条，必须是单一卖点，不包含证明点、品牌数字、奖项、学校案例或具体效果承诺。
必须使用业务小白会说的间接表达、生活情境、代词和同义改写；
不要直接写卖点名称，不要逐字复述 avoid_verbatim 中的任何短语。
每条 18～55 个汉字，彼此语义和句式明显不同。只返回：
{"items":[{"code":"稳定code","query":"自然搜索话术"}]}
目标目录：
""" + "\n".join(catalog_lines)
        payload = provider.generate_json(
            ModelRequest(
                task="search_intent_understanding",
                prompt=prompt,
                timeout_seconds=180,
            )
        ).value
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            code = str(item.get("code") or "").strip()
            query = str(item.get("query") or "").strip()
            key = _normalize(query)
            if code not in group or not query or key in seen:
                continue
            seen.add(key)
            generated.append({"code": code, "query": query})
        print(
            f"candidate_generation group={group_index // 4 + 1}/4 total={len(generated)}",
            flush=True,
        )

    selected: list[dict[str, str]] = []
    selected_counts: Counter[str] = Counter()
    model_required_counts: Counter[str] = Counter()
    for item in generated:
        code = item["code"]
        local = service.query_understanding.understand_locally(item["query"])
        if not service.query_understanding.should_use_model(item["query"], local):
            continue
        model_required_counts[code] += 1
        if selected_counts[code] >= TARGET_COUNTS[code]:
            continue
        selected.append(
            {
                "id": f"SPX{len(selected) + 1:03d}",
                "query": item["query"],
                "expected_code": code,
                "expected_name": DISPLAY_NAMES[code],
                "review_status": "pending",
                "review_notes": "",
            }
        )
        selected_counts[code] += 1

    shortages = {
        code: TARGET_COUNTS[code] - selected_counts[code]
        for code in SELLING_POINTS
        if selected_counts[code] < TARGET_COUNTS[code]
    }
    print(
        "model_required_counts="
        + json.dumps(model_required_counts, ensure_ascii=False, sort_keys=True),
        flush=True,
    )
    if shortages:
        raise SystemExit(
            "外部语义候选不足，请调整生成提示后重试："
            + json.dumps(shortages, ensure_ascii=False)
        )
    if len(selected) != 100:
        raise SystemExit(f"评测集数量应为 100，实际为 {len(selected)}")
    return selected


def prepare(path: Path) -> None:
    with SessionLocal() as db:
        service = get_search_service(db)
        cases = _generate_candidates(service)
    payload = {
        "version": "2026-07-22.1",
        "created_at": datetime.now().astimezone().isoformat(),
        "provider": "gpt-5.5",
        "criteria": {
            "scope": "只评卖点，不评证明点",
            "external_success": "search_diagnostics.query_understanding.status == ok 且非缓存",
            "selection": "仅保留运行前应触发外部模型的话术",
        },
        "cases": cases,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"prepared path={path} cases={len(cases)}", flush=True)


def _branch(response, source: str) -> dict[str, Any] | None:
    diagnostics = response.search_diagnostics
    if diagnostics is None:
        return None
    for item in diagnostics.branches:
        if item.source == source:
            return item.model_dump(mode="json", by_alias=True)
    return None


def _concept_codes(service, response) -> list[str]:
    understanding = response.search_understanding
    if understanding is None:
        return []
    lookup: dict[str, str] = {}
    for intent in service.query_understanding.catalog.intents:
        lookup[_normalize(intent.display_name)] = intent.code
        lookup[_normalize(intent.name)] = intent.code
    codes: list[str] = []
    for match in understanding.matched_business_concepts:
        code = lookup.get(_normalize(match.concept))
        if code and code not in codes:
            codes.append(code)
    return codes


def _result_concept_names(response) -> list[str]:
    names: list[str] = []
    for result in response.results:
        for match in result.matched_query_concepts:
            if match.concept_name not in names:
                names.append(match.concept_name)
    return names


def run(path: Path, *, start: int, end: int, max_attempts: int) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    with SessionLocal() as db:
        service = get_search_service(db)
        for position, case in enumerate(cases, start=1):
            if position < start or position > end:
                continue
            if case.get("attempts") and case.get("external_semantic_success"):
                continue
            attempts: list[dict[str, Any]] = list(case.get("attempts") or [])
            final_response = None
            first_attempt = len(attempts) + 1
            for attempt_no in range(first_attempt, first_attempt + max_attempts):
                started = time.perf_counter()
                try:
                    response = service.search(case["query"], 12)
                    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
                    branch = _branch(response, "query_understanding") or {
                        "source": "query_understanding",
                        "status": "missing",
                        "durationMs": 0,
                        "resultCount": 0,
                        "cacheHit": False,
                        "detail": "诊断缺失",
                    }
                    attempts.append(
                        {
                            "attempt": attempt_no,
                            "elapsed_ms": elapsed_ms,
                            "query_understanding": branch,
                            "fallback": response.fallback,
                            "fallback_reason": response.fallback_reason,
                        }
                    )
                    final_response = response
                    if branch.get("status") == "ok" and not branch.get("cacheHit"):
                        break
                except Exception as exc:  # noqa: BLE001 - audit every failed real run
                    attempts.append(
                        {
                            "attempt": attempt_no,
                            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                            "query_understanding": {
                                "source": "query_understanding",
                                "status": "failed",
                                "cacheHit": False,
                                "detail": f"{type(exc).__name__}: {exc}",
                            },
                            "fallback": True,
                            "fallback_reason": str(exc),
                        }
                    )

            final_branch = attempts[-1]["query_understanding"]
            external_success = bool(
                final_branch.get("status") == "ok" and not final_branch.get("cacheHit")
            )
            case["attempts"] = attempts
            case["external_semantic_success"] = external_success
            case["final_branch_status"] = final_branch.get("status")
            case["final_branch_detail"] = final_branch.get("detail") or ""
            if final_response is not None:
                actual_codes = _concept_codes(service, final_response)
                case["actual_codes"] = actual_codes
                case["actual_names"] = [DISPLAY_NAMES.get(code, code) for code in actual_codes]
                case["result_selling_points"] = _result_concept_names(final_response)
                case["has_selling_point"] = bool(actual_codes)
                case["expected_code_present"] = case["expected_code"] in actual_codes
                case["query_type"] = (
                    final_response.search_understanding.query_type
                    if final_response.search_understanding
                    else None
                )
                case["top_result_titles"] = [
                    result.image.title for result in final_response.results[:5]
                ]
                case["result_count"] = len(final_response.results)
                case["total_duration_ms"] = (
                    final_response.search_diagnostics.total_duration_ms
                    if final_response.search_diagnostics
                    else attempts[-1]["elapsed_ms"]
                )
                case["fallback"] = final_response.fallback
                case["fallback_reason"] = final_response.fallback_reason
            case["recorded_at"] = datetime.now().astimezone().isoformat()
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"completed {position:03d}/100 {case['id']} "
                f"external={external_success} branch={case['final_branch_status']} "
                f"actual={','.join(case.get('actual_codes', [])) or '-'}",
                flush=True,
            )


def report(data_path: Path, report_path: Path) -> None:
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    cases = payload["cases"]
    completed = [case for case in cases if case.get("attempts")]
    external_successes = sum(case.get("external_semantic_success") is True for case in completed)
    with_selling_point = sum(case.get("has_selling_point") is True for case in completed)
    expected_present = sum(case.get("expected_code_present") is True for case in completed)
    fallback_count = sum(case.get("fallback") is True for case in completed)
    local_semantic_count = sum(
        case.get("external_semantic_success") is not True for case in completed
    )
    durations = sorted(float(case.get("total_duration_ms") or 0) for case in completed)
    p50 = durations[len(durations) // 2] if durations else 0
    p95 = durations[max(0, int(len(durations) * 0.95) - 1)] if durations else 0
    branch_counts = Counter(case.get("final_branch_status") or "not_run" for case in cases)
    lines = [
        "# 100 条卖点话术外部语义评测（待业务审批）",
        "",
        f"生成时间：{datetime.now().astimezone().isoformat()}",
        "",
        "## 口径",
        "",
        "- 本报告只评核心卖点，不评证明点、证据表达点或具体图片质量。",
        (
            "- 100 条话术在执行前均通过本地预检，确认会触发外部查询理解；"
            "随后严格串行逐条运行线上同款搜索依赖。"
        ),
        "- “外部语义成功”要求查询诊断中 `query_understanding=ok` 且不是缓存结果。",
        (
            "- “产出卖点”只表示实际响应至少返回一个稳定卖点；"
            "是否符合业务含义，最终以负责人逐条审批为准。"
        ),
        "- `expected_code_present` 仅作自动预检，不替代人工审批。",
        "",
        "## 汇总",
        "",
        f"- 已完成：{len(completed)}/100",
        f"- 外部语义成功：{external_successes}/{len(completed) or 100}",
        f"- 产出至少一个卖点：{with_selling_point}/{len(completed) or 100}",
        f"- 实际卖点包含预设卖点：{expected_present}/{len(completed) or 100}",
        f"- 外部语义失败、由本地语义完成：{local_semantic_count}/{len(completed) or 100}",
        f"- 搜索结果层降级（与外部语义成功互不排斥）：{fallback_count}/{len(completed) or 100}",
        f"- 最终分支状态：{json.dumps(branch_counts, ensure_ascii=False, sort_keys=True)}",
        f"- 延迟 P50/P95：{p50:.0f}ms / {p95:.0f}ms",
        "",
        "## 逐条审批表",
        "",
        (
            "| # | ID | 测试话术 | 预设卖点 | 实际识别卖点 | 结果卡卖点 | "
            "外部语义 | 搜索结果降级 | 耗时 | 自动检查 | 业务审批 | 审批备注 |"
        ),
        "|---:|---|---|---|---|---|---|---|---:|---|---|---|",
    ]
    for index, case in enumerate(cases, start=1):
        attempts = case.get("attempts") or []
        attempt_note = f"成功（{len(attempts)}次）" if case.get("external_semantic_success") else (
            case.get("final_branch_status") or "未执行"
        )
        actual_names = "、".join(case.get("actual_names") or []) or "—"
        result_names = "、".join(case.get("result_selling_points") or []) or "—"
        auto = (
            "有卖点；含预设"
            if case.get("has_selling_point") and case.get("expected_code_present")
            else "有卖点；不含预设"
            if case.get("has_selling_point")
            else "未产出卖点"
        )
        query = str(case["query"]).replace("|", "\\|").replace("\n", " ")
        fallback = "是" if case.get("fallback") else "否"
        lines.append(
            f"| {index} | {case['id']} | {query} | {case['expected_name']} | "
            f"{actual_names} | {result_names} | {attempt_note} | {fallback} | "
            f"{float(case.get('total_duration_ms') or 0):.0f}ms | {auto} | ☐正确 ☐错误 |  |"
        )
    lines.extend(
        [
            "",
            "## 指标计算（审批完成后）",
            "",
            "- 卖点产出率 = 审批为“正确”的条数 ÷ 100。",
            "- 外部语义成功率 = 外部语义成功条数 ÷ 100。",
            "- 外部语义卖点正确率 = 同时满足“外部语义成功”且审批正确的条数 ÷ 外部语义成功条数。",
            "- 本地语义占比 = 外部语义未成功、最终由本地语义完成的条数 ÷ 100。",
            "",
            "## 原始运行信息",
            "",
            f"- Provider：{payload.get('provider', 'unknown')}",
            f"- 数据版本：{payload.get('version', 'unknown')}",
            f"- 原始 JSON：`{data_path.name}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report path={report_path}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=100)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.data)
    if args.run:
        run(
            args.data,
            start=max(1, args.start),
            end=min(100, args.end),
            max_attempts=max(1, args.max_attempts),
        )
    if args.report:
        report(args.data, args.report)


if __name__ == "__main__":
    main()
