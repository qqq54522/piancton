from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ai.contracts import ModelRequest
from app.db.session import SessionLocal
from app.services.api_center_service import ApiCenterService

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_KNOWLEDGE_DOC = PROJECT_DIR / "docs" / "VIKINGDB_KNOWLEDGE_PREVIEW_2026-09-02.md"
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / "PREVIEW_SKILL_ROUTER_EVAL_2026-09-02.md"
DEFAULT_COMPACT_OUTPUT = (
    PROJECT_DIR / "docs" / "PREVIEW_SKILL_ROUTER_EVAL_COMPACT_2026-09-02.md"
)

SYSTEM_CODES = {
    "sync_school",
    "sync_exam",
    "sync_cultivation",
    "sync_planning",
    "sync_self_study",
    "sync_companion",
}
SELLING_POINT_CODES = {
    "school_sync",
    "animation_explanation",
    "instant_quiz",
    "new_curriculum_prediction",
    "focused_excellence",
    "transfer_practice",
    "expert_planning",
    "stage_transition",
    "universal_method",
    "ai_learning_plan",
    "ai_tutor_qa",
    "photo_guided_learning",
    "rapid_preview_review",
    "ai_error_book",
    "human_teacher_supervision",
    "learning_report",
}


@dataclass(frozen=True)
class Case:
    case_id: str
    query: str
    expected_systems: tuple[str, ...]
    expected_selling_points: tuple[str, ...]
    note: str


CASES = (
    Case(
        "DOC001",
        "洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做",
        ("sync_self_study",),
        ("photo_guided_learning",),
        "单卖点：拍题精学",
    ),
    Case(
        "DOC002",
        "我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做",
        ("sync_exam",),
        ("transfer_practice",),
        "单卖点：举一反三",
    ),
    Case(
        "DOC003",
        "拍题精学之后还能从一道题带到一类题，不只是告诉答案",
        ("sync_self_study", "sync_exam"),
        ("photo_guided_learning", "transfer_practice"),
        "多卖点：拍题精学 + 举一反三",
    ),
    Case(
        "DOC004",
        "动画课程",
        ("sync_school",),
        ("animation_explanation",),
        "宽泛概念：应命中但低置信或探索",
    ),
    Case(
        "DOC005",
        "孩子刚看完这节课，想马上做几道题看看是不是真的会了",
        ("sync_school",),
        ("instant_quiz",),
        "课后小测，不应跑到学情报告",
    ),
    Case(
        "DOC006",
        "我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材",
        ("sync_companion",),
        ("learning_report",),
        "学情报告，不应跑到课后小测",
    ),
    Case(
        "DOC007",
        "想找训练拔高、题型突破、压轴题专项提升的图",
        ("sync_exam",),
        ("focused_excellence",),
        "专项培优",
    ),
    Case(
        "DOC008",
        "孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课",
        ("sync_self_study",),
        ("rapid_preview_review",),
        "极速预习复习，不应硬判同步校内",
    ),
    Case(
        "DOC009",
        "希望课程内容能和学校教材版本、章节进度对得上",
        ("sync_school",),
        ("school_sync",),
        "同步校内",
    ),
    Case(
        "DOC010",
        "我想体现这套课是命题专家和教材编者一起规划出来的",
        ("sync_cultivation",),
        ("expert_planning",),
        "专家规划",
    ),
    Case(
        "DOC011",
        "小升初之前怕知识断层，想找能表达平稳衔接的素材",
        ("sync_cultivation",),
        ("stage_transition",),
        "学段衔接",
    ),
    Case(
        "DOC012",
        "同一道题可以用好几种方法拆开，不是死记一个公式",
        ("sync_cultivation",),
        ("universal_method",),
        "万能解法，不应跑到举一反三",
    ),
)


def build_prompt(knowledge_doc: Path, *, style: str = "strict") -> str:
    knowledge = knowledge_doc.read_text(encoding="utf-8")
    if style == "compact":
        return f"""
现在这是一个判断文档。现在我输入一段话，你判断这段话适配于这个文档里的哪几个体系和哪几个卖点，并告诉我这些体系和卖点叫什么。

要求：
- 可以有一个卖点，也可以有多个卖点。
- 如果这句话很宽泛，只能判断大概方向，就把 route_state 写成 ambiguous_or_exploratory。
- 只返回 JSON，不要返回 Markdown。
- JSON 格式：
{{
  "systems": [{{"code": "体系code", "name": "体系名", "reason": "原因"}}],
  "selling_points": [{{"code": "卖点code", "name": "卖点名", "reason": "原因"}}],
  "route_state": "precise | multi | ambiguous_or_exploratory | no_match",
  "short_reason": "一句话总结"
}}

判断文档：
{knowledge}
""".strip()
    return f"""
下面是一份业务知识文档，请只依据文档判断用户搜索话术涉及的体系和卖点。

判断原则：
1. 可以返回多个体系和多个卖点，但必须按用户原话重点从强到弱排序。
2. 如果只是宽泛概念，可以返回最相关卖点，但 confidence 不要虚高，
   并在 route_state 写 ambiguous_or_exploratory。
3. 不要判断证明点，不要选择图片，不要编造文档外 code。
4. 输出必须是合法 JSON，不要输出 Markdown。

允许的 system code：
{", ".join(sorted(SYSTEM_CODES))}

允许的 selling point code：
{", ".join(sorted(SELLING_POINT_CODES))}

输出协议：
{{
  "systems": [
    {{"code": "system code", "confidence": 0.0, "reason": "为什么命中"}}
  ],
  "selling_points": [
    {{"code": "selling point code", "confidence": 0.0, "reason": "为什么命中"}}
  ],
  "route_state": "precise | multi | ambiguous_or_exploratory | no_match",
  "short_reason": "一句话解释整体判断"
}}

业务知识文档：
{knowledge}
""".strip()


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    systems = payload.get("systems")
    selling_points = payload.get("selling_points")
    if not isinstance(systems, list) or not isinstance(selling_points, list):
        raise ValueError("缺少 systems 或 selling_points 数组")
    for item in systems:
        if not isinstance(item, dict) or item.get("code") not in SYSTEM_CODES:
            raise ValueError(f"无效体系 code：{item}")
    for item in selling_points:
        if not isinstance(item, dict) or item.get("code") not in SELLING_POINT_CODES:
            raise ValueError(f"无效卖点 code：{item}")
    return payload


def _codes(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item.get("code")) for item in items if isinstance(item, dict)]


def run_case(provider, prompt: str, case: Case, timeout_seconds: int) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        call = provider.generate_validated_json(
            ModelRequest(
                task="search_intent_understanding",
                prompt=prompt,
                input_text=case.query,
                timeout_seconds=timeout_seconds,
            ),
            validate_payload,
        )
        payload = call.value
        error = ""
        attempts = call.attempts
    except Exception as exc:  # noqa: BLE001 - keep report readable
        payload = {}
        error = f"{type(exc).__name__}: {exc}"
        attempts = getattr(exc, "attempts", ())
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    actual_systems = _codes(payload.get("systems"))
    actual_selling_points = _codes(payload.get("selling_points"))
    return {
        "id": case.case_id,
        "query": case.query,
        "note": case.note,
        "expectedSystems": list(case.expected_systems),
        "actualSystems": actual_systems,
        "systemHit": all(code in actual_systems for code in case.expected_systems),
        "expectedSellingPoints": list(case.expected_selling_points),
        "actualSellingPoints": actual_selling_points,
        "sellingPointHit": all(
            code in actual_selling_points for code in case.expected_selling_points
        ),
        "routeState": payload.get("route_state"),
        "shortReason": payload.get("short_reason", ""),
        "error": error,
        "latencyMs": latency_ms,
        "attempts": attempts,
    }


def render_report(results: list[dict[str, Any]], *, mode: str, knowledge_doc: Path) -> str:
    ok_system = sum(1 for item in results if item["systemHit"])
    ok_sp = sum(1 for item in results if item["sellingPointHit"])
    errors = sum(1 for item in results if item["error"])
    lines = [
        "# 业务文档版 Skill 路由小样本测试",
        "",
        f"运行时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        f"模式：`{mode}`",
        f"知识文档：`{knowledge_doc.relative_to(PROJECT_DIR)}`",
        "",
        "## 汇总",
        "",
        f"- 用例数：{len(results)}",
        f"- 体系命中：{ok_system}/{len(results)}",
        f"- 卖点命中：{ok_sp}/{len(results)}",
        f"- 错误数：{errors}",
        "",
        "## 明细",
        "",
        "| ID | 话术 | 预期卖点 | 实际卖点 | 状态 | 耗时 | 结论 |",
        "|---|---|---|---|---|---:|---|",
    ]
    for item in results:
        verdict = (
            "OK"
            if item["systemHit"] and item["sellingPointHit"] and not item["error"]
            else "CHECK"
        )
        if item["error"]:
            verdict = "ERROR"
        lines.append(
            (
                "| {id} | {query} | {expected} | {actual} | {state} | "
                "{latency:.0f}ms | {verdict} |"
            ).format(
                id=item["id"],
                query=item["query"].replace("|", "｜"),
                expected="、".join(item["expectedSellingPoints"]),
                actual="、".join(item["actualSellingPoints"]) or "—",
                state=item["routeState"] or "—",
                latency=item["latencyMs"],
                verdict=verdict,
            )
        )
    lines.extend(["", "## 模型解释", ""])
    for item in results:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- 话术：{item['query']}",
                f"- 预期体系：{', '.join(item['expectedSystems'])}",
                f"- 实际体系：{', '.join(item['actualSystems']) or '—'}",
                f"- 预期卖点：{', '.join(item['expectedSellingPoints'])}",
                f"- 实际卖点：{', '.join(item['actualSellingPoints']) or '—'}",
                f"- 判断状态：{item['routeState'] or '—'}",
                f"- 模型解释：{item['shortReason'] or '—'}",
                f"- 错误：{item['error'] or '—'}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the readable VikingDB knowledge preview as a single Skill."
    )
    parser.add_argument("--knowledge-doc", type=Path, default=DEFAULT_KNOWLEDGE_DOC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--prompt-style", choices=("strict", "compact"), default="strict")
    parser.add_argument("--allow-external", action="store_true")
    args = parser.parse_args()

    if args.prompt_style == "compact" and args.output == DEFAULT_OUTPUT:
        args.output = DEFAULT_COMPACT_OUTPUT
    prompt = build_prompt(args.knowledge_doc, style=args.prompt_style)
    if not args.allow_external:
        args.output.write_text(
            render_report(
                [],
                mode=f"prompt_preview_no_external/{args.prompt_style}",
                knowledge_doc=args.knowledge_doc,
            )
            + "\n\n"
            + "## 待发送 Prompt\n\n"
            + "```text\n"
            + prompt
            + "\n```\n",
            encoding="utf-8",
        )
        print(f"wrote prompt preview: {args.output}")
        return

    with SessionLocal() as db:
        provider = ApiCenterService(db).build_scheduled_provider(
            default_request_id="preview-skill-router-eval"
        )
        if not provider.configured:
            raise SystemExit("API 中心没有可用模型，无法执行外部调用测试")
        results = [
            run_case(provider, prompt, case, args.timeout_seconds) for case in CASES
        ]
    args.output.write_text(
        render_report(
            results,
            mode=f"api_center_external/{args.prompt_style}",
            knowledge_doc=args.knowledge_doc,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote eval report: {args.output}")


if __name__ == "__main__":
    main()
