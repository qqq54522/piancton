from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.services.vikingdb_client import VikingDBClient, VikingDBClientError

PROJECT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_DIR / "docs" / "VIKINGDB_KNOWLEDGE_SEARCH_PROBE_2026-09-02.md"

QUERIES = (
    "洋葱拍题精学可以让孩子不是直接抄答案，而是一步一步理解这道题怎么做",
    "我想找一张图，表达一道题讲透以后还能练同类题、换个条件也会做",
    "拍题精学之后还能从一道题带到一类题，不只是告诉答案",
    "动画课程",
    "孩子刚看完这节课，想马上做几道题看看是不是真的会了",
    "我需要家长能每周看到孩子学了多久、正确率和薄弱点的素材",
    "想找训练拔高、题型突破、压轴题专项提升的图",
    "孩子课前拍一下课本，几分钟知道今天要学什么，带着问题去听课",
)


def build_client() -> tuple[VikingDBClient, str, int]:
    settings = get_settings()
    client = VikingDBClient(
        base_url=settings.vikingdb_base_url,
        api_key=settings.vikingdb_api_key,
        collection_name=settings.vikingdb_collection_name,
        upsert_path=settings.vikingdb_upsert_path,
        search_path=settings.vikingdb_search_path,
        timeout_seconds=settings.vikingdb_timeout_seconds,
    )
    return client, settings.vikingdb_index_name, settings.vikingdb_search_limit


def run_probe(queries: tuple[str, ...], *, limit: int | None = None) -> list[dict[str, Any]]:
    client, index_name, default_limit = build_client()
    if not client.configured:
        raise SystemExit("VikingDB 未配置或未启用，无法执行检索探针")
    resolved_limit = limit or default_limit
    results: list[dict[str, Any]] = []
    for query in queries:
        started = time.perf_counter()
        error = ""
        response: dict[str, Any] = {}
        matches: list[dict[str, Any]] = []
        try:
            result = client.search_text(
                query,
                index_name=index_name,
                limit=resolved_limit,
                filter_expression={
                    "op": "must",
                    "field": "doc_type",
                    "conds": ["selling_point"],
                },
            )
            response = result.response
            matches = result.matches
        except VikingDBClientError as exc:
            error = str(exc)
        results.append(
            {
                "query": query,
                "latencyMs": round((time.perf_counter() - started) * 1000, 2),
                "error": error,
                "matches": matches,
                "response": response,
            }
        )
    return results


def _match_code(match: dict[str, Any]) -> str:
    for key in ("concept_code", "doc_id", "id", "source_id"):
        value = match.get(key)
        if value:
            return str(value)
    fields = match.get("fields")
    if isinstance(fields, dict):
        for key in ("concept_code", "doc_id", "source_id"):
            value = fields.get(key)
            if value:
                return str(value)
    return "unknown"


def _short_response(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    return text[:1200] + ("..." if len(text) > 1200 else "")


def render_report(results: list[dict[str, Any]]) -> str:
    lines = [
        "# 火山体系/卖点知识检索探针",
        "",
        f"运行时间：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        "",
        "## 汇总",
        "",
        "| 话术 | 耗时 | 错误 | Top 命中 |",
        "|---|---:|---|---|",
    ]
    for item in results:
        top_codes = [_match_code(match) for match in item["matches"][:5]]
        lines.append(
            "| {query} | {latency:.0f}ms | {error} | {codes} |".format(
                query=item["query"].replace("|", "｜"),
                latency=item["latencyMs"],
                error=item["error"] or "—",
                codes="、".join(top_codes) or "—",
            )
        )
    lines.extend(["", "## 原始响应摘录", ""])
    for index, item in enumerate(results, start=1):
        lines.extend(
            [
                f"### Q{index}",
                "",
                f"- 话术：{item['query']}",
                f"- 耗时：{item['latencyMs']}ms",
                f"- 错误：{item['error'] or '—'}",
                "",
                "```json",
                _short_response(item["response"]) if item["response"] else "{}",
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Probe VikingDB knowledge-card search latency and recall."
    )
    parser.add_argument("--query", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    queries = tuple(args.query) if args.query else QUERIES
    results = run_probe(queries, limit=args.limit)
    args.output.write_text(render_report(results) + "\n", encoding="utf-8")
    print(f"wrote probe report: {args.output}")


if __name__ == "__main__":
    main()
