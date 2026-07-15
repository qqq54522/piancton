from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from math import ceil

from app.models.search_feedback import SearchFeedbackEvent
from app.models.search_log import SearchLog
from app.repositories.search_feedback_repository import SearchFeedbackRepository
from app.repositories.search_log_repository import SearchLogRepository
from app.repositories.search_ops_repository import SearchOpsRepository
from app.schemas.search_ops import (
    AiConceptReviewQueueItem,
    AssetGapItem,
    ConceptHealthItem,
    SearchMetricItem,
    SearchOpsIssueRead,
    SearchOpsSummary,
)
from app.services.search_ops_serializers import feedback_read, log_read


class SearchOpsService:
    """Read path for the admin search operations dashboard.

    Pulls raw rows through repositories and only performs in-memory
    aggregation, ranking and formatting here.
    """

    def __init__(self, db):
        self.logs = SearchLogRepository(db)
        self.feedback = SearchFeedbackRepository(db)
        self.ops = SearchOpsRepository(db)

    def summary(self, *, days: int = 7, limit: int = 2000) -> SearchOpsSummary:
        bounded_days = max(1, min(days, 90))
        since = datetime.now(timezone.utc) - timedelta(days=bounded_days)
        logs = self.logs.list_since(since, limit=limit)
        feedback_events = self.feedback.list_since(since, limit=limit)
        total = len(logs)
        durations = sorted(
            item.duration_ms
            for item in logs
            if item.duration_ms is not None
        )
        return SearchOpsSummary(
            total_searches=total,
            zero_result_count=sum(1 for item in logs if item.result_count == 0),
            fallback_count=sum(1 for item in logs if item.fallback),
            timed_out_count=sum(1 for item in logs if item.timed_out),
            cache_hit_count=sum(1 for item in logs if item.cache_hit),
            reranker_used_count=sum(1 for item in logs if item.reranker_used),
            average_duration_ms=(
                round(sum(durations) / len(durations), 2)
                if durations
                else 0.0
            ),
            p95_duration_ms=_percentile_95(durations),
            ai_understood_count=sum(1 for item in logs if item.normalized_query),
            top_queries=self._top_items(item.keyword for item in logs if item.keyword),
            zero_result_queries=self._top_items(
                item.keyword for item in logs if item.keyword and item.result_count == 0
            ),
            top_normalized_queries=self._top_items(
                item.normalized_query for item in logs if item.normalized_query
            ),
            top_matched_concepts=self._top_items(
                item.matched_concept for item in logs if item.matched_concept
            ),
            feedback_count=len(feedback_events),
            feedback_by_type=self._top_items(
                item.feedback_type for item in feedback_events if item.feedback_type
            ),
            feedback_queries=self._top_items(
                item.keyword for item in feedback_events if item.keyword
            ),
            recent_feedback=[
                feedback_read(item) for item in feedback_events[:50]
            ],
            recent_logs=[log_read(item) for item in logs[:50]],
            search_issues=self._search_issues(logs, feedback_events),
            ai_review_queue=self._ai_review_queue(),
            concept_health=self._concept_health(logs),
            asset_gaps=self._asset_gaps(logs, feedback_events),
        )

    def _search_issues(
        self,
        logs: list[SearchLog],
        feedback_events: list[SearchFeedbackEvent],
    ) -> list[SearchOpsIssueRead]:
        grouped: dict[tuple[str, str], dict] = {}

        def add(
            *,
            keyword: str,
            issue_type: str,
            source: str,
            reason: str,
            suggested_action: str,
            created_at: datetime,
            severity: str,
        ) -> None:
            key = (keyword.strip(), issue_type)
            if not key[0]:
                return
            row = grouped.setdefault(
                key,
                {
                    "count": 0,
                    "source": source,
                    "reason": reason,
                    "suggested_action": suggested_action,
                    "latest_at": created_at,
                    "severity": severity,
                },
            )
            row["count"] += 1
            if created_at > row["latest_at"]:
                row["latest_at"] = created_at
            if severity == "high" or (severity == "medium" and row["severity"] == "low"):
                row["severity"] = severity

        for log in logs:
            if log.result_count == 0:
                add(
                    keyword=log.keyword,
                    issue_type="zero_result",
                    source="search_log",
                    reason="用户搜索没有返回素材",
                    suggested_action="先判断是素材缺口、概念关系缺失，还是业务话术没有进入意图词库",
                    created_at=log.created_at,
                    severity="high",
                )
            if log.fallback:
                add(
                    keyword=log.keyword,
                    issue_type="search_fallback",
                    source="search_log",
                    reason=log.fallback_reason or "智能搜索发生降级",
                    suggested_action="检查 Meilisearch、Embedding/Reranker 或模型理解链路是否可用",
                    created_at=log.created_at,
                    severity="medium",
                )

        feedback_map = {
            "not_relevant": (
                "irrelevant_results",
                "业务方反馈结果不相关",
                "查看 Top 图片和命中原因，判断是否误标、summary 偏泛或强意图过滤不够收紧",
                "high",
            ),
            "too_few_results": (
                "too_few_results",
                "业务方反馈结果太少",
                "判断是否需要补素材，或把同义表达补进业务意图词库",
                "medium",
            ),
            "need_different_style": (
                "style_gap",
                "业务方想要不同风格",
                "记录为素材风格需求，后续补充设计生产 brief",
                "low",
            ),
            "asset_request": (
                "asset_request",
                "业务方提交素材需求",
                "沉淀为素材需求，优先补齐高频业务话术对应图片",
                "high",
            ),
        }
        for event in feedback_events:
            if event.feedback_type == "relevant":
                continue
            issue_type, reason, action, severity = feedback_map.get(
                event.feedback_type,
                ("feedback", "业务方提交了搜索反馈", "查看反馈备注并归因", "medium"),
            )
            add(
                keyword=event.keyword,
                issue_type=issue_type,
                source="search_feedback",
                reason=reason,
                suggested_action=action,
                created_at=event.created_at,
                severity=severity,
            )

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        rows = [
            SearchOpsIssueRead(
                id=f"{issue_type}:{keyword}",
                keyword=keyword,
                issue_type=issue_type,
                severity=data["severity"],
                source=data["source"],
                count=data["count"],
                reason=data["reason"],
                suggested_action=data["suggested_action"],
                latest_at=data["latest_at"],
            )
            for (keyword, issue_type), data in grouped.items()
        ]
        return sorted(
            rows,
            key=lambda item: (
                severity_rank.get(item.severity, 3),
                -item.count,
                item.latest_at,
            ),
            reverse=False,
        )[:50]

    def _ai_review_queue(self, limit: int = 50) -> list[AiConceptReviewQueueItem]:
        rows: list[AiConceptReviewQueueItem] = []
        for link in self.ops.pending_ai_concept_links(limit=limit):
            image_id = link.asset_group.primary_image_id
            if not image_id:
                continue
            rows.append(
                AiConceptReviewQueueItem(
                    id=link.id,
                    asset_group_id=link.asset_group_id,
                    image_id=image_id,
                    image_title=link.asset_group.title,
                    thumbnail_url=f"/api/images/{image_id}/thumbnail",
                    concept_code=link.concept.code,
                    concept_name=link.concept.name,
                    system_names=[
                        item.system_tag.name
                        for item in link.concept.system_links
                        if item.status == "active"
                    ],
                    relation_role=link.relation_role,
                    confidence=link.confidence,
                    reason=link.evidence_reason,
                    created_at=link.created_at,
                )
            )
        return rows

    def _concept_health(self, logs: list[SearchLog]) -> list[ConceptHealthItem]:
        concepts = self.ops.active_concepts()
        asset_counts = self.ops.asset_counts_by_concept()
        links = self.ops.active_concept_links()
        manual_counts: Counter[str] = Counter()
        ai_pending_counts: Counter[str] = Counter()
        ai_accepted_counts: Counter[str] = Counter()
        ai_rejected_counts: Counter[str] = Counter()
        for link in links:
            if link.origin in {"manual", "migrated"}:
                manual_counts[link.concept_id] += 1
            elif link.review_status == "pending":
                ai_pending_counts[link.concept_id] += 1
            elif link.review_status == "accepted":
                ai_accepted_counts[link.concept_id] += 1
            elif link.review_status == "rejected":
                ai_rejected_counts[link.concept_id] += 1

        search_counts: Counter[str] = Counter()
        for log in logs:
            for concept in concepts:
                if (
                    log.matched_concept == concept.name
                    or log.normalized_query == concept.name
                ):
                    search_counts[concept.id] += 1

        rows: list[ConceptHealthItem] = []
        for concept in concepts:
            image_count = int(asset_counts.get(concept.id, 0))
            pending = ai_pending_counts[concept.id]
            manual = manual_counts[concept.id]
            accepted = ai_accepted_counts[concept.id]
            search_count = search_counts[concept.id]
            if image_count == 0 and search_count > 0:
                level = "needs_assets"
                recommendation = "有搜索需求但没有可用素材，优先补图或检查概念关系"
            elif pending >= max(2, manual + accepted):
                level = "needs_review"
                recommendation = "AI 待审核量偏高，优先批量确认或拒绝"
            elif search_count > 0 and image_count < 3:
                level = "watch"
                recommendation = "有搜索需求但素材覆盖偏少，建议继续观察并补充"
            else:
                level = "healthy"
                recommendation = "当前概念供给和审核状态基本正常"
            rows.append(
                ConceptHealthItem(
                    concept_id=concept.id,
                    concept_code=concept.code,
                    concept_name=concept.name,
                    system_names=[
                        item.system_tag.name
                        for item in concept.system_links
                        if item.status == "active"
                    ],
                    image_count=image_count,
                    manual_count=manual,
                    ai_pending_count=pending,
                    ai_accepted_count=accepted,
                    ai_rejected_count=ai_rejected_counts[concept.id],
                    search_count=search_count,
                    health_level=level,
                    recommendation=recommendation,
                )
            )
        rank = {"needs_assets": 0, "needs_review": 1, "watch": 2, "healthy": 3}
        return sorted(
            rows,
            key=lambda item: (
                rank[item.health_level],
                -item.search_count,
                item.image_count,
                item.concept_name,
            ),
        )[:80]

    def _asset_gaps(
        self,
        logs: list[SearchLog],
        feedback_events: list[SearchFeedbackEvent],
    ) -> list[AssetGapItem]:
        demand: Counter[str] = Counter()
        source: dict[str, set[str]] = {}
        suggested_concept: dict[str, str] = {}
        for log in logs:
            if log.result_count == 0:
                demand[log.keyword] += 2
                source.setdefault(log.keyword, set()).add("空结果")
            elif log.result_count < 3:
                demand[log.keyword] += 1
                source.setdefault(log.keyword, set()).add("结果少")
            if log.matched_concept or log.normalized_query:
                suggested_concept[log.keyword] = log.matched_concept or log.normalized_query or ""
        for event in feedback_events:
            if event.feedback_type in {"asset_request", "too_few_results", "need_different_style"}:
                demand[event.keyword] += 2 if event.feedback_type == "asset_request" else 1
                source.setdefault(event.keyword, set()).add("用户反馈")
        rows = [
            AssetGapItem(
                keyword=keyword,
                demand_count=count,
                suggested_concept=suggested_concept.get(keyword) or None,
                reason="高频需求未被现有素材充分满足",
                source="、".join(sorted(source.get(keyword, {"搜索"}))),
            )
            for keyword, count in demand.most_common(30)
            if keyword.strip()
        ]
        return rows

    def _top_items(self, values) -> list[SearchMetricItem]:
        return [
            SearchMetricItem(label=label, count=count)
            for label, count in Counter(values).most_common(10)
        ]

def _percentile_95(values: list[int]) -> int:
    if not values:
        return 0
    index = max(0, min(len(values) - 1, ceil(0.95 * len(values)) - 1))
    return values[index]
